"""Noticias: listado, investigación, guiones con versiones, aprobación y storyboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..db import get_db
from ..models import Approval, Claim, Evidence, Job, ScriptVersion, Source, Story, StorySource
from ..providers.image_prompt import build_storyboard
from ..queue import enqueue
from ..schemas import ApproveRequest, RejectRequest, ScriptPatch, ScriptVersionOut
from ..security import get_current_actor, require_paid_services
from ..services.dedupe import duplicates_for_all, find_possible_duplicates
from ..services.research import score_story
from ..services.scripts import (
    ScriptConflict,
    active_approval,
    approve_version,
    create_draft_version,
    latest_version,
    reject_story,
    save_user_edit,
)
from ..states import SOURCE_LABELS, STORY_LABELS
from ..worker_tasks import DRAFT_SCRIPT, RESEARCH_STORY

router = APIRouter(prefix="/api/v1/stories", tags=["stories"])


def story_to_out(story: Story) -> dict:
    return {
        "id": story.id,
        "topic_key": story.topic_key,
        "title": story.title,
        "summary": story.summary,
        "status": story.status,
        "status_label": STORY_LABELS.get(story.status, story.status),
        "editorial_score": story.editorial_score,
        "score_breakdown": story.score_breakdown or {},
        "is_opinion": story.is_opinion,
        "original_event_date": story.original_event_date.isoformat() if story.original_event_date else None,
        "created_at": story.created_at.isoformat(),
    }


@router.get("")
def list_stories(
    db=Depends(get_db),
    actor=Depends(get_current_actor),
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = select(Story).order_by(Story.created_at.desc())
    if status:
        query = query.where(Story.status == status)
    rows = db.scalars(query).all()
    total = len(rows)
    rows = rows[offset : offset + min(limit, 200)]
    duplicates = duplicates_for_all(db)
    items = []
    for story in rows:
        out = story_to_out(story)
        sources = db.scalars(select(StorySource).where(StorySource.story_id == story.id)).all()
        out["source_count"] = len(sources)
        claims = db.scalars(select(Claim).where(Claim.story_id == story.id)).all()
        out["claim_count"] = len(claims)
        out["unverified_claims"] = sum(1 for c in claims if c.verification_status == "UNVERIFIED")
        out["possible_duplicates"] = duplicates.get(story.id, [])
        items.append(out)
    return {"total": total, "items": items}


@router.get("/{story_id}")
def get_story(story_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    out = story_to_out(story)

    sources = []
    for link in db.scalars(select(StorySource).where(StorySource.story_id == story.id)).all():
        source = db.get(Source, link.source_id)
        sources.append(
            {
                "source_id": source.id,
                "provider": source.provider,
                "title": source.title,
                "canonical_url": source.canonical_url,
                "published_at": source.published_at.isoformat() if source.published_at else None,
                "status_label": SOURCE_LABELS.get(source.status, source.status),
                "relevance": link.relevance,
            }
        )
    out["sources"] = sources

    claims_out = []
    for claim in db.scalars(select(Claim).where(Claim.story_id == story.id)).all():
        evidence = db.scalars(select(Evidence).where(Evidence.claim_id == claim.id)).all()
        claims_out.append(
            {
                "id": claim.id,
                "statement": claim.statement,
                "verification_status": claim.verification_status,
                "verification_notes": claim.verification_notes,
                "evidence": [
                    {
                        "id": e.id,
                        "url": e.url,
                        "publisher": e.publisher,
                        "published_at": e.published_at.isoformat() if e.published_at else None,
                        "retrieved_at": e.retrieved_at.isoformat(),
                        "excerpt_or_paraphrase": e.excerpt_or_paraphrase,
                        "kind": e.kind,
                        "confidence": e.confidence,
                        "demo": e.demo,
                    }
                    for e in evidence
                ],
            }
        )
    out["claims"] = claims_out

    versions = db.scalars(
        select(ScriptVersion).where(ScriptVersion.story_id == story.id).order_by(ScriptVersion.version)
    ).all()
    out["script_versions"] = [
        {
            "id": v.id,
            "version": v.version,
            "content": v.content,
            "target_duration_s": v.target_duration_s,
            "language": v.language,
            "author_type": v.author_type,
            "created_at": v.created_at.isoformat(),
            "content_hash": v.content_hash,
        }
        for v in versions
    ]
    approval = active_approval(db, story.id)
    out["active_approval"] = (
        {
            "script_version_id": approval.script_version_id,
            "approved_at": approval.approved_at.isoformat(),
            "actor": approval.actor_id,
            "content_hash": approval.script_version.content_hash,
        }
        if approval
        else None
    )
    out["pending_approval_flag"] = approval is None or approval.status != "ACTIVE"
    out["possible_duplicates"] = find_possible_duplicates(db, story)
    return out


@router.get("/{story_id}/storyboard")
def get_storyboard(story_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Preparación visual: escenas orientativas y prompts de imagen del guion vigente.

    No genera imágenes ni vídeo: sólo prepara lo que se puede copiar a la herramienta elegida.
    """
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    version = latest_version(db, story.id)
    if version is None:
        raise HTTPException(status_code=404, detail="Todavía no hay guion para preparar la escena")
    approval = active_approval(db, story.id)
    storyboard = build_storyboard(story, version, approval)
    return {
        "story_id": story.id,
        "script_version": version.version,
        "approved": bool(approval and approval.status == "ACTIVE"),
        **storyboard.model_dump(mode="json"),
        "note": (
            "Prompts preliminares para usar manualmente en la herramienta de vídeo elegida. "
            "No se han generado imágenes ni vídeo."
        ),
    }


