"""Contratos tipados entre capas. Toda salida de LLM o conector se valida con estos modelos."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContentKind = Literal[
    "TRANSCRIPT",
    "VIDEO_ANALYSIS",
    "ARTICLE_TEXT",
    "MANUAL_TEXT",
    "AUDIO_FILE",
    "METADATA_ONLY",
]
Verification = Literal["UNVERIFIED", "SUPPORTED", "CONTRADICTED", "NOT_VERIFIABLE"]


class SegmentDraft(BaseModel):
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    sequence: int = 0


class ContentDraft(BaseModel):
    content_type: ContentKind
    text: str
    is_verbatim: bool = False
    provider: str | None = None
    model: str | None = None
    coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: Literal["high", "medium", "low"] | None = None
    segments: list[SegmentDraft] = Field(default_factory=list)


class FetchResult(BaseModel):
    provider: str
    external_id: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    status: Literal["READY", "PARTIAL", "METADATA_ONLY", "FAILED"]
    error: str | None = None
    contents: list[ContentDraft] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class FactDraft(BaseModel):
    statement: str
    quote_or_reference: str | None = None
    segment_sequence: int | None = None
    start_ms: int | None = None


class StoryDraft(BaseModel):
    """Contrato de extracción (documento, §8). Campos ausentes = null, nunca inventados."""

    provisional_title: str
    neutral_summary: str
    facts: list[FactDraft] = Field(default_factory=list)
    source_published_at: datetime | None = None
    event_date: datetime | None = None
    entities: list[str] = Field(default_factory=list)
    questions_to_verify: list[str] = Field(default_factory=list)
    evidence_state: Literal["WITHOUT_CONFIRMATION", "PARTIAL", "CONFIRMED"] = "WITHOUT_CONFIRMATION"
    is_opinion: bool = False
    topic_key: str
    novelty: Literal["NEW_EVENT", "UPDATE", "ANALYSIS", "OPINION"] = "NEW_EVENT"


class ClaimDraft(BaseModel):
    statement: str


class EvidenceDraft(BaseModel):
    url: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    excerpt_or_paraphrase: str | None = None
    kind: Literal["PRIMARY", "CORROBORATION", "CONTRADICTING", "REFERENCE"] = "REFERENCE"
    confidence: Literal["high", "medium", "low"] = "medium"


class ClaimResearchDraft(BaseModel):
    claim: str
    verification_status: Verification
    verification_notes: str | None = None
    evidence: list[EvidenceDraft] = Field(default_factory=list)


class ResearchDraft(BaseModel):
    """Contrato de investigación: sólo enlaces recuperados de verdad; nunca citas inventadas."""

    claims: list[ClaimResearchDraft] = Field(default_factory=list)


class ScriptSceneDraft(BaseModel):
    message: str
    seconds: int = 8
    visual: str
    data_source: str | None = None
    image_prompt: str
    overlay_text: str | None = None


class ScriptDraft(BaseModel):
    """Contrato de redacción: titular, gancho, hechos, utilidad, matiz y cierre."""

    title: str
    content: str
    target_duration_s: int = 40
    language: str = "es-ES"


class StoryboardDraft(BaseModel):
    scenes: list[ScriptSceneDraft] = Field(default_factory=list)
