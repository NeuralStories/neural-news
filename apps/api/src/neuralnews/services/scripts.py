"""Guiones: versiones con hash, control de concurrencia y aprobación humana.

La aprobación queda vinculada a una versión exacta (id + hash de contenido).
Crear una nueva versión anula la aprobación vigente: hay que volver a aprobar.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    Approval,
    AuditLog,
    Claim,
    ScriptVersion,
    Story,
    content_hash,
    utcnow,
)
from ..providers.image_prompt import estimate_duration
from ..providers.llm import EditorialLLMProvider, EditorialLLMError
from ..states import APPROVAL_LABELS, STORY_TRANSITIONS, assert_transition


class ScriptConflict(Exception):
    def __init__(self, message: str, current_version: int) -> None:
        super().__init__(message)
        self.current_version = current_version


def latest_version(db: Session, story_id: int) -> ScriptVersion | None:
    return db.scalar(
        select(ScriptVersion)
        .where(ScriptVersion.story_id == story_id)
        .order_by(ScriptVersion.version.desc())
        .limit(1)
    )


def active_approval(db: Session, story_id: int) -> Approval | None:
    return db.scalar(
        select(Approval)
        .where(Approval.story_id == story_id, Approval.status == "ACTIVE")
        .order_by(Approval.approved_at.desc())
        .limit(1)
    )


def create_draft_version(db: Session, story: Story, actor_id: str = "system") -> ScriptVersion:
    """Genera el primer borrador automático. Si ya existe uno idéntico, garantiza sólo el estado."""
    claims = db.scalars(select(Claim).where(Claim.story_id == story.id)).all()
    llm = EditorialLLMProvider()
    try:
        draft = llm.draft_script(story, [c.statement for c in claims], target_duration_s=40)
    except EditorialLLMError as exc:
        raise RuntimeError(str(exc)) from exc
    return _add_version(db, story, content=draft.content, author_type="AI", actor_id=actor_id, allow_identical=True)


def _add_version(
    db: Session,
    story: Story,
    *,
    content: str,
    author_type: str,
    actor_id: str,
    target_duration_s: int | None = None,
    allow_identical: bool = False,
) -> ScriptVersion:
    if not content or not content.strip():
        raise ValueError("El guion está vacío; escribe algún texto antes de guardar")
    current = latest_version(db, story.id)
    if current and current.content_hash == content_hash(content.strip()):
        if allow_identical:
            _ensure_script_draft_state(db, story)
            return current
        raise ValueError("Ese texto es idéntico a la versión actual; no se crea una versión repetida")
    return _create_version(db, story, content=content, author_type=author_type, actor_id=actor_id, target_duration_s=target_duration_s)


def _ensure_script_draft_state(db: Session, story: Story) -> None:
    if story.status in ("APPROVED", "REVIEW_REQUIRED", "CANDIDATE", "RESEARCHING"):
        if story.status == "APPROVED":
            approval = active_approval(db, story.id)
            if approval is not None:
                approval.status = "INVALIDATED"
        assert_transition("story", story.status, "SCRIPT_DRAFT")
        story.status = "SCRIPT_DRAFT"


def _create_version(
    db: Session,
    story: Story,
    *,
    content: str,
    author_type: str,
    actor_id: str,
    target_duration_s: int | None,
) -> ScriptVersion:
    """Crea una versión de guion con un número **único**.

    El número se calcula como «el último + 1», lo que tiene una ventana de
    carrera: dos borradores simultáneos sobre la misma noticia calculan el mismo
    número y chocan con la restricción UNIQUE
    (`script_versions.story_id, script_versions.version`). Cuando eso pasaba, la
    sesión quedaba rota y el trabajo se perdía con un error interno.

    Ahora el intento se hace dentro de un *savepoint*: si choca, sólo se
    revierte ese savepoint (la transacción del manejador sigue viva) y se
    recalcula el número (hallazgo B24).
    """
    for _intento in range(3):
        current = latest_version(db, story.id)
        version_number = (current.version if current else 0) + 1
        _ensure_script_draft_state(db, story)
        try:
            with db.begin_nested():
                version = ScriptVersion(
                    story_id=story.id,
                    version=version_number,
                    content=content.strip(),
                    target_duration_s=target_duration_s or estimate_duration(content.strip()),
                    language="es-ES",
                    author_type=author_type,
                    content_hash=content_hash(content.strip()),
                )
                db.add(version)
                db.flush()
        except IntegrityError:
            # Otro borrador se creó a la vez: se recalcula el número libre.
            continue
        db.add(AuditLog(event="script_version_created", actor_id=actor_id, detail={
            "story_id": story.id, "version": version_number, "author_type": author_type,
        }))
        return version
    raise RuntimeError(
        "No se ha podido asignar un número de versión de guion libre tras varios intentos"
    )


def save_user_edit(
    db: Session,
    story: Story,
    *,
    content: str,
    expected_version: int,
    actor_id: str,
) -> ScriptVersion:
    """Guarda una edición del usuario con control de concurrencia optimista.

    Si el número de versión esperado no coincide con el actual, se rechaza con
    conflicto: el texto del servidor y el del usuario se conservan (el usuario
    puede reenviar el suyo como versión nueva tras revisar).
    """
    current = latest_version(db, story.id)
    current_number = current.version if current else 0
    if expected_version != current_number:
        raise ScriptConflict(
            "Otra edición ha guardado una versión mientras escribías; revisa la versión actual "
            "y vuelve a guardar el tuyo como versión nueva",
            current_number,
        )
    if current and current.content_hash == content_hash(content.strip()):
        raise ValueError("Ese texto es idéntico a la versión actual; no se crea una versión repetida")
    return _add_version(db, story, content=content, author_type="HUMAN", actor_id=actor_id)


def approve_version(db: Session, story: Story, script_version_id: int, actor_id: str) -> Approval:
    """Aprueba una versión exacta. Un hash distinto o una versión antigua se rechaza."""
    version = db.get(ScriptVersion, script_version_id)
    if version is None or version.story_id != story.id:
        raise ValueError("Esa versión de guion no existe para esta noticia")
    current = latest_version(db, story.id)
    if current is None or current.id != version.id:
        raise ValueError(
            "Solo se puede aprobar la versión más reciente del guion; guarda o selecciona la última"
        )
    approval = active_approval(db, story.id)
    if approval is not None and approval.script_version_id == version.id:
        raise ValueError("Esta versión ya está aprobada")
    if approval is not None:
        approval.status = "INVALIDATED"
    row = Approval(
        story_id=story.id,
        script_version_id=version.id,
        actor_id=actor_id,
        status="ACTIVE",
    )
    db.add(row)
    db.flush()
    if story.status != "APPROVED":
        assert_transition("story", story.status, "APPROVED")
        story.status = "APPROVED"
    db.add(AuditLog(event="script_approved", actor_id=actor_id, detail={
        "story_id": story.id,
        "script_version_id": version.id,
        "content_hash": version.content_hash,
    }))
    return row


def reject_story(db: Session, story: Story, reason: str, actor_id: str) -> None:
    if story.status == "REJECTED":
        return
    assert_transition("story", story.status, "REJECTED")
    story.status = "REJECTED"
    approval = active_approval(db, story.id)
    if approval is not None:
        approval.status = "REVOKED"
    db.add(AuditLog(event="story_rejected", actor_id=actor_id, detail={
        "story_id": story.id, "reason": reason[:500],
    }))


def approval_label(status: str) -> str:
    return APPROVAL_LABELS.get(status, status)
