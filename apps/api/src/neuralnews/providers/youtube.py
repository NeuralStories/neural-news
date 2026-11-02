"""Conector YouTube.

- Metadatos reales vía YouTube Data API v3 (requiere clave; sin clave → error explicativo).
- Análisis de vídeo vía Gemini (funciones documentadas que aceptan URL pública de YouTube):
  adaptador preparado pero NO validado; su salida se guarda como VIDEO_ANALYSIS y nunca como
  transcripción literal.
- Modo demo: devuelve el vídeo ficticio de fixtures, claramente marcado.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import httpx

from ..services import secrets as secrets_service
from ..config import get_settings
from .base import ContentDraft, FetchResult, SegmentDraft
from .fixtures import (
    DEMO_VIDEO_AUTHOR,
    DEMO_VIDEO_TITLE,
    DEMO_VIDEO_TRANSCRIPT,
)
from .manual import split_paragraphs

YOUTUBE_URL_PATTERNS = [
    re.compile(r"youtube\.com/watch\?(?:.*&)?v=([\w-]{11})"),
    re.compile(r"youtu\.be/([\w-]{11})"),
    re.compile(r"youtube\.com/shorts/([\w-]{11})"),
    re.compile(r"youtube\.com/embed/([\w-]{11})"),
]


def extract_video_id(url: str) -> str | None:
    for pattern in YOUTUBE_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def normalize_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_youtube_metadata(video_id: str) -> dict:
    """Metadatos reales con YouTube Data API. Requiere NEURAL_YOUTUBE_API_KEY."""
    settings = get_settings()
    if not secrets_service.clave_de_proveedor("youtube_api_key"):
        raise RuntimeError(
            "No hay clave de YouTube configurada. Añade NEURAL_YOUTUBE_API_KEY en .env para "
            "obtener metadatos reales, o usa el modo demo."
        )
    response = httpx.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet,contentDetails",
            "id": video_id,
            "key": secrets_service.clave_de_proveedor("youtube_api_key"),
        },
        timeout=15,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        raise RuntimeError(
            "El vídeo no existe, es privado o está restringido; no se pueden leer sus datos"
        )
    snippet = items[0]["snippet"]
    return {
        "title": snippet.get("title"),
        "author": snippet.get("channelTitle"),
        "published_at": snippet.get("publishedAt"),
        "language": (snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")),
        "duration": items[0].get("contentDetails", {}).get("duration"),
        "provider": "youtube_data_api_v3",
    }


def _iso8601_duration_seconds(duration: str) -> int | None:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return None
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def fetch_youtube(url: str, demo: bool) -> FetchResult:
    """Punto de entrada del conector: demo o metadatos reales (el análisis llega después)."""
    video_id = extract_video_id(url or "")
    if not video_id:
        return FetchResult(
            provider="youtube", canonical_url=url, status="FAILED",
            error="La URL no parece de un vídeo de YouTube válido",
        )
    canonical = normalize_video_url(video_id)
    if demo:
        return FetchResult(
            provider="youtube",
            external_id=video_id,
            canonical_url=canonical,
            title=DEMO_VIDEO_TITLE,
            author=DEMO_VIDEO_AUTHOR,
            published_at=datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc),
            language="es",
            status="READY",
            contents=[
                ContentDraft(
                    content_type="TRANSCRIPT",
                    text=DEMO_VIDEO_TRANSCRIPT,
                    is_verbatim=False,  # transcripción simulada, no la real del vídeo
                    provider="demo",
                    coverage=1.0,
                    confidence="high",
                    segments=_timestamped_segments(DEMO_VIDEO_TRANSCRIPT),
                ),
                ContentDraft(
                    content_type="VIDEO_ANALYSIS",
                    text=(
                        "ANÁLISIS SIMULADO DEL VÍDEO (DEMO) — no es una transcripción literal.\n"
                        "[00:05] Cortexa Labs anuncia Radar, modelo multimodal; 12% más de acierto en "
                        "benchmarks internos de razonamiento visual; lista de espera para demo web.\n"
                        "[00:35] Vireo AI confirma ronda de 40 millones de dólares liderada por Meridian Capital.\n"
                        "[00:50] Opinión del autor: predicción sin datos sobre móviles con modelo local."
                    ),
                    is_verbatim=False,
                    provider="gemini_demo",
                    model="demo-model",
                    coverage=0.8,
                    confidence="low",
                    segments=_timestamped_segments(
                        "[00:05] Cortexa Labs anuncia Radar con 12% más de acierto en benchmarks internos. "
                        "[00:35] Vireo AI confirma ronda de 40 millones. "
                        "[00:50] Opinión sin datos sobre móviles con modelo local."
                    ),
                ),
            ],
            metadata={"demo": True, "video_id": video_id},
        )
    try:
        meta = fetch_youtube_metadata(video_id)
    except RuntimeError as exc:
        return FetchResult(
            provider="youtube", external_id=video_id, canonical_url=canonical,
            status="FAILED", error=str(exc),
        )
    except httpx.HTTPError as exc:
        return FetchResult(
            provider="youtube", external_id=video_id, canonical_url=canonical,
            status="FAILED",
            error=f"No se ha podido contactar con la API de YouTube: {exc.__class__.__name__}",
        )
    published = None
    if meta.get("published_at"):
        published = datetime.fromisoformat(meta["published_at"].replace("Z", "+00:00"))
    return FetchResult(
        provider="youtube",
        external_id=video_id,
        canonical_url=canonical,
        title=meta.get("title"),
        author=meta.get("author"),
        published_at=published,
        language=meta.get("language"),
        status="METADATA_ONLY",
        contents=[
            ContentDraft(
                content_type="METADATA_ONLY",
                text=f"{meta.get('title') or ''}\n{meta.get('author') or ''}".strip(),
                is_verbatim=False,
                provider="youtube_data_api_v3",
                coverage=None,
                confidence=None,
            )
        ],
        metadata={
            "video_id": video_id,
            "duration": meta.get("duration"),
            "metadata_provider": "youtube_data_api_v3",
            "demo": False,
            "note": "Sin transcripción: pide un análisis del vídeo o aporta una transcripción",
        },
    )


def _timestamped_segments(text: str) -> list[SegmentDraft]:
    """Convierte marcas [mm:ss] del texto en segmentos con posición temporal."""
    segments: list[SegmentDraft] = []
    pattern = re.compile(r"\[(\d{1,2}):(\d{2})\]")
    current_start = None
    buffer: list[str] = []

    def flush(end_ms: int | None) -> None:
        if buffer and current_start is not None:
            segments.append(
                SegmentDraft(
                    text=" ".join(buffer).strip(),
                    start_ms=current_start,
                    end_ms=end_ms,
                    sequence=len(segments),
                )
            )

    for line in text.splitlines():
        match = pattern.search(line)
        if match:
            flush(match.group(1) and int(match.group(1)) * 60_000 + int(match.group(2)) * 1000)
            buffer = []
            current_start = int(match.group(1)) * 60_000 + int(match.group(2)) * 1000
            line = pattern.sub("", line)
        if line.strip():
            buffer.append(line.strip())
    flush(None)
    return segments


def fetch_youtube_demo_analysis(video_id: str, analysis_kind: str = "gemini_demo") -> FetchResult:
    """Análisis simulado del vídeo (modo demo): resultado tipado, nunca transcripción literal."""
    body = (
        "ANÁLISIS SIMULADO DEL VÍDEO (DEMO) — no es una transcripción literal.\n"
        "[00:05] Cortexa Labs anuncia Radar, modelo multimodal; 12% más de acierto en benchmarks "
        "internos de razonamiento visual; lista de espera para demo web.\n"
        "[00:35] Vireo AI confirma ronda de 40 millones de dólares liderada por Meridian Capital.\n"
        "[00:50] Opinión del autor: predicción sin datos sobre móviles con modelo local."
    )
    return FetchResult(
        provider="youtube",
        external_id=video_id,
        canonical_url=normalize_video_url(video_id),
        title=DEMO_VIDEO_TITLE,
        author=DEMO_VIDEO_AUTHOR,
        published_at=datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc),
        language="es",
        status="READY",
        contents=[
            ContentDraft(
                content_type="VIDEO_ANALYSIS",
                text=body,
                is_verbatim=False,
                provider=analysis_kind,
                model="demo-model",
                coverage=0.8,
                confidence="low",
                segments=_timestamped_segments(body),
            )
        ],
        metadata={"demo": True, "video_id": video_id, "kind": "video_analysis"},
    )
