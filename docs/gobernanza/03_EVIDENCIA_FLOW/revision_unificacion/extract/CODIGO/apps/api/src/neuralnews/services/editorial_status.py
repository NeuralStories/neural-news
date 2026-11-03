"""Estado editorial de una noticia: fuente de verdad compartida.

Este módulo evita que la web, el lote y el traspaso calculen estados distintos.
Reglas (ver `docs/EDITORIAL_STYLE.md` §3 y §5):

- **Etapa** (candidato → investigación → guion → aprobado) es distinta de
  **verificación** (afirmaciones con o sin evidencia).
- **Aprobación humana** es distinta de **disponibilidad para producción**: un
  guion puede estar aprobado y aun así quedar texto sin confirmar.
- **DEMO es procedencia**, no una palabra del titular: si no hay dato de
  procedencia, se informa «Origen no determinado»; nunca se afirma que un
  contenido es real sin saberlo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Claim, Evidence, ScriptVersion, Source, SourceContent, Story, StorySource

# --- Dimensiones de estado -------------------------------------------------

STAGE_LABELS = {
    "candidate": "Candidata",
    "research": "Investigación",
    "script": "Guion",
    "approved": "Aprobada",
    "rejected": "Descartada",
}

VERIFICATION_LABELS = {
    "unverified": "Sin verificar",
    "in_review": "En revisión",
    "verified": "Verificada",
    "disputed": "Con contradicciones",
    "opinion": "No verificable (opinión)",
}

APPROVAL_LABELS = {
    "not_requested": "No solicitada",
    "pending": "Pendiente de aprobación",
    "approved": "Aprobada por una persona",
    "superseded": "Anulada por una edición posterior",
}

ORIGIN_LABELS = {
    "real": "Contenido real",
    "demo": "Contenido ficticio (DEMO)",
    "manual": "Aportado a mano",
    "unknown": "Origen no determinado",
}

# Estados de verificación que cuentan como «respaldo suficiente».
# NOT_VERIFIABLE no es verificación: es una opinión (no comprobable).
VERIFIED_CLAIM_STATES = ("SUPPORTED",)


def stage_of(story: Story) -> str:
    if story.status in ("RESEARCHING", "REVIEW_REQUIRED"):
        return "research"
    if story.status == "SCRIPT_DRAFT":
        return "script"
    if story.status == "APPROVED":
        return "approved"
    if story.status == "REJECTED":
        return "rejected"
    return "candidate"


def verification_of(claims: list[Claim], is_opinion: bool) -> str:
    if is_opinion:
        return "opinion"
    if not claims:
        return "unverified"
    if any(c.verification_status == "CONTRADICTED" for c in claims):
        return "disputed"
    if any(c.verification_status not in VERIFIED_CLAIM_STATES for c in claims):
        return "in_review"
    return "verified"


def approval_of(
    versions: list[ScriptVersion],
    approved_version_id: int | None,
    pending_flag: bool,
) -> str:
    if not versions:
        return "not_requested"
    if approved_version_id is None:
        return "pending"
    latest = versions[-1]
    if approved_version_id != latest.id:
        return "superseded"
    return "pending" if pending_flag else "approved"


@dataclass
class StoryStatus:
    """Estado editorial completo de una noticia (lo que la UI debe mostrar)."""

    story_id: int
    stage: str
    verification: str
    approval: str
    origin: str
    provider: str | None = None
    claim_total: int = 0
    claim_verified: int = 0
    claim_unverified: int = 0
    claim_contradicted: int = 0
    claim_not_verifiable: int = 0
    approved_version_id: int | None = None
    approved_version: int | None = None
    latest_version: int | None = None
    script_version_id: int | None = None
    has_summary: bool = False
    source_count: int = 0
    usable_content: bool = False
    in_batch: bool = False
    batch_ids: list[int] = field(default_factory=list)
    # Motivos que impiden el traspaso a producción (vacío = apto).
    production_blockers: list[str] = field(default_factory=list)
    # Avisos visibles que no impiden el traspaso (verificación incompleta).
    production_warnings: list[str] = field(default_factory=list)

    @property
    def production_ready(self) -> bool:
        return self.approval == "approved" and not self.production_blockers

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "stage_label": STAGE_LABELS.get(self.stage, self.stage),
            "verification": self.verification,
            "verification_label": VERIFICATION_LABELS.get(self.verification, self.verification),
            "approval": self.approval,
            "approval_label": APPROVAL_LABELS.get(self.approval, self.approval),
            "origin": self.origin,
            "origin_label": ORIGIN_LABELS.get(self.origin, self.origin),
            "provider": self.provider,
            "claim_total": self.claim_total,
            "claim_verified": self.claim_verified,
            "claim_unverified": self.claim_unverified,
            "claim_contradicted": self.claim_contradicted,
            "claim_not_verifiable": self.claim_not_verifiable,
            "approved_version_id": self.approved_version_id,
            "approved_version": self.approved_version,
            "latest_version": self.latest_version,
            "script_version_id": self.script_version_id,
            "has_summary": self.has_summary,
            "source_count": self.source_count,
            "usable_content": self.usable_content,
            "in_batch": self.in_batch,
            "batch_ids": self.batch_ids,
            "production_ready": self.production_ready,
            "production_blockers": self.production_blockers,
            "production_warnings": self.production_warnings,
        }


def story_provenance(
    db: Session, story: Story, sources: list[Source], claims: list[Claim]
) -> tuple[str, str | None]:
    """Procedencia real (DEMO / manual / real / sin determinar) y proveedor técnico.

    DEMO gana si cualquier fuente o evidencia es ficticia. Si no hay ninguna
    fuente registrada, la procedencia es «no determinada» (no se inventa).
    """
    provider = sources[0].provider if sources else None
    demo_source = any(s.demo for s in sources)
    demo_evidence = False
    for claim in claims:
        for ev in claim.evidence if hasattr(claim, "evidence") else []:
            if ev.demo:
                demo_evidence = True
                break
    if demo_source or demo_evidence:
        return "demo", provider
    if not sources:
        return "unknown", None
    if all(s.provider == "manual" for s in sources):
        return "manual", provider
    return "real", provider


def production_blockers(
    *,
    approval: str,
    version: ScriptVersion | None,
    claims: list[Claim],
    has_summary: bool,
    is_opinion: bool,
) -> list[str]:
    """Motivos concretos que impiden el traspaso a producción.

    Regla de producto (contrastada con `EDITORIAL_STYLE.md` §3 y §5): el guion
    puede aprobarse y el lote editorial puede exportarse con advertencias, pero
    el traspaso a producción exige evidencia suficiente. Las opiniones no se
    penalizan por no ser verificables.
    """
    blockers: list[str] = []
    if version is None:
        blockers.append("La noticia no tiene guion")
        return blockers
    if approval == "not_requested":
        blockers.append("No hay ningún guion aprobado")
    elif approval == "pending":
        blockers.append(
            f"El guion v{version.version} está pendiente de aprobación humana"
        )
    elif approval == "superseded":
        blockers.append(
            f"La aprobación es de una versión anterior: vuelve a aprobar el guion v{version.version}"
        )
    if not has_summary:
        blockers.append("La noticia no tiene resumen editorial")
    if not is_opinion:
        contradicted = sum(1 for c in claims if c.verification_status == "CONTRADICTED")
        if contradicted:
            blockers.append(f"{contradicted} afirmación(es) contradichas por la evidencia")
    return blockers


def production_warnings(
    *,
    claims: list[Claim],
    is_opinion: bool,
    approval: str = "not_requested",
) -> list[str]:
    """Avisos que no impiden el traspaso pero deben verse junto a él.

    Una afirmación sin evidencia no se oculta: el guion puede estar aprobado
    (la revisión es humana) y aun así transportarse «con revisión pendiente».
    El texto se ajusta al estado real para no afirmar que hay un guion
    aprobado cuando todavía no lo hay.
    """
    warnings: list[str] = []
    if is_opinion:
        return warnings
    unverified = sum(1 for c in claims if c.verification_status == "UNVERIFIED")
    if unverified:
        detail = f"{unverified} afirmación(es) sin evidencia suficiente."
        if approval == "approved":
            detail += " El guion está aprobado, pero la verificación está incompleta."
        else:
            detail += " La verificación está incompleta."
        warnings.append(detail)
    return warnings


def build_story_status(
    db: Session,
    story: Story,
    *,
    versions: list[ScriptVersion] | None = None,
    claims: list[Claim] | None = None,
    approved_version_id: int | None = None,
    pending_flag: bool = False,
) -> StoryStatus:
    """Estado editorial completo de una noticia, con consultas agrupadas."""
    if versions is None:
        versions = list(
            db.scalars(
                select(ScriptVersion)
                .where(ScriptVersion.story_id == story.id)
                .order_by(ScriptVersion.version)
            ).all()
        )
    if claims is None:
        claims = list(db.scalars(select(Claim).where(Claim.story_id == story.id)).all())

    links = list(db.scalars(select(StorySource).where(StorySource.story_id == story.id)).all())
    sources = [db.get(Source, link.source_id) for link in links]
    sources = [s for s in sources if s is not None]

    origin, provider = story_provenance(db, story, sources, claims)
    latest = versions[-1] if versions else None
    approval = approval_of(versions, approved_version_id, pending_flag)
    has_summary = bool((story.summary or "").strip())

    usable_content = False
    for source in sources:
        contents = list(
            db.scalars(
                select(SourceContent).where(SourceContent.source_id == source.id)
            ).all()
        )
        if contents:
            usable_content = True
            break

    batch_ids = _batch_ids_for(db, story.id)

    blockers = production_blockers(
        approval=approval,
        version=latest,
        claims=claims,
        has_summary=has_summary,
        is_opinion=bool(story.is_opinion),
    )
    warnings = production_warnings(
        claims=claims, is_opinion=bool(story.is_opinion), approval=approval
    )

    return StoryStatus(
        story_id=story.id,
        stage=stage_of(story),
        verification=verification_of(claims, bool(story.is_opinion)),
        approval=approval,
        origin=origin,
        provider=provider,
        claim_total=len(claims),
        claim_verified=sum(1 for c in claims if c.verification_status in VERIFIED_CLAIM_STATES),
        claim_unverified=sum(1 for c in claims if c.verification_status == "UNVERIFIED"),
        claim_contradicted=sum(1 for c in claims if c.verification_status == "CONTRADICTED"),
        claim_not_verifiable=sum(1 for c in claims if c.verification_status == "NOT_VERIFIABLE"),
        approved_version_id=approved_version_id,
        approved_version=(
            next((v.version for v in versions if v.id == approved_version_id), None)
        ),
        latest_version=latest.version if latest else None,
        script_version_id=latest.id if latest else None,
        has_summary=has_summary,
        source_count=len(sources),
        usable_content=usable_content,
        in_batch=bool(batch_ids),
        batch_ids=batch_ids,
        production_blockers=blockers,
        production_warnings=warnings,
    )


def _batch_ids_for(db: Session, story_id: int) -> list[int]:
    from ..models import BatchItem

    rows = db.scalars(select(BatchItem).where(BatchItem.story_id == story_id)).all()
    return sorted({row.batch_id for row in rows})


def build_story_statuses(
    db: Session, stories: list[Story]
) -> dict[int, StoryStatus]:
    """Estado editorial de varias noticias con consultas agrupadas (sin N+1)."""
    if not stories:
        return {}
    story_ids = [s.id for s in stories]

    versions_by_story: dict[int, list[ScriptVersion]] = {sid: [] for sid in story_ids}
    for version in db.scalars(
        select(ScriptVersion).where(ScriptVersion.story_id.in_(story_ids)).order_by(ScriptVersion.version)
    ).all():
        versions_by_story[version.story_id].append(version)

    claims_by_story: dict[int, list[Claim]] = {sid: [] for sid in story_ids}
    for claim in db.scalars(select(Claim).where(Claim.story_id.in_(story_ids))).all():
        claims_by_story[claim.story_id].append(claim)

    claim_ids = [c.id for claims in claims_by_story.values() for c in claims]
    demo_claim_ids: set[int] = set()
    if claim_ids:
        for ev in db.scalars(select(Evidence).where(Evidence.claim_id.in_(claim_ids))).all():
            if ev.demo:
                demo_claim_ids.add(ev.claim_id)

    links_by_story: dict[int, list[Source]] = {sid: [] for sid in story_ids}
    for link in db.scalars(select(StorySource).where(StorySource.story_id.in_(story_ids))).all():
        source = db.get(Source, link.source_id)
        if source is not None:
            links_by_story[link.story_id].append(source)

    source_ids = [s.id for sources in links_by_story.values() for s in sources]
    usable_by_source: set[int] = set()
    if source_ids:
        for content in db.scalars(
            select(SourceContent).where(SourceContent.source_id.in_(source_ids))
        ).all():
            usable_by_source.add(content.source_id)

    from ..models import Approval, BatchItem

    approvals: dict[int, int] = {}
    for approval in db.scalars(
        select(Approval).where(Approval.story_id.in_(story_ids), Approval.status == "ACTIVE")
    ).all():
        approvals[approval.story_id] = approval.script_version_id

    batch_ids_by_story: dict[int, set[int]] = {sid: set() for sid in story_ids}
    for item in db.scalars(select(BatchItem).where(BatchItem.story_id.in_(story_ids))).all():
        batch_ids_by_story[item.story_id].add(item.batch_id)

    result: dict[int, StoryStatus] = {}
    for story in stories:
        versions = versions_by_story.get(story.id, [])
        claims = claims_by_story.get(story.id, [])
        sources = links_by_story.get(story.id, [])
        latest = versions[-1] if versions else None
        approval = approval_of(versions, approvals.get(story.id), False)

        demo_source = any(s.demo for s in sources)
        demo_evidence = any(c.id in demo_claim_ids for c in claims)
        if demo_source or demo_evidence:
            origin = "demo"
        elif not sources:
            origin = "unknown"
        elif all(s.provider == "manual" for s in sources):
            origin = "manual"
        else:
            origin = "real"

        has_summary = bool((story.summary or "").strip())
        blockers = production_blockers(
            approval=approval,
            version=latest,
            claims=claims,
            has_summary=has_summary,
            is_opinion=bool(story.is_opinion),
        )
        warnings = production_warnings(
            claims=claims, is_opinion=bool(story.is_opinion), approval=approval
        )
        result[story.id] = StoryStatus(
            story_id=story.id,
            stage=stage_of(story),
            verification=verification_of(claims, bool(story.is_opinion)),
            approval=approval,
            origin=origin,
            provider=sources[0].provider if sources else None,
            claim_total=len(claims),
            claim_verified=sum(
                1 for c in claims if c.verification_status in VERIFIED_CLAIM_STATES
            ),
            claim_unverified=sum(1 for c in claims if c.verification_status == "UNVERIFIED"),
            claim_contradicted=sum(
                1 for c in claims if c.verification_status == "CONTRADICTED"
            ),
            claim_not_verifiable=sum(
                1 for c in claims if c.verification_status == "NOT_VERIFIABLE"
            ),
            approved_version_id=approvals.get(story.id),
            approved_version=next(
                (v.version for v in versions if v.id == approvals.get(story.id)), None
            ),
            latest_version=latest.version if latest else None,
            script_version_id=latest.id if latest else None,
            has_summary=has_summary,
            source_count=len(sources),
            usable_content=any(s.id in usable_by_source for s in sources),
            in_batch=bool(batch_ids_by_story.get(story.id)),
            batch_ids=sorted(batch_ids_by_story.get(story.id, set())),
            production_blockers=blockers,
            production_warnings=warnings,
        )
    return result
