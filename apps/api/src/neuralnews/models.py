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
    error_kind: Mapped[str | None] = mapped_column(String(24), nullable=True)
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


class ProviderSecret(Base):
    """Secreto de proveedor **cifrado** con la clave maestra (NN-117.3).

    En la base de datos no hay ningún valor en claro: sólo el texto cifrado.
    El valor descifrado vive en memoria del proceso (`neuralnews.vault`).
    """

    __tablename__ = "provider_secrets"

    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


def dumps_compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


# ---------------------------------------------------------------------------
# NN-107 — Reintegración de Flow: proyecto de producción y Studio (subconjunto
# mínimo del cap. 13 de la especificación rectora). Una sola fuente de datos:
# todo lo que muestra el Studio se persiste aquí, nunca solo en el navegador.
# ---------------------------------------------------------------------------

STUDIO_STEPS = (
    "noticias",
    "personaje",
    "fondo",
    "guion",
    "voz",
    "movimiento",
    "referencias",
    "resultado",
)

TAKE_STATUSES = ("PLANIFICADA", "PROMPT_LISTO", "IMPORTADA", "APROBADA", "RECHAZADA")


class ProductionProject(Base):
    """Proyecto audiovisual sobre una historia editorial (una sola redacción).

    `ratio` se fija en la creación desde `format_profile` y ningún endpoint lo
    muta (R-BUG-2: crear el plan de producción nunca altera la proporción).
    `story_id` es la noticia activa: vincular o importar una historia la activa
    automáticamente (R-BUG-1).
    """

    __tablename__ = "production_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    story_id: Mapped[int | None] = mapped_column(ForeignKey("stories.id"), nullable=True, index=True)
    script_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("script_versions.id"), nullable=True
    )
    ratio: Mapped[str] = mapped_column(String(8), default="9:16")  # 9:16 | 16:9 — solo creación
    format_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    target_duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", index=True)
    step_revisions: Mapped[dict] = mapped_column(JSON, default=dict)  # {step: int}
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)

    step_history: Mapped[list["StudioStepRevision"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    beats: Mapped[list["NarrationBeat"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="NarrationBeat.sequence"
    )
    shots: Mapped[list["Shot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Shot.sequence"
    )
    takes: Mapped[list["GeneratedTake"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="GeneratedTake.id"
    )
    story: Mapped[Story | None] = relationship()
    script_version: Mapped[ScriptVersion | None] = relationship()


class StudioStepRevision(Base):
    """Revisión inmutable del estado de un paso del Studio (CAS + trazabilidad).

    Cada guardado inserta una fila nueva; las aprobaciones nunca se reescriben
    (cap. 13). `expected_revision` obsoleto → 409 en el endpoint.
    """

    __tablename__ = "studio_step_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    step: Mapped[str] = mapped_column(String(24), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    project: Mapped[ProductionProject] = relationship(back_populates="step_history")

    __table_args__ = (
        UniqueConstraint("project_id", "step", "revision", name="uq_step_revision"),
    )


class NarrationBeat(Base):
    """Unidad de sentido de la locución. Independiente de las ventanas de vídeo
    (F-05: el audio no se corta cada 8 s; eso es capacidad del proveedor)."""

    __tablename__ = "narration_beats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    est_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    claim_ids: Mapped[list] = mapped_column(JSON, default=list)
    emphasis: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[ProductionProject] = relationship(back_populates="beats")


class Shot(Base):
    """Ventana visual: puede cubrir varios beats o ser cubierta por varios."""

    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    beat_id: Mapped[int | None] = mapped_column(ForeignKey("narration_beats.id"), nullable=True)
    shot_kind: Mapped[str] = mapped_column(String(32), default="PENDING")
    # USER_VIDEO|FLOW_MAXDOTAI|DOCUMENTARY|DATA_GRAPHIC|GENERATIVE_BROLL|TITLE_CARD|PENDING
    rationale: Mapped[str | None] = mapped_column(Text)
    start_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped[ProductionProject] = relationship(back_populates="shots")
    beat: Mapped[NarrationBeat | None] = relationship()


class CharacterProfile(Base):
    """Ficha de identidad del presentador (ficha maestra). maxDotAi es el único
    personaje generativo previsto; sin activos vinculados queda PENDING_ASSET."""

    __tablename__ = "character_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_projects.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING_ASSET")
    # PENDING_ASSET|PENDING_DE_VINCULAR|VINCULADO|RECHAZADO
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class VoiceProfile(Base):
    """Perfil de locución configurable. El prototipo «Algenib» es hipótesis, no
    calibración confirmada (F-04): velocidad editable y marcada."""

    __tablename__ = "voice_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_projects.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    locale: Mapped[str] = mapped_column(String(16), default="es-ES")
    speed_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(24), default="HYPOTHESIS")
    # HYPOTHESIS|AUTHORIZED|REJECTED
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class SetProfile(Base):
    """Plató/fondo con referencia visual verdadera; el texto de un prompt no
    garantiza recreación exacta (cap. 6.3)."""

    __tablename__ = "set_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_projects.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    ratio: Mapped[str] = mapped_column(String(8), default="9:16")
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class MediaAsset(Base):
    """Activo binario en el almacén direccionado por contenido. En DB solo
    metadatos: el archivo vive en storage/media/{sha256[:2]}/{sha256}{ext}."""

    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    filename: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(1024))
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    orientation: Mapped[str | None] = mapped_column(String(8), nullable=True)
    has_audio: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    probe_status: Mapped[str] = mapped_column(String(16), default="UNKNOWN")  # OK|UNAVAILABLE|FAILED
    provenance: Mapped[str] = mapped_column(String(32), default="imported_flow_manual")
    license_state: Mapped[str] = mapped_column(String(24), default="PENDING")
    # PENDING|APPROVED|REJECTED — aprobación humana, nunca automática (F-02)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    approvals: Mapped[list["MediaApproval"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class MediaApproval(Base):
    __tablename__ = "media_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id"), index=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24))  # APPROVED|REJECTED
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    asset: Mapped[MediaAsset] = relationship(back_populates="approvals")


