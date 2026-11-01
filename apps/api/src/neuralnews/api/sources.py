"""Fuentes: alta con idempotencia, consulta, reprocesado y transcripciones aportadas."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from ..config import get_settings
from ..db import get_db
from ..models import Claim, Job, Source, SourceContent, Story, StorySource
from ..queue import enqueue
from ..schemas import ProcessRequest, SourceCreate, SourceDetailOut, SourceOut
from ..providers.safety import FetchBlocked
from ..security import get_current_actor
from ..services.sources import DuplicateSource, create_source
from ..states import CONTENT_TYPE_LABELS, SOURCE_LABELS, STORY_LABELS
from ..worker_tasks import ANALYZE_VIDEO, PROCESS_SOURCE  # noqa: F401  (ANALYZE_VIDEO usado)

logger = logging.getLogger(__name__)

# Caché de transcripciones automáticas: acotada en tiempo y en tamaño para que no
# crezca sin límite en un proceso de larga vida (NN-109.8, hallazgo B8).
_AUTO_TRANSCRIPT_TTL_S = 3600.0
_AUTO_TRANSCRIPT_NEGATIVE_TTL_S = 300.0
_AUTO_TRANSCRIPT_MAX_ENTRIES = 64
_auto_transcript_cache: dict[str, tuple[float, object]] = {}


def _cache_get(video_id: str):
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


def _auto_transcript(video_id: str):
    """Búsqueda automática de transcripción de YouTube (punto de inyección
    para pruebas). Cadena de proveedores, sin Docker ni claves de API:
      1) yt-dlp (subtítulos automáticos y manuales, cualquier vídeo);
      2) timedtext (pistas manuales publicadas);
      3) reproductor interno (pistas ASR)."""
    hit, cached = _cache_get(video_id)
    if hit:
        return cached
    from ..providers.transcript import fetch_youtube_transcript_auto
    draft = fetch_youtube_transcript_auto(video_id)
    _cache_put(video_id, draft)
    return draft

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


def source_to_out(db, source: Source) -> SourceOut:
    return SourceOut(
        id=source.id,
        provider=source.provider,
        external_id=source.external_id,
        canonical_url=source.canonical_url,
        title=source.title,
        author=source.author,
        published_at=source.published_at,
        imported_at=source.imported_at,
        language=source.language,
        status=source.status,
        status_label=SOURCE_LABELS.get(source.status, source.status),
        demo=source.demo,
        metadata=source.metadata_json or {},
    )


@router.post("", response_model=dict)
def add_source(
    payload: SourceCreate,
    request: Request,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Registra una fuente. Con Idempotency-Key, repetir la llamada no duplica nada."""
    idempotency_key = request.headers.get("Idempotency-Key")
    try:
        source = create_source(
            db,
            url=payload.url,
            text=payload.text,
            title=payload.title,
            author=payload.author,
            published_at=payload.published_at,
            transcript=payload.transcript,
        )
    except DuplicateSource as exc:
        job = None
        if idempotency_key:
            job, _ = enqueue(
                db, PROCESS_SOURCE, {"source_id": exc.source.id},
                dedupe_key=f"process:{exc.source.id}:{idempotency_key}",
            )
        db.flush()
        return {
            "source": source_to_out(db, exc.source),
            "job_id": job.id if job else None,
            "created": False,
            "message": str(exc),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job, created = enqueue(
        db,
        PROCESS_SOURCE,
        {"source_id": source.id},
        dedupe_key=(
            f"process:{source.id}:{idempotency_key}" if idempotency_key else f"process:{source.id}"
        ),
    )
    db.flush()
    return {
        "source": source_to_out(db, source),
        "job_id": job.id,
        "created": True,
        "message": None,
    }


@router.get("")
def list_sources(
    db=Depends(get_db),
    actor=Depends(get_current_actor),
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = select(Source).order_by(Source.imported_at.desc())
    if status:
        query = query.where(Source.status == status)
    if provider:
        query = query.where(Source.provider == provider)
    total = len(db.scalars(query).all())
    rows = db.scalars(query.limit(min(limit, 200)).offset(offset)).all()
    return {
        "total": total,
        "items": [source_to_out(db, s).model_dump(mode="json") for s in rows],
    }


@router.get("/{source_id}")
def get_source(source_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    out = SourceDetailOut(
        **source_to_out(db, source).model_dump(),
        contents=[],
        stories=[],
    )
    contents = db.scalars(
        select(SourceContent).where(SourceContent.source_id == source.id)
    ).all()
    for content in contents:
        out.contents.append(
            {
                "id": content.id,
                "content_type": content.content_type,
                "content_type_label": CONTENT_TYPE_LABELS.get(content.content_type, content.content_type),
                "is_verbatim": content.is_verbatim,
                "provider": content.provider,
                "model": content.model,
                "coverage": content.coverage,
                "confidence": content.confidence,
                "extracted_at": content.extracted_at.isoformat(),
                "char_count": len(content.text),
                "segment_count": len(content.segments),
            }
        )
    links = db.scalars(select(StorySource).where(StorySource.source_id == source.id)).all()
    for link in links:
        story = db.get(Story, link.story_id)
        out.stories.append(
            {
                "id": story.id,
                "title": story.title,
                "status": story.status,
                "status_label": STORY_LABELS.get(story.status, story.status),
            }
        )
    return out.model_dump(mode="json")


@router.get("/{source_id}/transcript")
def get_transcript(source_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Devuelve la transcripción vigente de la fuente (texto + segmentos)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    for content in db.scalars(
        select(SourceContent)
        .where(SourceContent.source_id == source.id)
        .order_by(SourceContent.id.desc())
    ).all():
        if content.content_type in ("TRANSCRIPT", "ARTICLE_TEXT", "MANUAL_TEXT"):
            return {
                "found": True,
                "content_type": content.content_type,
                "content_type_label": CONTENT_TYPE_LABELS.get(content.content_type, content.content_type),
                "is_verbatim": content.is_verbatim,
                "provider": content.provider,
                "text": content.text,
                "segments": [
                    {
                        "start_ms": seg.start_ms,
                        "end_ms": seg.end_ms,
                        "text": seg.text,
                        "sequence": seg.sequence,
                    }
                    for seg in content.segments
                ],
            }
    return {"found": False, "message": "Esta fuente todavía no tiene transcripción"}


@router.post("/{source_id}/transcribe")
def transcribe_source(source_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Busca o crea la transcripción de la fuente según su tipo:
    YouTube → subtítulos públicos; pódcast → podcast:transcript del feed;
    artículo web → texto del artículo; manual → el texto aportado.
    Nada se inventa: si no hay transcripción accesible, se responde el motivo."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")

    def out(found: bool, created: bool, draft=None, message: str | None = None,
            transcript: dict | None = None) -> dict:
        body: dict = {"found": found, "created": created}
        if message:
            body["message"] = message
        if draft is not None:
            body["transcript"] = {
                "text": draft.text,
                "provider": draft.provider,
                "segments": len(draft.segments),
            }
        elif transcript is not None:
            body["transcript"] = transcript
        return body

    from ..services.sources import _store_content
    try:
        if source.provider == "youtube":
            # Búsqueda automática para CUALQUIER vídeo: pistas manuales
            # (timedtext) y automáticas ASR (reproductor interno). Descarga
            # pública sin clave ni coste, como el artículo web.
            video_id = source.external_id or ""
            draft = _auto_transcript(video_id)
            if draft is not None:
                _store_content(db, source, draft)
                db.flush()
                return out(True, True, draft, "Transcripción encontrada automáticamente y almacenada")
            existing_demo = db.scalar(
                select(SourceContent)
                .where(SourceContent.source_id == source.id,
                       SourceContent.content_type == "TRANSCRIPT")
                .order_by(SourceContent.id.desc())
            )
            if existing_demo is not None:
                return out(
                    True,
                    False,
                    message="Fuente de demostración: la transcripción simulada ya está almacenada",
                    transcript={
                        "text": existing_demo.text,
                        "provider": existing_demo.provider,
                        "segments": len(existing_demo.segments),
                    },
                )
            return out(False, False, None,
                       "El vídeo no tiene subtítulos (ni manuales ni automáticos) accesibles; "
                       "aporta la transcripción manualmente")
        elif source.provider == "spotify":
            # El feed RSS lo aporta el operador en los metadatos de la fuente.
            # La columna del modelo es `metadata_json` (no `metadata`): leerla con
            # el nombre equivocado lanzaba AttributeError y lo enmascaraba el
            # `except Exception` de más abajo (hallazgo B1, NN-109.1).
            feed_url = (source.metadata_json or {}).get("feed_url")
            if not feed_url:
                return out(False, False, None,
                           "Spotify no expone la transcripción sin el feed RSS del programa: "
                           "añade feed_url a los metadatos de la fuente o pega la transcripción")
            from ..providers.transcript import fetch_podcast_transcript_from_feed
            draft = fetch_podcast_transcript_from_feed(
                feed_url, source.external_id, source.title)
            if draft is None:
                return out(False, False, None,
                           "El feed no incluye podcast:transcript para este episodio")
        elif source.provider in ("web_rss", "manual") and source.canonical_url:
            from ..providers.web_rss import fetch_web
            result = fetch_web(source.canonical_url)
            if result.status in ("READY", "PARTIAL") and result.contents:
                for draft in result.contents:
                    _store_content(db, source, draft)
                return out(True, True, result.contents[0],
                           "Texto del artículo extraído de nuevo desde la URL canónica")
            return out(False, False, None,
                       f"No se ha podido extraer el texto desde la URL: {result.error or result.status}")
        else:
            return out(False, False, None,
                       "Fuente manual: el texto aportado ES la transcripción; "
                       "guárdalo con «Guardar transcripción»")
    except FetchBlocked as exc:
        return out(False, False, None, f"Bloqueado por seguridad: {exc}")
    except Exception as exc:  # noqa: BLE001 — el fallo se registra; al cliente solo un motivo seguro
        # No se filtra el texto crudo de la excepción al cliente: puede contener rutas
        # del sistema o stderr de herramientas. El detalle completo queda en el log.
        logger.exception("Fallo al obtener la transcripción de la fuente %s", source.id)
        return out(
            False,
            False,
            None,
            "No se ha podido obtener la transcripción por un fallo del conector; "
            "inténtalo de nuevo o aporta la transcripción manualmente",
        )

    _store_content(db, source, draft)
    db.flush()
    return out(True, True, draft, "Transcripción creada y almacenada como texto literal")


@router.post("/{source_id}/process")
def process_source(
    source_id: int,
    payload: ProcessRequest,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Reprocesa la fuente. Es idempotente: si ya hay un trabajo vivo, se reutiliza."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    job, created = enqueue(
        db,
        PROCESS_SOURCE,
        {"source_id": source.id},
        dedupe_key=f"process:{source.id}",
    )
    db.flush()
    return {"job_id": job.id, "created": created}


@router.post("/{source_id}/analyze")
def analyze_video(
    source_id: int,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Pide el análisis del vídeo de la fuente (adaptador Gemini; requiere clave, salvo demo)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    if source.provider != "youtube":
        raise HTTPException(
            status_code=400,
            detail="El análisis de vídeo sólo aplica a fuentes de YouTube; para otros tipos, "
            "aporta el texto o una transcripción",
        )
    job, created = enqueue(
        db,
        ANALYZE_VIDEO,
        {"source_id": source.id},
        dedupe_key=f"analyze:{source.id}",
    )
    db.flush()
    return {"job_id": job.id, "created": created}


@router.post("/{source_id}/transcript")
def add_transcript(
    source_id: int,
    payload: SourceCreate,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Añade una transcripción real aportada por el usuario (queda marcada como literal)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Escribe o pega la transcripción")
    from ..providers.base import ContentDraft
    

    _store_content(
        db,
        source,
        ContentDraft(
            content_type="TRANSCRIPT",
            text=payload.transcript.strip(),
            is_verbatim=True,
            provider="manual",
            coverage=1.0,
            confidence="high",
        ),
    )
    if source.status in ("METADATA_ONLY", "PARTIAL", "FAILED"):
        source.status = "READY"
    db.flush()
    return {"ok": True, "message": "Transcripción guardada como texto literal aportado"}
