"""Búsqueda y creación de transcripciones para cualquier fuente (NN-107 FASE 4).

- YouTube: pista de subtítulos pública vía el endpoint timedtext (sin clave),
  con preferencia de idiomas en castellano; segmentos con marcas de tiempo.
- Pódcast (Spotify/feeds): etiqueta podcast:transcript del feed RSS del
  programa (texto plano, VTT, SRT o JSON), sólo si el operador aporta el feed.
- Artículo web: el texto del artículo ES su transcripción (ya se extrae al
  procesar la fuente); aquí se devuelve o se vuelve a extraer.
- Fuente manual: el texto aportado es la transcripción.

Nada se inventa: si no hay transcripción accesible, se responde con el motivo
exacto en lugar de fabricar texto.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import feedparser

from ..config import get_settings
from ..providers.base import ContentDraft, SegmentDraft
from ..providers.safety import FetchBlocked, fetch_url_safely

PREFERRED_LANGS = ("es", "es-419", "es-ES", "en", "en-US")

# Cliente web interno del reproductor de YouTube: permite listar las pistas de
# subtítulos (incluidas las automáticas ASR) de CUALQUIER vídeo, sin clave.
INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
INNERTUBE_CONTEXT = {
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20261001.00.00",
            "hl": "es",
            "gl": "ES",
        }
    }
}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def _fetch_text(url: str) -> str:
    """Descarga con el guardián SSRF y devuelve el cuerpo como texto UTF-8."""
    settings = get_settings()
    fetched = fetch_url_safely(url, settings)
    if fetched.status >= 400:
        raise ValueError(f"La descarga respondió {fetched.status}")
    return fetched.body.decode("utf-8", errors="replace")


def _start_ms(value: str | None) -> int:
    try:
        return int(round(float(value or 0) * 1000))
    except (TypeError, ValueError):
        return 0


def parse_timedtext(xml_text: str) -> list[SegmentDraft]:
    """Parsea el XML de subtítulos de YouTube (<text start dur>)."""
    segments: list[SegmentDraft] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return segments
    for node in root.iter("text"):
        text = html.unescape(node.text or "").replace("\n", " ").strip()
        if not text:
            continue
        start = _start_ms(node.get("start"))
        dur = _start_ms(node.get("dur"))
        segments.append(
            SegmentDraft(text=text, start_ms=start, end_ms=start + dur if dur else None,
                         sequence=len(segments))
        )
    return segments


def parse_vtt(raw: str) -> str:
    """Convierte WebVTT en texto plano (sin cabeceras ni marcas)."""
    lines: list[str] = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        for line in block.splitlines():
            if "-->" in line or line.strip().startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
                continue
            if re.fullmatch(r"\d+", line.strip()):
                continue
            text = re.sub(r"<[^>]+>", "", line).strip()
            if text and text not in lines[-1:]:
                lines.append(text)
    return " ".join(lines)


def parse_srt(raw: str) -> str:
    return parse_vtt(re.sub(r"^WEBVTT.*$", "", raw.strip(), flags=re.M) or raw)


def parse_podcast_json(raw: str) -> str:
    """Formato JSON de Podcasting 2.0: segmentos con body o texto."""
    try:
        data = json.loads(raw)
    except ValueError:
        return ""
    items = data if isinstance(data, list) else data.get("segments", [])
    parts = []
    for item in items:
        body = (item.get("body") or item.get("text") or "").strip()
        if body:
            parts.append(body)
    return "\n\n".join(parts)


def fetch_youtube_transcript(video_id: str, langs: tuple[str, ...] = PREFERRED_LANGS) -> ContentDraft | None:
    """Busca una pista de subtítulos pública del vídeo y la convierte en
    ContentDraft con marcas de tiempo. None si no hay pista accesible."""
    try:
        listing = _fetch_text(f"https://video.google.com/timedtext?type=list&v={video_id}")
        tracks = re.findall(
            r'<track[^>]*lang="([^"]+)"[^>]*name="([^"]*)"', listing
        ) or re.findall(r"<track[^>]*lang=\"([^\"]+)\"[^>]*>", listing)
        # (lang, name) o (lang, lang) según el orden de atributos
        parsed: list[tuple[str, str]] = []
        for match in re.finditer(r"<track[^>]*>", listing):
            tag = match.group(0)
            lang = re.search(r'lang="([^"]+)"', tag)
            name = re.search(r'name="([^"]*)"', tag)
            if lang:
                parsed.append((lang.group(1), name.group(1) if name else ""))
    except ValueError:
        return None

    ordered: list[tuple[str, str]] = []
    for want in langs:
        for lang, name in parsed:
            if lang.lower().startswith(want.lower()):
                ordered.append((lang, name))
    ordered += [(l, n) for l, n in parsed if (l, n) not in ordered]

    for lang, name in ordered:
        url = f"https://www.youtube.com/api/timedtext?lang={lang}&v={video_id}"
        if name:
            url += f"&name={name}"
        try:
            xml_text = _fetch_text(url)
        except ValueError:
            continue
        segments = parse_timedtext(xml_text)
        if not segments:
            continue
        text = " ".join(seg.text for seg in segments)
        return ContentDraft(
            content_type="TRANSCRIPT",
            text=text,
            is_verbatim=True,
            provider="youtube_timedtext",
            confidence="medium",  # puede ser subtítulo automático
            segments=segments,
        )
    return None


def fetch_podcast_transcript_from_feed(feed_url: str, episode_external_id: str | None,
                                       episode_title: str | None = None) -> ContentDraft | None:
    """Busca la etiqueta podcast:transcript del episodio en el feed RSS del
    programa (sólo si el operador aporta el feed) y la convierte a texto."""
    try:
        feed_text = _fetch_text(feed_url)
    except ValueError:
        return None
    feed = feedparser.parse(feed_text)
    entry = None
    for item in feed.entries:
        if episode_external_id and episode_external_id in (item.get("id") or ""):
            entry = item
            break
        if episode_title and (item.get("title") or "") == episode_title:
            entry = item
            break
    if entry is None:
        return None
    links = entry.get("podcast_transcript") or entry.get("podcast:transcript") or []
    if not isinstance(links, list):
        links = [links]
    for link in links:
        href = link.get("href") if isinstance(link, dict) else None
        if not href:
            continue
        try:
            raw = _fetch_text(href)
        except ValueError:
            continue
        ctype = (link.get("type") or "").lower() if isinstance(link, dict) else ""
        if "json" in ctype or href.endswith(".json"):
            text = parse_podcast_json(raw)
        elif "vtt" in ctype or href.endswith(".vtt"):
            text = parse_vtt(raw)
        elif "srt" in ctype or href.endswith(".srt"):
            text = parse_srt(raw)
        else:
            text = raw if raw.strip() and "<" not in raw[:200] else parse_vtt(raw)
        if text.strip():
            return ContentDraft(
                content_type="TRANSCRIPT",
                text=text,
                is_verbatim=True,
                provider="podcast_feed",
                confidence="high",
                segments=[],
            )
    return None


def _valid_video_id(video_id: str) -> bool:
    return bool(VIDEO_ID_RE.match(video_id or ""))


def youtube_caption_tracks(video_id: str) -> list[dict]:
    """Lista las pistas de subtítulos del vídeo vía la API interna del
    reproductor (incluye las automáticas ASR). Sin clave de API."""
    if not _valid_video_id(video_id):
        raise ValueError("Identificador de vídeo de YouTube no válido")
    body = {**INNERTUBE_CONTEXT, "videoId": video_id}
    response = httpx.post(INNERTUBE_URL, json=body, timeout=get_settings().fetch_timeout_s,
                          headers={"Content-Type": "application/json"})
    response.raise_for_status()
    payload = response.json()
    renderer = (payload.get("captions") or {}).get("playerCaptionsTracklistRenderer") or {}
    tracks = renderer.get("captionTracks") or []
    # Preferencia: castellano primero, y pistas manuales antes que automáticas
    def sort_key(track: dict) -> tuple[int, int]:
        lang = (track.get("languageCode") or "").lower()
        lang_pref = 0 if lang.startswith("es") else (1 if lang.startswith("en") else 2)
        is_asr = track.get("kind") == "asr"
        return (lang_pref, 1 if is_asr else 0)
    return sorted(tracks, key=sort_key)


def parse_json3_events(payload: dict) -> list[SegmentDraft]:
    """Convierte la respuesta json3 de subtítulos en segmentos con tiempos."""
    segments: list[SegmentDraft] = []
    for event in payload.get("events") or []:
        segs = event.get("segs") or []
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        start = int(event.get("tStartMs") or 0)
        dur = int(event.get("dDurationMs") or 0)
        segments.append(
            SegmentDraft(text=text, start_ms=start, end_ms=start + dur if dur else None,
                         sequence=len(segments))
        )
    return segments


def fetch_youtube_transcript_auto(video_id: str, langs: tuple[str, ...] = PREFERRED_LANGS) -> ContentDraft | None:
    """Transcripción AUTOMÁTICA para cualquier vídeo de YouTube:
    1) pistas manuales vía timedtext (más fiables); 2) si no, las automáticas
    ASR del reproductor. None si el vídeo no tiene subtítulos de ningún tipo."""
    if not _valid_video_id(video_id):
        raise ValueError("Identificador de vídeo de YouTube no válido")

    # 0) yt-dlp: vía que hoy descarga los subtítulos automáticos de cualquier
    # vídeo (incluidos los ASR). Es el proveedor principal.
    via_ytdlp = fetch_youtube_transcript_ytdlp(video_id, langs)
    if via_ytdlp is not None:
        return via_ytdlp

    # 1) Pistas manuales publicadas (timedtext)
    manual = fetch_youtube_transcript(video_id, langs)
    if manual is not None:
        return manual

    # 2) Cualquier pista (incluida ASR) vía el reproductor interno
    try:
        tracks = youtube_caption_tracks(video_id)
    except (httpx.HTTPError, ValueError):
        return None
    for track in tracks:
        base_url = track.get("baseUrl")
        if not base_url:
            continue
        try:
            response = httpx.get(f"{base_url}&fmt=json3", timeout=get_settings().fetch_timeout_s)
            response.raise_for_status()
            segments = parse_json3_events(response.json())
        except (httpx.HTTPError, ValueError):
            continue
        if not segments:
            continue
        text = " ".join(seg.text for seg in segments)
        is_asr = track.get("kind") == "asr"
        return ContentDraft(
            content_type="TRANSCRIPT",
            text=text,
            is_verbatim=True,
            provider="youtube_asr" if is_asr else "youtube_captions",
            confidence="medium" if is_asr else "high",
            segments=segments,
        )
    return None


# ---------------------------------------------------------------------------
# Proveedor yt-dlp (binario autónomo, sin dependencias de Python):
# es la vía que hoy lista y descarga los subtítulos AUTOMÁTICOS de cualquier
# vídeo. Se usa como proveedor principal; innertube queda como alternativa.
# ---------------------------------------------------------------------------
# El binario puede vivir en tools/ dentro del repo o junto a él (herramientas
# locales del proyecto); se buscan ambos, sin depender del PATH.
_REPO_ROOT = Path(__file__).resolve().parents[5]
YTDLP_CANDIDATES = (
    _REPO_ROOT / "tools" / "yt-dlp.exe",
    _REPO_ROOT / "tools" / "yt-dlp",
    _REPO_ROOT.parent / "tools" / "yt-dlp.exe",
    _REPO_ROOT.parent / "tools" / "yt-dlp",
)


def yt_dlp_binary() -> Path | None:
    """Localiza el binario de yt-dlp (herramienta local o variable de entorno)."""
    import os
    import shutil as _shutil
    env = os.getenv("NEURAL_YTDLP_PATH")
    if env and Path(env).exists():
        return Path(env)
    found = _shutil.which("yt-dlp")
    if found:
        return Path(found)
    for candidate in YTDLP_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def yt_dlp_available_languages(video_id: str) -> list[str]:
    """Idiomas de subtítulos disponibles (automáticos y manuales) del vídeo."""
    binary = yt_dlp_binary()
    if binary is None:
        return []
    try:
        proc = subprocess.run(
            [str(binary), "--list-subs", "--no-warnings", "--no-playlist",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, timeout=90,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    text = proc.stdout.decode("utf-8", "replace")
    langs: list[str] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("Language") and "Name" in line:
            in_table = True
            continue
        if not in_table:
            continue
        parts = line.split()
        if not parts:
            continue
        lang = parts[0]
        # Las líneas de la tabla empiezan por el código de idioma; se ignoran
        # los avisos [info] y las cabeceras.
        if lang.startswith("["):
            continue
        if re.fullmatch(r"[a-zA-Z]{2,3}(-[a-zA-Z0-9-]+)?", lang) and lang not in langs:
            langs.append(lang)
    return langs


def _pick_language(available: list[str], preferred: tuple[str, ...]) -> str | None:
    """Elige el idioma disponible más cercano al preferido.

    Se prioriza la coincidencia EXACTA (p. ej. «es-419» si existe) frente a la
    parcial, porque YouTube usa variantes regionales: pedir «es» cuando sólo
    existe «es-419» devuelve 404/429 en la descarga."""
    # 1) Variante regional corta del idioma preferido (es-419, es-ES, en-US…):
    #    se prueban ANTES que el idioma genérico, porque en YouTube «es» puede
    #    no existir como pista aunque sí exista «es-419». Se descartan las
    #    variantes encadenadas («es-es-419», «en-zh-TW»): son traducciones
    #    automáticas de otra lengua y no una transcripción en el idioma pedido.
    for want in preferred:
        base = want.split("-")[0].lower()
        variants = [l for l in available
                    if l.lower().startswith(base + "-")
                    and not re.match(rf"^{base}-[a-z]{{2,3}}-", l.lower())]
        if variants:
            return sorted(variants, key=len, reverse=True)[0]
    # 2) Coincidencia exacta con un idioma preferido
    for want in preferred:
        for lang in available:
            if lang.lower() == want.lower():
                return lang
    # 3) Idioma genérico
    for want in preferred:
        base = want.split("-")[0].lower()
        for lang in available:
            if lang.lower() == base:
                return lang
    return available[0] if available else None


def fetch_youtube_transcript_ytdlp(
    video_id: str, preferred: tuple[str, ...] = PREFERRED_LANGS
) -> ContentDraft | None:
    """Transcripción COMPLETA de cualquier vídeo con subtítulos, mediante
    yt-dlp. Descarga una sola pista (evita los 429 por peticiones múltiples) y
    devuelve el texto con sus marcas de tiempo."""
    binary = yt_dlp_binary()
    if binary is None or not _valid_video_id(video_id):
        return None

    import tempfile

    langs = yt_dlp_available_languages(video_id)
    lang = _pick_language(langs, preferred)
    if lang is None:
        return None

    import time

    with tempfile.TemporaryDirectory(prefix="nn-subs-") as tmp:
        out = str(Path(tmp) / "cap.%(ext)s")
        files: list[Path] = []
        # YouTube limita por IP las peticiones de subtítulos (429): se reintenta
        # con espera y, en cada intento, se pide UNA sola pista.
        for attempt in range(3):
            for flag in ("--write-auto-subs", "--write-subs"):
                try:
                    subprocess.run(
                        [str(binary), "--skip-download", flag,
                         "--sub-langs", lang, "--sub-format", "json3/vtt", "--no-warnings",
                         "--no-playlist", "-o", out,
                         f"https://www.youtube.com/watch?v={video_id}"],
                        capture_output=True, timeout=180,
                    )
                except (subprocess.SubprocessError, OSError):
                    continue
                files = sorted(Path(tmp).glob("cap.*"))
                if files:
                    break
            if files:
                break
            time.sleep(3 + attempt * 4)  # backoff ante 429
        if not files:
            return None

        path = files[0]
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".json3":
            try:
                segments = parse_json3_events(json.loads(raw))
            except ValueError:
                segments = []
            provider = "yt_dlp_json3"
        else:
            segments = _segments_from_vtt(raw)
            provider = "yt_dlp_vtt"
        text = " ".join(seg.text for seg in segments) if segments else ""
        if not text.strip():
            return None
        return ContentDraft(
            content_type="TRANSCRIPT",
            text=text,
            is_verbatim=True,
            provider=provider,
            confidence="medium",  # subtítulos automáticos: no verificados por humanos
            segments=segments,
        )


def _segments_from_vtt(raw: str) -> list[SegmentDraft]:
    """Segmentos con tiempos a partir de un WebVTT (tolerante a CRLF, cabeceras
    y bloques con líneas de texto multilínea)."""
    segments: list[SegmentDraft] = []
    pattern = re.compile(
        r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*"
        r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
    )
    normalised = raw.replace("\r\n", "\n").replace("\r", "\n")
    current_time: int | None = None
    for line in normalised.split(chr(10)):
        match = pattern.search(line)
        if match:
            h, m, sec, ms = match.group(1), match.group(2), match.group(3), match.group(4)
            total = (int(h) * 3600 if h else 0) + int(m) * 60 + int(sec)
            current_time = total * 1000 + int(ms.ljust(3, "0"))
            continue
        if current_time is None:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")):
            continue
        text = re.sub(r"<[^>]+>", "", stripped).strip()
        if text:
            segments.append(SegmentDraft(text=text, start_ms=current_time,
                                         sequence=len(segments)))
    return segments