class PromptPackage(Base):
    """Prompt reproducible por toma (cap. 9): orden fijo, referencias con hash
    y checklist. Editable; cada edición crea versión (cap. 13)."""

    __tablename__ = "prompt_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    take_id: Mapped[int | None] = mapped_column(
        ForeignKey("generated_takes.id"), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    prompt_en: Mapped[str] = mapped_column(Text)
    explanation_es: Mapped[str | None] = mapped_column(Text)
    constraints: Mapped[list] = mapped_column(JSON, default=list)
    attachments_manifest: Mapped[list] = mapped_column(JSON, default=list)
    checklist: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    """Hash del propio texto del prompt."""
    source_script_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Hash del guion del proyecto al compilar: permite invalidación exclusiva
    (solo los prompts que dependían del texto cambiado requieren revisión)."""
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    take: Mapped[GeneratedTake | None] = relationship(back_populates="prompts")

    __table_args__ = (UniqueConstraint("take_id", "version", name="uq_prompt_take_version"),)


class GraphicSpec(Base):
    """Gráfico programático con datos exactos de claims aprobados (cap. 11).
    Nunca se pide a un generativo que invente cifras."""

    __tablename__ = "graphic_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    chart_type: Mapped[str] = mapped_column(String(24), default="BAR")
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # series con unidad y fuente
    spec: Mapped[dict] = mapped_column(JSON, default=dict)  # plantilla, escala, easing…
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class GeneratedTake(Base):
    """Toma del plan. `IMPORTADA` solo tras subir el MP4; `APROBADA` solo por
    revisión humana. Un prompt listo nunca equivale a vídeo generado (cap. 13)."""

    __tablename__ = "generated_takes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    shot_id: Mapped[int | None] = mapped_column(ForeignKey("shots.id"), nullable=True, index=True)
    take_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default="PLANIFICADA", index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    """El guion cambió tras compilarse su prompt: requiere revisión sin regenerar."""
    imported_media_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id"), nullable=True, index=True
    )
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    project: Mapped[ProductionProject] = relationship(back_populates="takes")
    shot: Mapped[Shot | None] = relationship()
    imported_media: Mapped[MediaAsset | None] = relationship()
    prompts: Mapped[list["PromptPackage"]] = relationship(
        back_populates="take", cascade="all, delete-orphan", order_by="PromptPackage.version"
    )


class BatchBudget(Base):
    """Techo de presupuesto de un lote (portado de la integración del 29/10).

    `limit_eur` es el tope agregado; `committed_eur` lo reservado por trabajos
    encolados; al liquidar se pasa a `spent_eur`.
    """

    __tablename__ = "batch_budgets"

    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    limit_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    committed_eur: Mapped[float] = mapped_column(Float, default=0.0)
    spent_eur: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class RenderOutput(Base):
    """Salida del montaje técnico local (portado del 29/10). AVISO: el motor
    FFmpeg actual es una simulación (color/rótulos/tono); nunca se presenta como
    montaje audiovisual real (cap. 11)."""

    __tablename__ = "render_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("production_projects.id"), index=True)
    plan_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    output_format: Mapped[str] = mapped_column(String(8))  # 9:16 | 16:9
    mime_type: Mapped[str] = mapped_column(String(64), default="video/mp4")
    storage_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64))
    duration_s: Mapped[float] = mapped_column(Float)
    scene_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
