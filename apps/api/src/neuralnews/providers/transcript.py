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
import re
import xml.etree.ElementTree as ET

import httpx
import feedparser

from ..config import get_settings
from ..providers.base import ContentDraft, SegmentDraft
from ..providers.safety import FetchBlocked, fetch_url_safely

PREFERRED_LANGS = ("es", "es-419", "es-ES", "en", "en-US")


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
