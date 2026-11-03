"""Conector web/RSS: artículos públicos y feeds RSS/Atom.

Implementación real (httpx + feedparser + BeautifulSoup), verificable contra
servidores de prueba locales. No ejecuta ni conserva HTML activo: el texto se
extrae como datos y se sanea.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup

from ..config import get_settings
from ..providers.safety import FetchBlocked, fetch_url_safely
from .base import ContentDraft, FetchResult, SegmentDraft
from .manual import split_paragraphs


def looks_like_feed(url: str, content_type: str, body: bytes) -> bool:
    if "rss" in url.lower() or "feed" in url.lower() or "atom" in url.lower():
        return True
    head = body[:512].lstrip().lower()
    if "xml" in content_type and (b"<rss" in head or b"<feed" in head):
        return True
    return head.startswith(b"<?xml") and (b"<rss" in body[:2048] or b"<feed" in body[:2048])


def sanitize_text(raw: str) -> str:
    """Convierte HTML a texto plano: el contenido es dato, nunca se ejecuta."""
    soup = BeautifulSoup(raw, "lxml")
    for tag in soup(["script", "style", "iframe", "object", "embed", "template"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value.strip(), fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def extract_article(html: str, base_url: str) -> dict:
    """Extrae título, autor, fecha, URL canónica y texto del artículo."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "iframe", "nav", "footer", "aside", "form", "template"]):
        tag.decompose()
    canonical = None
    link = soup.find("link", rel=lambda v: v and "canonical" in v)
    if link and link.get("href"):
        canonical = link["href"]
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    meta_title = soup.find("meta", attrs={"property": "og:title"})
    if not title and meta_title and meta_title.get("content"):
        title = meta_title["content"].strip()
    author = None
    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author and meta_author.get("content"):
        author = meta_author["content"].strip()
    published = None
    for attr, value in (("property", "article:published_time"), ("name", "date")):
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            published = _parse_date(tag["content"])
            if published:
                break
    time_tag = soup.find("time") if not published else None
    if time_tag:
        published = _parse_date(time_tag.get("datetime") or time_tag.get_text())
    article = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs = [p.get_text(" ", strip=True) for p in article.find_all(["p", "h2", "h3"])]
    text = "\n\n".join(p for p in paragraphs if len(p) > 20)
    if not text:
        text = sanitize_text(str(article))
    return {
        "title": title,
        "author": author,
        "published_at": published,
        "canonical": canonical,
        "text": text,
    }


def fetch_web(url: str) -> FetchResult:
    settings = get_settings()
    try:
        fetched = fetch_url_safely(url, settings)
    except FetchBlocked as exc:
        return FetchResult(provider="web_rss", canonical_url=url, status="FAILED", error=str(exc))
    if fetched.status >= 400:
        return FetchResult(
            provider="web_rss",
            canonical_url=url,
            status="FAILED",
            error=f"La página ha respondido con un error {fetched.status}",
        )
    body_text = fetched.body.decode("utf-8", errors="replace")

    if looks_like_feed(url, fetched.content_type, fetched.body):
        feed = feedparser.parse(body_text)
        items = feed.entries[:10]
        if not items:
            return FetchResult(
                provider="web_rss", canonical_url=url, status="FAILED",
                error="El feed no contiene elementos legibles",
            )
        first = items[0]
        contents = []
        for idx, item in enumerate(items[:1]):  # MVP: el feed crea una fuente por invocación con su elemento principal
            summary_html = item.get("content", [{}])[0].get("value") or item.get("summary", "")
            text = sanitize_text(summary_html) if summary_html else ""
            contents.append(
                ContentDraft(
                    content_type="ARTICLE_TEXT",
                    text=text,
                    is_verbatim=True,
                    provider="web_rss",
                    coverage=0.5 if summary_html else None,
                    confidence="medium",
                    segments=split_paragraphs(text) if text else [],
                )
            )
        published = None
        if getattr(first, "published_parsed", None):
            published = datetime(*first.published_parsed[:6], tzinfo=timezone.utc)
        return FetchResult(
            provider="web_rss",
            external_id=getattr(first, "id", None) or getattr(first, "link", None),
            canonical_url=getattr(first, "link", url),
            title=getattr(first, "title", None),
            author=getattr(first, "author", None),
            published_at=published,
            language=(feed.feed.get("language") if hasattr(feed, "feed") else None),
            status="PARTIAL" if (not contents[0].text) else "READY",
            error=None if contents[0].text else "El feed entrega el titular pero no el texto del artículo",
            contents=contents,
            metadata={"feed_url": url, "items_in_feed": len(items), "demo": False},
        )

    article = extract_article(body_text, url)
    if not article["text"]:
        return FetchResult(
            provider="web_rss", canonical_url=url, status="FAILED",
            error="No se ha encontrado texto de artículo legible en la página",
        )
    segments: list[SegmentDraft] = split_paragraphs(article["text"])
    return FetchResult(
        provider="web_rss",
        canonical_url=article["canonical"] or fetched.final_url,
        title=article["title"],
        author=article["author"],
        published_at=article["published_at"],
        language=None,
        status="READY",
        contents=[
            ContentDraft(
                content_type="ARTICLE_TEXT",
                text=article["text"],
                is_verbatim=True,
                provider="web_rss",
                coverage=None,
                confidence="high",
                segments=segments,
            )
        ],
        metadata={"fetched_url": url, "content_type": fetched.content_type, "demo": False},
    )


def detect_platform(url: str) -> str | None:
    """Detecta la plataforma a partir de la URL. Devuelve None si no se reconoce."""
    lowered = url.lower()
    if "youtube.com/" in lowered or "youtu.be/" in lowered:
        return "youtube"
    if "open.spotify.com/" in lowered or "spotify:" in lowered:
        return "spotify"
    if re.search(r"^https?://", lowered):
        return "web_rss"
    return None
