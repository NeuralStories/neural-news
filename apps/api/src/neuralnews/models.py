"""Modelo de datos (SQLAlchemy 2.0). Compatible con SQLite (desarrollo/demo) y PostgreSQL."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime que garantizaAware-UTC al leer (SQLite devuelve naive)."""

    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Base(DeclarativeBase):
    pass


def _json_default(value: object) -> str:
    raise TypeError(type(value))


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)  # youtube|spotify|web_rss|manual
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    imported_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    language: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="NEW")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)

    contents: Mapped[list["SourceContent"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_sources_provider_external"),
    )


class SourceContent(Base):
    __tablename__ = "source_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    content_type: Mapped[str] = mapped_column(String(32))  # TRANSCRIPT|VIDEO_ANALYSIS|...
    is_verbatim: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)
    coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(16))  # high|medium|low
    extracted_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    content_hash: Mapped[str] = mapped_column(String(64))

    source: Mapped[Source] = relationship(back_populates="contents")
    segments: Mapped[list["SourceSegment"]] = relationship(
        back_populates="content", cascade="all, delete-orphan", order_by="SourceSegment.sequence"
    )


class SourceSegment(Base):
    __tablename__ = "source_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("source_contents.id"), index=True)
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    content: Mapped[SourceContent] = relationship(back_populates="segments")


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_key: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text)
    original_event_date: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(24), default="CANDIDATE", index=True)
    editorial_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    is_opinion: Mapped[bool] = mapped_column(Boolean, default=False)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)

    sources: Mapped[list["StorySource"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    script_versions: Mapped[list["ScriptVersion"]] = relationship(
        back_populates="story", cascade="all, delete-orphan", order_by="ScriptVersion.version"
    )


class StorySource(Base):
    __tablename__ = "story_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    segment_id: Mapped[int | None] = mapped_column(ForeignKey("source_segments.id"), nullable=True)
    relevance: Mapped[str | None] = mapped_column(String(16))  # primary|supporting|mention

    story: Mapped[Story] = relationship(back_populates="sources")
    source: Mapped[Source] = relationship()
    segment: Mapped[SourceSegment | None] = relationship()


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(24), default="UNVERIFIED")
    verification_notes: Mapped[str | None] = mapped_column(Text)

    story: Mapped[Story] = relationship(back_populates="claims")
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    excerpt_or_paraphrase: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(24), default="REFERENCE")  # PRIMARY|CORROBORATION|CONTRADICTING|REFERENCE
    confidence: Mapped[str] = mapped_column(String(16), default="medium")
    demo: Mapped[bool] = mapped_column(Boolean, default=False)

    claim: Mapped[Claim] = relationship(back_populates="evidence")


class ScriptVersion(Base):
    __tablename__ = "script_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    target_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="es-ES")
    author_type: Mapped[str] = mapped_column(String(16), default="AI")  # AI|HUMAN
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    content_hash: Mapped[str] = mapped_column(String(64))

    story: Mapped[Story] = relationship(back_populates="script_versions")

    __table_args__ = (UniqueConstraint("story_id", "version", name="uq_script_version"),)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    script_version_id: Mapped[int] = mapped_column(ForeignKey("script_versions.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    approved_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE")  # ACTIVE|INVALIDATED|REVOKED

    script_version: Mapped[ScriptVersion] = relationship()


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    target_size: Mapped[int] = mapped_column(Integer)  # 5|10
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    items: Mapped[list["BatchItem"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan", order_by="BatchItem.position"
    )


class BatchItem(Base):
    __tablename__ = "batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), index=True)
    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    batch: Mapped[Batch] = relationship(back_populates="items")
    story: Mapped[Story] = relationship()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(24), default="QUEUED", index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    lease_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    progress: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class ProductionPackage(Base):
    __tablename__ = "production_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), nullable=True, index=True)
    story_id: Mapped[int | None] = mapped_column(ForeignKey("stories.id"), nullable=True, index=True)
    package_version: Mapped[int] = mapped_column(Integer, default=1)
    mime_type: Mapped[str] = mapped_column(String(64), default="application/zip")
    storage_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="EXPORTED")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[str | None] = mapped_column(String(128))
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    cost_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    event: Mapped[str] = mapped_column(String(64))  # call|blocked|error
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Setting(Base):
    """Clave/valor para preferencias editoriales, presupuesto y pesos de puntuación."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


def dumps_compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
