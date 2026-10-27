"""Esquemas de petición/respuesta de la API v1 (Pydantic v2)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class MeResponse(BaseModel):
    actor_id: str
    is_demo: bool
    demo_mode: bool


class SourceCreate(BaseModel):
    url: str | None = None
    text: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    transcript: str | None = None


class SourceOut(BaseModel):
    id: int
    provider: str
    external_id: str | None
    canonical_url: str | None
    title: str | None
    author: str | None
    published_at: datetime | None
    imported_at: datetime
    language: str | None
    status: str
    status_label: str
    demo: bool
    metadata: dict


class SourceDetailOut(SourceOut):
    contents: list[dict] = Field(default_factory=list)
    stories: list[dict] = Field(default_factory=list)


class ContentOut(BaseModel):
    id: int
    content_type: str
    content_type_label: str
    is_verbatim: bool
    provider: str | None
    model: str | None
    coverage: float | None
    confidence: str | None
    extracted_at: datetime
    char_count: int
    segment_count: int


class StoryRefOut(BaseModel):
    id: int
    title: str
    status: str
    status_label: str


class ProcessRequest(BaseModel):
    note: str | None = None


class StoryOut(BaseModel):
    id: int
    topic_key: str
    title: str
    summary: str | None
    status: str
    status_label: str
    editorial_score: float | None
    score_breakdown: dict
    is_opinion: bool
    original_event_date: datetime | None
    created_at: datetime


class StoryDetailOut(StoryOut):
    sources: list[dict]
    claims: list["ClaimOut"]
    script_versions: list["ScriptVersionOut"]
    active_approval: dict | None
    pending_approval_flag: bool


class ClaimOut(BaseModel):
    id: int
    statement: str
    verification_status: str
    verification_notes: str | None
    evidence: list["EvidenceOut"]


class EvidenceOut(BaseModel):
    id: int
    url: str | None
    publisher: str | None
    published_at: datetime | None
    retrieved_at: datetime
    excerpt_or_paraphrase: str | None
    kind: str
    confidence: str
    demo: bool


class ScriptVersionOut(BaseModel):
    id: int
    version: int
    content: str
    target_duration_s: int | None
    language: str
    author_type: str
    created_at: datetime
    content_hash: str


class ScriptPatch(BaseModel):
    content: str = Field(min_length=1)
    expected_version: int = Field(ge=0)


class ApproveRequest(BaseModel):
    script_version_id: int


class RejectRequest(BaseModel):
    reason: str = ""


class BatchCreate(BaseModel):
    name: str = ""
    target_size: Literal[5, 10]
    story_ids: list[int]


class BatchOut(BaseModel):
    id: int
    name: str
    target_size: int
    status: str
    created_at: datetime


class JobOut(BaseModel):
    id: int
    type: str
    status: str
    status_label: str
    attempt: int
    progress: str | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
    payload: dict


class BudgetUpdate(BaseModel):
    paid_services_enabled: bool | None = None
    daily_limit_eur: float | None = Field(default=None, ge=0)


class ProviderStatusOut(BaseModel):
    key: str
    name: str
    configured: bool
    state: str  # mock|implementado|probado|error
    note: str


SourceDetailOut.model_rebuild()
