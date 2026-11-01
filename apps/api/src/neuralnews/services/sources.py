"""Servicio de fuentes: alta con deduplicación, obtención de contenido y extracción.

Regla clave: una URL repetida no crea una segunda fuente; procesar dos veces no
duplica trabajos ni candidatos (topic_key + dedupe_key).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..errors import safe_error
from ..models import (
    Claim,
    Source,
    SourceContent,
    SourceSegment,
    Story,
    StorySource,
    content_hash,
    utcnow,
)
from ..providers import youtube as yt
from ..providers.base import ContentDraft, FetchResult
from ..providers.llm import EditorialLLMProvider, EditorialLLMError
from ..providers.manual import fetch_manual, normalize_input
from ..providers.spotify import fetch_spotify
from ..providers.web_rss import fetch_web
from ..states import SOURCE_TRANSITIONS, STORY_TRANSITIONS, assert_transition

logger = logging.getLogger(__name__)


class DuplicateSource(ValueError):
    def __init__(self, source: Source, message: str) -> None:
        super().__init__(message)
        self.source = source


class SourceNotAnalyzable(RuntimeError):
    """La fuente sólo tiene información básica: no hay contenido del que extraer noticias.

    No es un fallo reintentable: es el resultado esperado de un episodio o vídeo sin
    transcripción. El trabajo termina con este mensaje y la fuente queda METADATA_ONLY.
    """


def detect_and_normalize(url: str) -> tuple[str, str | None]:
    """Devuelve (provider, external_id) y normaliza la URL canónica de la plataforma."""
    lowered = url.strip().lower()
    if "youtube.com/" in lowered or "youtu.be/" in lowered:
        video_id = yt.extract_video_id(url.strip())
        if video_id:
            return "youtube", video_id
        return "youtube", None
    if "open.spotify.com/" in lowered:
        from ..providers.spotify import extract_episode_id

        episode_id = extract_episode_id(url.strip())
        return "spotify", episode_id
    if lowered.startswith("http"):
        return "web_rss", None
    raise ValueError("No se reconoce la URL; pega un enlace de YouTube, Spotify o una página web")


def create_source(
    db: Session,
    *,
    url: str | None = None,
    text: str | None = None,
    title: str | None = None,
    author: str | None = None,
    published_at: datetime | None = None,
    transcript: str | None = None,
    demo: bool | None = None,
) -> Source:
    """Crea (o devuelve si ya existe) una fuente a partir de URL o texto manual."""
    settings = get_settings()
    demo_mode = settings.demo_mode if demo is None else demo

    if url and url.strip():
        provider, external_id = detect_and_normalize(url.strip())
        if provider == "youtube" and external_id:
            canonical_url = yt.normalize_video_url(external_id)
        elif provider == "spotify" and external_id:
            canonical_url = f"https://open.spotify.com/episode/{external_id}"
        else:
            canonical_url = url.strip()

        existing = None
        if external_id:
            existing = db.scalar(
                select(Source).where(Source.provider == provider, Source.external_id == external_id)
            )
        if existing is None:
            existing = db.scalar(select(Source).where(Source.canonical_url == canonical_url))
        if existing is not None:
            raise DuplicateSource(existing, "Esta fuente ya estaba registrada; se ha abierto la existente")

        source = Source(
            provider=provider,
            external_id=external_id,
            canonical_url=canonical_url,
            title=title,
            author=author,
            published_at=published_at,
            language="es",
            status="NEW",
            demo=demo_mode,
            metadata_json={"original_url": url.strip()},
        )
        db.add(source)
        db.flush()
        if transcript and transcript.strip():
            _store_content(db, source, ContentDraft(
                content_type="TRANSCRIPT",
                text=transcript.strip(),
                is_verbatim=True,
                provider="manual",
                coverage=1.0,
                confidence="high",
            ))
        return source

    if text and text.strip():
        clean_url, clean_text = normalize_input(None, text)
        digest = content_hash(clean_text)
        existing_content = db.scalar(select(SourceContent).where(SourceContent.content_hash == digest))
        if existing_content is not None:
            existing = db.get(Source, existing_content.source_id)
            raise DuplicateSource(existing, "Ese texto ya se había registrado antes; se ha abierto la fuente existente")
        source = Source(
            provider="manual",
            external_id=None,
            canonical_url=clean_url,
            title=title or "Texto aportado",
            author=author,
            published_at=published_at,
            language="es",
            status="NEW",
            demo=demo_mode,
            metadata_json={"input": "text"},
        )
        db.add(source)
        db.flush()
        _store_content(db, source, ContentDraft(
            content_type="MANUAL_TEXT",
            text=clean_text,
            is_verbatim=True,
            provider="manual",
            coverage=1.0,
            confidence="high",
        ))
        # Una transcripción aportada se guarda TAMBIÉN como TRANSCRIPT: antes se
        # perdía en silencio en esta rama (hallazgo B2, NN-109.2).
        if transcript and transcript.strip():
            _store_content(db, source, ContentDraft(
                content_type="TRANSCRIPT",
                text=transcript.strip(),
                is_verbatim=True,
                provider="manual",
                coverage=1.0,
                confidence="high",
            ))
        return source

    raise ValueError("Aporta una URL o pega un texto para registrar la fuente")


def _store_content(db: Session, source: Source, draft: ContentDraft) -> SourceContent:
    content = SourceContent(
        source_id=source.id,
        content_type=draft.content_type,
        is_verbatim=draft.is_verbatim,
        provider=draft.provider,
        model=draft.model,
        text=draft.text,
        coverage=draft.coverage,
        confidence=draft.confidence,
        content_hash=content_hash(draft.text),
    )
    db.add(content)
    db.flush()
    for segment in draft.segments:
        db.add(
            SourceSegment(
                content_id=content.id,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=segment.text,
                sequence=segment.sequence,
            )
        )
    return content


def run_fetch(db: Session, source: Source) -> Source:
    """Ejecuta el conector correspondiente y guarda lo conseguido (o el error)."""
    settings = get_settings()
    assert_transition("source", source.status, "FETCHING")
    source.status = "FETCHING"
    db.flush()

    demo = source.demo or settings.demo_mode
    try:
        if source.provider == "youtube":
            result = fetch_youtube_with_contents(db, source, demo=demo)
        elif source.provider == "spotify":
            result = fetch_spotify(source.canonical_url or source.metadata_json.get("original_url", ""), demo=demo)
        elif source.provider == "web_rss":
            result = fetch_web(source.canonical_url or source.metadata_json.get("original_url", ""))
        elif source.provider == "manual":
            content = db.scalar(
                select(SourceContent).where(SourceContent.source_id == source.id).limit(1)
            )
            result = fetch_manual(source, content.text if content else "")
        else:
            result = FetchResult(
                provider=source.provider, status="FAILED", error="Conector no disponible"
            )
    except Exception as exc:  # error del conector: se registra, la fuente no se pierde
        source.status = "FAILED"
        # `metadata_json` se devuelve al cliente en GET /sources, así que NO se guarda
        # ahí el texto crudo de la excepción: puede contener rutas del sistema o
        # stderr de herramientas. El detalle completo queda en el log (hallazgo B7).
        logger.exception("Fallo del conector al procesar la fuente %s", source.id)
        source.metadata_json = {**source.metadata_json, "last_error": safe_error(exc)}
        raise

    if result.title and not source.title:
        source.title = result.title
    if result.author and not source.author:
        source.author = result.author
    if result.published_at and not source.published_at:
        source.published_at = result.published_at
    if result.language:
        source.language = result.language

    new_contents = 0
    existing_hashes = {
        c.content_hash
        for c in db.scalars(select(SourceContent).where(SourceContent.source_id == source.id))
    }
    for draft in result.contents:
        if content_hash(draft.text) in existing_hashes:
            continue
        _store_content(db, source, draft)
        new_contents += 1

    if result.status == "FAILED":
        source.status = "FAILED"
        source.metadata_json = {**source.metadata_json, "last_error": result.error}
    else:
        has_transcript_or_text = db.scalar(
            select(SourceContent.id).where(
                SourceContent.source_id == source.id,
                SourceContent.content_type.in_(["TRANSCRIPT", "ARTICLE_TEXT", "MANUAL_TEXT", "VIDEO_ANALYSIS"]),
            )
        )
        if has_transcript_or_text:
            source.status = "READY" if result.status == "READY" else "PARTIAL"
        else:
            source.status = "METADATA_ONLY"
    source.metadata_json = {
        **source.metadata_json,
        "last_fetch": utcnow().isoformat(),
        "fetch_status": result.status,
        "new_contents": new_contents,
    }
    db.flush()
    return source


def fetch_youtube_with_contents(db: Session, source: Source, *, demo: bool) -> FetchResult:
    """YouTube: en demo devuelve transcripción simulada + análisis; en real, metadatos."""
    from ..providers.youtube import fetch_youtube

    return fetch_youtube(source.canonical_url or source.metadata_json.get("original_url", ""), demo=demo)


def extract_stories_from_source(db: Session, source: Source) -> list[Story]:
    """Extrae candidatos del contenido disponible y los deduplica por topic_key."""
    llm = EditorialLLMProvider()
    contents = db.scalars(
        select(SourceContent)
        .where(SourceContent.source_id == source.id)
        .order_by(SourceContent.id)
    ).all()
    analyzable = [c for c in contents if c.content_type != "METADATA_ONLY"]
    if not analyzable:
        raise SourceNotAnalyzable(
            "Esta fuente solo tiene información básica; añade una transcripción o un análisis "
            "antes de buscar noticias"
        )

    created: list[Story] = []
    opinion_ya_registrada = False
    for content in analyzable:
        try:
            drafts = llm.extract_stories(content.text, published_at=source.published_at)
        except EditorialLLMError as exc:
            source.metadata_json = {**source.metadata_json, "last_extraction_error": str(exc)}
            raise
        for draft in drafts:
            if draft.is_opinion:
                # Una sola opinión por fuente: un vídeo con transcripción y análisis
                # no debe generar dos candidatos de opinión idénticos.
                if opinion_ya_registrada:
                    continue
                opinion_ya_registrada = True
            story = _upsert_story(db, source, content, draft)
            if story is not None:
                created.append(story)
    db.flush()
    return created


def _upsert_story(db: Session, source: Source, content: SourceContent, draft) -> Story | None:
    """Crea la noticia o la fusiona con una existente del mismo tema conservando referencias."""
    existing = db.scalar(select(Story).where(Story.topic_key == draft.topic_key))
    segments = db.scalars(
        select(SourceSegment).where(SourceSegment.content_id == content.id).order_by(SourceSegment.sequence)
    ).all()

    if existing is not None:
        story = existing
        if draft.neutral_summary and (not story.summary or len(draft.neutral_summary) > len(story.summary)):
            story.summary = draft.neutral_summary
        already_linked = db.scalar(
            select(StorySource.id).where(
                StorySource.story_id == story.id, StorySource.source_id == source.id
            )
        )
        if already_linked is None:
            db.add(
                StorySource(
                    story_id=story.id,
                    source_id=source.id,
                    segment_id=(segments[0].id if segments else None),
                    relevance="supporting",
                )
            )
        return story

    story = Story(
        topic_key=draft.topic_key,
        title=draft.provisional_title,
        summary=draft.neutral_summary,
        original_event_date=draft.event_date,
        status="CANDIDATE",
        is_opinion=draft.is_opinion,
        demo=source.demo,
    )
    db.add(story)
    db.flush()
    db.add(
        StorySource(
            story_id=story.id,
            source_id=source.id,
            segment_id=(segments[0].id if segments else None),
            relevance="primary",
        )
    )
    for fact in draft.facts:
        segment_id = None
        if fact.segment_sequence is not None and 0 <= fact.segment_sequence < len(segments):
            segment_id = segments[fact.segment_sequence].id
        elif fact.quote_or_reference:
            match = next((s for s in segments if fact.quote_or_reference.lower() in s.text.lower()), None)
            segment_id = match.id if match else None
        db.add(
            Claim(
                story_id=story.id,
                statement=fact.statement,
                verification_status="NOT_VERIFIABLE" if draft.is_opinion else "UNVERIFIED",
                verification_notes=None,
            )
        )
    return story


def transition_source(db: Session, source: Source, target: str) -> None:
    assert_transition("source", source.status, target)
    source.status = target
    db.flush()
