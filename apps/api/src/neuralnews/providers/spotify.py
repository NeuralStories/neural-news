"""Conector Spotify/pódcast.

- Identifica episodios y programas desde la URL (open.spotify.com/episode/…|show/…).
- Metadatos reales vía Spotify Web API cuando hay token (NEURAL_SPOTIFY_ACCESS_TOKEN);
  el endpoint get-an-episode exige autorización de usuario: adaptador preparado, NO validado.
- Busca transcripción pública (podcast:transcript) sólo si el usuario aporta el feed RSS
  del programa; nunca se extrae ni descifra audio.
- Sin transcripción: estado METADATA_ONLY («Solo información básica») y opción de cargar
  texto o audio por el usuario.
- Modo demo: episodio ficticio de fixtures.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from ..config import get_settings
from .base import ContentDraft, FetchResult

SPOTIFY_EPISODE_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?episode/([A-Za-z0-9]+)")
SPOTIFY_SHOW_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?show/([A-Za-z0-9]+)")


def extract_episode_id(url: str) -> str | None:
    match = SPOTIFY_EPISODE_RE.search(url or "")
    return match.group(1) if match else None


def extract_show_id(url: str) -> str | None:
    match = SPOTIFY_SHOW_RE.search(url or "")
    return match.group(1) if match else None


def fetch_spotify_episode_metadata(episode_id: str) -> dict:
    """Metadatos reales con Spotify Web API. Requiere token de usuario (no validado en MVP)."""
    settings = get_settings()
    if not settings.spotify_access_token:
        raise RuntimeError(
            "No hay token de Spotify configurado. Añade NEURAL_SPOTIFY_ACCESS_TOKEN (autorización "
            "de usuario) para leer metadatos reales, pega el feed RSS del pódcast, o usa el modo demo."
        )
    response = httpx.get(
        f"https://api.spotify.com/v1/episodes/{episode_id}",
        headers={"Authorization": f"Bearer {settings.spotify_access_token}"},
        params={"market": "ES"},
        timeout=15,
    )
    if response.status_code in (401, 403):
        raise RuntimeError("El token de Spotify no es válido o ha caducado")
    if response.status_code == 404:
        raise RuntimeError("El episodio no existe o no está disponible en el mercado ES")
    response.raise_for_status()
    return response.json()


def fetch_spotify(url: str, demo: bool) -> FetchResult:
    episode_id = extract_episode_id(url or "")
    show_id = extract_show_id(url or "")
    if not episode_id and not show_id:
        return FetchResult(
            provider="spotify", canonical_url=url, status="FAILED",
            error="La URL no parece de un episodio o programa de Spotify",
        )
    if show_id and not episode_id:
        return FetchResult(
            provider="spotify", canonical_url=url, status="FAILED",
            external_id=show_id,
            error=(
                "Has pegado un programa completo. Pega la URL de un episodio concreto, o el feed "
                "RSS del pódcast en el conector web para revisar sus capítulos."
            ),
        )
    canonical = f"https://open.spotify.com/episode/{episode_id}"
    if demo:
        from .fixtures import DEMO_SPOTIFY_EPISODE as ep  # import local: evita ciclo en pruebas

        release = datetime.strptime(ep["release_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return FetchResult(
            provider="spotify",
            external_id=episode_id,
            canonical_url=canonical,
            title=ep["title"],
            author=ep["author"],
            published_at=release,
            language=ep["language"],
            status="METADATA_ONLY",
            contents=[
                ContentDraft(
                    content_type="METADATA_ONLY",
                    text=ep["description"],
                    is_verbatim=False,
                    provider="demo",
                    coverage=None,
                    confidence=None,
                )
            ],
            metadata={
                "demo": True,
                "episode_id": episode_id,
                "duration_ms": ep["duration_ms"],
                "note": "Este episodio solo tiene información básica. Añade una transcripción para analizar lo que se ha dicho",
            },
        )
    try:
        meta = fetch_spotify_episode_metadata(episode_id)
    except RuntimeError as exc:
        return FetchResult(
            provider="spotify", external_id=episode_id, canonical_url=canonical,
            status="FAILED", error=str(exc),
        )
    except httpx.HTTPError as exc:
        return FetchResult(
            provider="spotify", external_id=episode_id, canonical_url=canonical,
            status="FAILED",
            error=f"No se ha podido contactar con la API de Spotify: {exc.__class__.__name__}",
        )
    release = None
    if meta.get("release_date"):
        try:
            release = datetime.strptime(meta["release_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            release = None
    return FetchResult(
        provider="spotify",
        external_id=episode_id,
        canonical_url=canonical,
        title=meta.get("name"),
        author=(meta.get("show") or {}).get("publisher") or (meta.get("show") or {}).get("name"),
        published_at=release,
        language=meta.get("language"),
        status="METADATA_ONLY",
        contents=[
            ContentDraft(
                content_type="METADATA_ONLY",
                text=meta.get("html_description") or meta.get("description") or "",
                is_verbatim=False,
                provider="spotify_web_api",
                coverage=None,
                confidence=None,
            )
        ],
        metadata={
            "episode_id": episode_id,
            "duration_ms": meta.get("duration_ms"),
            "demo": False,
            "note": "Este episodio solo tiene información básica. Añade una transcripción para analizar lo que se ha dicho",
        },
    )
