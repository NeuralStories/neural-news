"""Transcripción de fuentes: YouTube, pódcast y artículo web.

La lógica vive aquí, y no en el router, para que la API y el worker la usen
igual. El trabajo pesado —descargar subtítulos, consultar el feed RSS, extraer
el artículo— no debe ejecutarse dentro de una petición HTTP: se encola y lo
hace el worker (NN-110).

Regla del proyecto: **nada se inventa**. Si no hay transcripción accesible, se
devuelve el motivo exacto; nunca un texto de relleno.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Source, SourceContent

logger = logging.getLogger(__name__)

# Caché de transcripciones automáticas: acotada en tiempo y en tamaño para que
# no crezca sin límite en un proceso de larga vida (hallazgo B8, NN-109.8).
_AUTO_TRANSCRIPT_TTL_S = 3600.0
_AUTO_TRANSCRIPT_NEGATIVE_TTL_S = 300.0
_AUTO_TRANSCRIPT_MAX_ENTRIES = 64
_auto_transcript_cache: dict[str, tuple[float, object]] = {}


def _cache_get(video_id: str) -> tuple[bool, object]:
    """Devuelve (acierto, valor) del valor cacheado, vencida la entrada."""
    entry = _auto_transcript_cache.get(video_id)
    if entry is None:
        return False, None
    expires_at, value = entry
    if expires_at <= time.monotonic():
        _auto_transcript_cache.pop(video_id, None)
        return False, None
    return True, value


def _cache_put(video_id: str, value) -> None:
    if len(_auto_transcript_cache) >= _AUTO_TRANSCRIPT_MAX_ENTRIES:
        # Se descarta la entrada más antigua: el límite es de tamaño, no de tiempo.
        oldest = min(_auto_transcript_cache.items(), key=lambda item: item[1][0])
        _auto_transcript_cache.pop(oldest[0], None)
    ttl = _AUTO_TRANSCRIPT_TTL_S if value is not None else _AUTO_TRANSCRIPT_NEGATIVE_TTL_S
    _auto_transcript_cache[video_id] = (time.monotonic() + ttl, value)


def auto_transcript(video_id: str):
    """Búsqueda automática de transcripción de YouTube.

    Cadena de proveedores, sin Docker ni claves de API:
      1) yt-dlp (subtítulos automáticos y manuales, cualquier vídeo);
      2) timedtext (pistas manuales publicadas);
      3) reproductor interno (pistas ASR).
    """
    hit, cached = _cache_get(video_id)
    if hit:
        return cached
    from ..providers.transcript import fetch_youtube_transcript_auto
    draft = fetch_youtube_transcript_auto(video_id)
    _cache_put(video_id, draft)
    return draft


@dataclass
class TranscriptionOutcome:
    """Resultado de intentar transcribir una fuente."""

    found: bool = False
    created: bool = False
    text: str | None = None
    provider: str | None = None
    segments: int = 0
    message: str = ""

    def to_out(self) -> dict:
        body: dict = {"found": self.found, "created": self.created}
        if self.message:
            body["message"] = self.message
        if self.text is not None:
            body["transcript"] = {
                "text": self.text,
                "provider": self.provider,
                "segments": self.segments,
            }
        return body


def _transcript_guardado(db: Session, source: Source) -> SourceContent | None:
    return db.scalar(
        select(SourceContent)
        .where(
            SourceContent.source_id == source.id,
            SourceContent.content_type == "TRANSCRIPT",
        )
        .order_by(SourceContent.id.desc())
    )


def transcribe_source_content(db: Session, source: Source) -> TranscriptionOutcome:
    """Busca o crea la transcripción de la fuente según su tipo.

    - YouTube → subtítulos públicos (manuales o ASR).
    - Pódcast → `podcast:transcript` del feed RSS que aporta el operador.
    - Artículo web → texto extraído de la URL canónica.
    - Manual → el texto aportado ES la transcripción.

    Es **idempotente**: si ya hay una transcripción guardada, se devuelve sin
    volver a descargarla (salvo que el proveedor automático aporte una nueva).
    """
    from ..services.sources import _store_content

    if source.provider == "youtube":
        video_id = source.external_id or ""
        draft = auto_transcript(video_id)
        if draft is not None:
            _store_content(db, source, draft)
            db.flush()
            return TranscriptionOutcome(
                found=True,
                created=True,
                text=draft.text,
                provider=draft.provider,
                segments=len(draft.segments),
                message="Transcripción encontrada automáticamente y almacenada",
            )
        guardada = _transcript_guardado(db, source)
        if guardada is not None:
            return TranscriptionOutcome(
                found=True,
                created=False,
                text=guardada.text,
                provider=guardada.provider,
                segments=len(guardada.segments),
                message="Fuente de demostración: la transcripción simulada ya está almacenada",
            )
        return TranscriptionOutcome(
            found=False,
            message=(
                "El vídeo no tiene subtítulos (ni manuales ni automáticos) accesibles; "
                "aporta la transcripción manualmente"
            ),
        )

    if source.provider == "spotify":
        # El feed RSS lo aporta el operador en los metadatos de la fuente.
        # La columna del modelo es `metadata_json` (no `metadata`): leerla con
        # el nombre equivocado lanzaba AttributeError y lo enmascaraba el
        # `except Exception` de la API (hallazgo B1, NN-109.1).
        feed_url = (source.metadata_json or {}).get("feed_url")
        if not feed_url:
            return TranscriptionOutcome(
                found=False,
                message=(
                    "Spotify no expone la transcripción sin el feed RSS del programa: "
                    "añade feed_url a los metadatos de la fuente o pega la transcripción"
                ),
            )
        from ..providers.transcript import fetch_podcast_transcript_from_feed

        draft = fetch_podcast_transcript_from_feed(
            feed_url, source.external_id, source.title
        )
        if draft is None:
            return TranscriptionOutcome(
                found=False,
                message="El feed no incluye podcast:transcript para este episodio",
            )
        _store_content(db, source, draft)
        db.flush()
        return TranscriptionOutcome(
            found=True,
            created=True,
            text=draft.text,
            provider=draft.provider,
            segments=len(draft.segments),
            message="Transcripción creada y almacenada como texto literal",
        )

    if source.provider in ("web_rss", "manual") and source.canonical_url:
        return extract_web_content(db, source)

    return TranscriptionOutcome(
        found=False,
        message=(
            "Fuente manual: el texto aportado ES la transcripción; "
            "guárdalo con «Guardar transcripción»"
        ),
    )


def extract_web_content(db: Session, source: Source) -> TranscriptionOutcome:
    """Extrae el texto del artículo web de la URL canónica de la fuente."""
    from ..providers.web_rss import fetch_web
    from ..services.sources import _store_content

    result = fetch_web(source.canonical_url)
    if result.status in ("READY", "PARTIAL") and result.contents:
        for draft in result.contents:
            _store_content(db, source, draft)
        db.flush()
        primero = result.contents[0]
        return TranscriptionOutcome(
            found=True,
            created=True,
            text=primero.text,
            provider=primero.provider,
            segments=len(primero.segments),
            message="Texto del artículo extraído de nuevo desde la URL canónica",
        )
    return TranscriptionOutcome(
        found=False,
        message=f"No se ha podido extraer el texto desde la URL: {result.error or result.status}",
    )