@router.post("/{story_id}/research")
def research(story_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Encola la investigación con un proveedor real (búsqueda + modelo).

    En un despliegue sin servicios de pago activados, se dice en voz alta en
    lugar de encolar un trabajo que no podrá completarse.
    """
    require_paid_services()
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    job, created = enqueue(db, RESEARCH_STORY, {"story_id": story.id},
                           dedupe_key=f"research:{story.id}:{story.updated_at.isoformat()}")
    db.flush()
    return {"job_id": job.id, "created": created}


@router.post("/{story_id}/draft")
def draft(story_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Encola la redacción del guion con un proveedor real (modelo editorial)."""
    require_paid_services()
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    job, created = enqueue(db, DRAFT_SCRIPT, {"story_id": story.id},
                           dedupe_key=f"draft:{story.id}:{story.updated_at.isoformat()}")
    db.flush()
    return {"job_id": job.id, "created": created}


@router.patch("/{story_id}/script")
def patch_script(
    story_id: int,
    payload: ScriptPatch,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    try:
        version = save_user_edit(
            db, story,
            content=payload.content,
            expected_version=payload.expected_version,
            actor_id=actor["actor_id"],
        )
    except ScriptConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "current_version": exc.current_version},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "script_version": {
            "id": version.id,
            "version": version.version,
            "content_hash": version.content_hash,
        },
        "message": "Guardado como nueva versión; si estaba aprobada, la aprobación queda anulada",
    }


@router.post("/{story_id}/approve")
def approve(
    story_id: int,
    payload: ApproveRequest,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    try:
        approval = approve_version(db, story, payload.script_version_id, actor["actor_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "approval": {
            "script_version_id": approval.script_version_id,
            "status": approval.status,
        },
        "message": "Guion aprobado. Si editas el texto después, tendrás que aprobar la nueva versión.",
    }


@router.post("/{story_id}/reject")
def reject(
    story_id: int,
    payload: RejectRequest,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    try:
        reject_story(db, story, payload.reason, actor["actor_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "message": "Noticia descartada"}


@router.post("/{story_id}/rescore")
def rescore(story_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    score = score_story(db, story)
    return {"editorial_score": score, "breakdown": story.score_breakdown}
