"""Proyectos de producción y Studio (NN-107 F1): persistencia con control de
concurrencia (CAS por revisión de paso) y biblioteca de medios idempotente.

Reglas del cap. 13 de la especificación rectora:
- Cada guardado de paso inserta una revisión inmutable; `expected_revision`
  obsoleto responde 409 con la revisión vigente.
- `ratio` del proyecto se fija en la creación y ningún endpoint lo muta (R-BUG-2).
- Vincular una historia al proyecto la activa automáticamente (R-BUG-1).
- La subida de un MP4 deja la toma en IMPORTADA; APROBADA exige revisión humana.
- El estado vive en PostgreSQL/SQLite vía API: nunca solo en el navegador.
"""
from __future__ import annotations

import datetime as _dt

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    GeneratedTake,
    MediaAsset,
    MediaApproval,
    NarrationBeat,
    ProductionProject,
    PromptPackage,
    ScriptVersion,
    Shot,
    StudioStepRevision,
    Story,
    TAKE_STATUSES,
    STUDIO_STEPS,
    content_hash,
)
from ..security import get_current_actor
from ..services.director import build_plan
from ..services.media_library import MediaUploadError, asset_to_out, upload_media

router = APIRouter(prefix="/api/v1", tags=["projects"])


# ---------------------------------------------------------------------------
# Esquemas de petición
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    story_id: int | None = None
    ratio: str = "9:16"
    target_duration_s: int | None = None
    format_profile: dict = {}


class ProjectPatch(BaseModel):
    name: str | None = None
    status: str | None = None


class StepSave(BaseModel):
    payload: dict
    expected_revision: int = Field(ge=0)


class BeatIn(BaseModel):
    text: str
    est_seconds: float | None = None
    claim_ids: list[int] = []


class BeatsSave(BaseModel):
    beats: list[BeatIn]


class ShotIn(BaseModel):
    beat_id: int | None = None
    shot_kind: str = "PENDING"
    rationale: str | None = None
    start_s: float | None = None
    end_s: float | None = None
    max_duration_s: float | None = None
    data: dict = {}


class ShotsSave(BaseModel):
    shots: list[ShotIn]


class TakeCreate(BaseModel):
    shot_id: int | None = None
    take_number: int = 1


class TakeApproval(BaseModel):
    status: str  # APROBADA|RECHAZADA
    note: str | None = None


class PromptCreate(BaseModel):
    take_id: int | None = None
    prompt_en: str = Field(min_length=1)
    explanation_es: str | None = None
    constraints: list[str] = []
    attachments_manifest: list[dict] = []
    checklist: dict = {}


class MediaApprovalIn(BaseModel):
    status: str  # APPROVED|REJECTED
    note: str | None = None


class LinkStory(BaseModel):
    story_id: int


class DirectorPlanIn(BaseModel):
    provider_max_clip_s: float = 8.0
    script_text: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project(db: Session, project_id: int) -> ProductionProject:
    project = db.get(ProductionProject, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Ese proyecto no existe")
    return project


def _step_payload(db: Session, project: ProductionProject, step: str) -> dict:
    rev = int(project.step_revisions.get(step, 0))
    if rev == 0:
        return {"revision": 0, "payload": {}}
    row = db.scalars(
        select(StudioStepRevision)
        .where(StudioStepRevision.project_id == project.id, StudioStepRevision.step == step)
        .order_by(StudioStepRevision.revision.desc())
        .limit(1)
    ).first()
    return {"revision": rev, "payload": row.payload if row else {}}


def project_to_out(db: Session, project: ProductionProject, full: bool = False) -> dict:
    out = {
        "id": project.id,
        "name": project.name,
        "story_id": project.story_id,
        "script_version_id": project.script_version_id,
        "ratio": project.ratio,
        "format_profile": project.format_profile or {},
        "target_duration_s": project.target_duration_s,
        "status": project.status,
        "step_revisions": project.step_revisions or {},
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }
    if project.story_id:
        story = db.get(Story, project.story_id)
        if story is not None:
            out["story"] = {"id": story.id, "title": story.title, "status": story.status}
    if not full:
        return out

    out["steps"] = {step: _step_payload(db, project, step) for step in STUDIO_STEPS}
    out["beats"] = [
        {
            "id": b.id,
            "sequence": b.sequence,
            "text": b.text,
            "est_seconds": b.est_seconds,
            "claim_ids": b.claim_ids or [],
        }
        for b in project.beats
    ]
    out["shots"] = [
        {
            "id": s.id,
            "sequence": s.sequence,
            "beat_id": s.beat_id,
            "shot_kind": s.shot_kind,
            "rationale": s.rationale,
            "start_s": s.start_s,
            "end_s": s.end_s,
            "max_duration_s": s.max_duration_s,
            "data": s.data or {},
        }
        for s in project.shots
    ]
    takes = []
    for take in project.takes:
        prompts = db.scalars(
            select(PromptPackage).where(PromptPackage.take_id == take.id)
        ).all()
        takes.append(
            {
                "id": take.id,
                "shot_id": take.shot_id,
                "take_number": take.take_number,
                "status": take.status,
                "imported_media": (
                    asset_to_out(take.imported_media) if take.imported_media else None
                ),
                "prompt_versions": len(prompts),
                "created_at": take.created_at.isoformat(),
            }
        )
    out["takes"] = takes
    return out


# ---------------------------------------------------------------------------
# Proyectos
# ---------------------------------------------------------------------------


@router.post("/projects")
def create_project(body: ProjectCreate, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    if body.ratio not in ("9:16", "16:9"):
        raise HTTPException(status_code=422, detail="El ratio debe ser 9:16 o 16:9")
    story = None
    if body.story_id is not None:
        story = db.get(Story, body.story_id)
        if story is None:
            raise HTTPException(status_code=404, detail="Esa noticia no existe")
    project = ProductionProject(
        name=body.name,
        story_id=story.id if story else None,  # R-BUG-1: vincular = activar
        ratio=body.ratio,  # R-BUG-2: fijado solo aquí
        format_profile={"ratio": body.ratio, **(body.format_profile or {})},
        target_duration_s=body.target_duration_s,
        step_revisions={step: 0 for step in STUDIO_STEPS},
    )
    db.add(project)
    db.flush()
    return project_to_out(db, project)


@router.get("/projects")
def list_projects(
    db=Depends(get_db), actor=Depends(get_current_actor), limit: int = 50, offset: int = 0
) -> dict:
    rows = db.scalars(select(ProductionProject).order_by(ProductionProject.created_at.desc())).all()
    total = len(rows)
    return {
        "total": total,
        "items": [
            project_to_out(db, p) for p in rows[offset : offset + min(limit, 200)]
        ],
    }


@router.get("/projects/{project_id}")
def get_project(project_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    return project_to_out(db, _get_project(db, project_id), full=True)


@router.put("/projects/{project_id}")
def patch_project(
    project_id: int, body: ProjectPatch, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    project = _get_project(db, project_id)
    if body.name is not None:
        project.name = body.name
    if body.status is not None:
        project.status = body.status
    db.flush()
    return project_to_out(db, project)


@router.post("/projects/{project_id}/link-story")
def link_story(
    project_id: int, body: LinkStory, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """Vincula una historia y la deja activa para producción (R-BUG-1)."""
    project = _get_project(db, project_id)
    story = db.get(Story, body.story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Esa noticia no existe")
    project.story_id = story.id
    db.flush()
    return project_to_out(db, project)


# ---------------------------------------------------------------------------
# Studio: pasos con CAS
# ---------------------------------------------------------------------------


@router.put("/projects/{project_id}/studio/{step}")
def save_step(
    project_id: int, step: str, body: StepSave, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    if step not in STUDIO_STEPS:
        raise HTTPException(status_code=404, detail=f"Paso desconocido: {step}")
    project = _get_project(db, project_id)
    current = int(project.step_revisions.get(step, 0))
    if body.expected_revision != current:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Revisión obsoleta: recarga el proyecto antes de guardar",
                "current_revision": current,
            },
        )
    payload = dict(body.payload)
    if step == "noticias" and "story_id" in payload:
        # R-BUG-1: elegir/importar una noticia en el Studio la activa de verdad.
        story = db.get(Story, int(payload["story_id"]))
        if story is None:
            raise HTTPException(status_code=404, detail="Esa noticia no existe")
        project.story_id = story.id
    project.step_revisions = {**project.step_revisions, step: current + 1}
    db.add(
        StudioStepRevision(
            project_id=project.id,
            step=step,
            revision=current + 1,
            payload=payload,
            actor_id=actor["actor_id"],
        )
    )
    db.flush()
    return {"step": step, "revision": current + 1, "story_id": project.story_id}


@router.get("/projects/{project_id}/studio/{step}/history")
def step_history(
    project_id: int, step: str, db=Depends(get_db), actor=Depends(get_current_actor), limit: int = 20
) -> dict:
    if step not in STUDIO_STEPS:
        raise HTTPException(status_code=404, detail=f"Paso desconocido: {step}")
    project = _get_project(db, project_id)
    rows = db.scalars(
        select(StudioStepRevision)
        .where(StudioStepRevision.project_id == project.id, StudioStepRevision.step == step)
        .order_by(StudioStepRevision.revision.desc())
        .limit(min(limit, 100))
    ).all()
    return {
        "step": step,
        "current_revision": int(project.step_revisions.get(step, 0)),
        "items": [
            {
                "revision": r.revision,
                "actor_id": r.actor_id,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Beats, shots y tomas
# ---------------------------------------------------------------------------


@router.put("/projects/{project_id}/beats")
def save_beats(
    project_id: int, body: BeatsSave, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """Sustituye los beats del proyecto. El audio es continuo: aquí no hay cortes
    forzados de 8 s (F-05); `est_seconds` es solo estimación editable."""
    project = _get_project(db, project_id)
    project.beats.clear()
    for i, beat in enumerate(body.beats):
        project.beats.append(
            NarrationBeat(
                sequence=i,
                text=beat.text,
                est_seconds=beat.est_seconds,
                claim_ids=beat.claim_ids,
            )
        )
    db.flush()
    return {"beats": len(project.beats)}


@router.put("/projects/{project_id}/shots")
def save_shots(
    project_id: int, body: ShotsSave, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    project = _get_project(db, project_id)
    valid_kinds = {
        "USER_VIDEO", "FLOW_MAXDOTAI", "DOCUMENTARY", "DATA_GRAPHIC",
        "GENERATIVE_BROLL", "TITLE_CARD", "PENDING",
    }
    project.shots.clear()
    for i, shot in enumerate(body.shots):
        if shot.shot_kind not in valid_kinds:
            raise HTTPException(status_code=422, detail=f"Tipo de plano no válido: {shot.shot_kind}")
        project.shots.append(
            Shot(
                sequence=i,
                beat_id=shot.beat_id,
                shot_kind=shot.shot_kind,
                rationale=shot.rationale,
                start_s=shot.start_s,
                end_s=shot.end_s,
                max_duration_s=shot.max_duration_s,
                data=shot.data,
            )
        )
    db.flush()
    return {"shots": len(project.shots), "ratio": project.ratio}


@router.post("/projects/{project_id}/takes")
def create_take(
    project_id: int, body: TakeCreate, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    project = _get_project(db, project_id)
    shot = None
    if body.shot_id is not None:
        shot = db.get(Shot, body.shot_id)
        if shot is None or shot.project_id != project.id:
            raise HTTPException(status_code=404, detail="Ese plano no pertenece al proyecto")
    take = GeneratedTake(project_id=project.id, shot_id=shot.id if shot else None,
                         take_number=body.take_number, status="PLANIFICADA")
    db.add(take)
    db.flush()
    return {"id": take.id, "status": take.status, "take_number": take.take_number}


@router.post("/projects/{project_id}/takes/{take_id}/media")
async def upload_take_media(
    project_id: int,
    take_id: int,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
    file: UploadFile = File(...),
) -> dict:
    """Importa el MP4 generado externamente y lo asocia a la toma. Idempotente
    por SHA-256; la toma queda IMPORTADA (nunca APROBADA automáticamente)."""
    project = _get_project(db, project_id)
    take = db.get(GeneratedTake, take_id)
    if take is None or take.project_id != project.id:
        raise HTTPException(status_code=404, detail="Esa toma no pertenece al proyecto")
    data = await file.read()
    try:
        asset = upload_media(db, data, file.content_type or "application/octet-stream", file.filename)
    except MediaUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    take.imported_media_id = asset.id
    take.status = "IMPORTADA"
    db.flush()
    return {"take_id": take.id, "status": take.status, "media": asset_to_out(asset)}


@router.post("/projects/{project_id}/takes/{take_id}/approval")
def approve_take(
    project_id: int, take_id: int, body: TakeApproval,
    db=Depends(get_db), actor=Depends(get_current_actor),
) -> dict:
    """Aprobación humana de la toma importada. No requiere medios ausentes ni
    simula continuidad: solo registra la decisión del revisor."""
    project = _get_project(db, project_id)
    take = db.get(GeneratedTake, take_id)
    if take is None or take.project_id != project.id:
        raise HTTPException(status_code=404, detail="Esa toma no pertenece al proyecto")
    if body.status not in ("APROBADA", "RECHAZADA"):
        raise HTTPException(status_code=422, detail="Estado debe ser APROBADA o RECHAZADA")
    if body.status == "APROBADA" and take.imported_media_id is None:
        raise HTTPException(
            status_code=409,
            detail="No se puede aprobar una toma sin vídeo importado (un prompt listo no es un vídeo)",
        )
    take.status = body.status
    db.flush()
    return {"take_id": take.id, "status": take.status}


@router.post("/projects/{project_id}/prompts")
def save_prompt(
    project_id: int, body: PromptCreate, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    project = _get_project(db, project_id)
    take = None
    if body.take_id is not None:
        take = db.get(GeneratedTake, body.take_id)
        if take is None or take.project_id != project.id:
            raise HTTPException(status_code=404, detail="Esa toma no pertenece al proyecto")
    previous = db.scalars(
        select(PromptPackage).where(
            PromptPackage.project_id == project.id, PromptPackage.take_id == (take.id if take else None)
        )
    ).all()
    version = max((p.version for p in previous), default=0) + 1
    pkg = PromptPackage(
        project_id=project.id,
        take_id=take.id if take else None,
        version=version,
        prompt_en=body.prompt_en,
        explanation_es=body.explanation_es,
        constraints=body.constraints,
        attachments_manifest=body.attachments_manifest,
        checklist=body.checklist,
        content_hash=content_hash(body.prompt_en),
    )
    db.add(pkg)
    if take is not None and take.status == "PLANIFICADA":
        take.status = "PROMPT_LISTO"
    db.flush()
    return {"prompt_id": pkg.id, "version": version, "content_hash": pkg.content_hash,
            "take_status": take.status if take else None}


# ---------------------------------------------------------------------------
# Biblioteca de medios
# ---------------------------------------------------------------------------


@router.post("/media")
async def upload_media_endpoint(
    db=Depends(get_db), actor=Depends(get_current_actor), file: UploadFile = File(...)
) -> dict:
    data = await file.read()
    try:
        asset = upload_media(db, data, file.content_type or "application/octet-stream", file.filename)
    except MediaUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asset_to_out(asset)


@router.get("/media")
def list_media(db=Depends(get_db), actor=Depends(get_current_actor), limit: int = 50) -> dict:
    rows = db.scalars(select(MediaAsset).order_by(MediaAsset.created_at.desc())).all()
    return {"total": len(rows), "items": [asset_to_out(a) for a in rows[: min(limit, 200)]]}


@router.get("/media/{asset_id}/file")
def get_media_file(asset_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> object:
    from fastapi.responses import FileResponse

    asset = db.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Ese asset no existe")
    return FileResponse(asset.storage_path, media_type=asset.mime_type, filename=asset.filename)


@router.post("/media/{asset_id}/approval")
def approve_media(
    asset_id: int, body: MediaApprovalIn, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """Aprobación humana de derechos/uso del asset (F-02: nada aprobado por defecto)."""
    asset = db.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Ese asset no existe")
    if body.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=422, detail="Estado debe ser APPROVED o REJECTED")
    db.add(MediaApproval(asset_id=asset.id, actor_id=actor["actor_id"], status=body.status, note=body.note))
    asset.license_state = body.status
    db.flush()
    return asset_to_out(asset)


# ---------------------------------------------------------------------------
# F3 — Director audiovisual determinista y FlowManualPackage
# ---------------------------------------------------------------------------


def _project_script(db: Session, project: ProductionProject, override: str | None) -> str:
    """Guion con una sola fuente de verdad: el paso Guion del proyecto; si no
    hay, la última revisión de guion de la historia vinculada."""
    if override and override.strip():
        return override.strip()
    guion = (project.step_revisions or {}).get("guion", 0)
    if guion:
        row = db.scalars(
            select(StudioStepRevision)
            .where(
                StudioStepRevision.project_id == project.id,
                StudioStepRevision.step == "guion",
                StudioStepRevision.revision == guion,
            )
            .order_by(StudioStepRevision.revision.desc())
            .limit(1)
        ).first()
        text = ((row.payload or {}).get("scriptText") or "") if row else ""
        if text.strip():
            return text.strip()
    if project.story_id:
        version = db.scalars(
            select(ScriptVersion)
            .where(ScriptVersion.story_id == project.story_id)
            .order_by(ScriptVersion.version.desc())
            .limit(1)
        ).first()
        if version is not None and version.content.strip():
            return version.content.strip()
    return ""


@router.post("/projects/{project_id}/director/plan")
def run_director(
    project_id: int, body: DirectorPlanIn, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """Director audiovisual determinista (cap. 7): beats de locución continua y
    tomas por capacidad del proveedor. Misma entrada → mismo plan."""
    project = _get_project(db, project_id)
    script = _project_script(db, project, body.script_text)
    if not script:
        raise HTTPException(
            status_code=409,
            detail="No hay guion todavía: escribe el guion del proyecto o vincula una historia con revisión de guion",
        )
    if body.provider_max_clip_s <= 0 or body.provider_max_clip_s > 60:
        raise HTTPException(status_code=422, detail="provider_max_clip_s debe estar entre 0 y 60 segundos")
    plan = build_plan(script, provider_max_clip_s=body.provider_max_clip_s)

    project.beats.clear()
    for beat in plan.beats:
        project.beats.append(
            NarrationBeat(
                sequence=beat["sequence"],
                text=beat["text"],
                est_seconds=beat["est_seconds"],
                claim_ids=beat["claim_ids"],
            )
        )
    project.shots.clear()
    for shot in plan.shots:
        project.shots.append(
            Shot(
                sequence=shot["sequence"],
                shot_kind=shot["shot_kind"],
                rationale=shot["rationale"],
                start_s=shot["start_s"],
                end_s=shot["end_s"],
                max_duration_s=shot["max_duration_s"],
                data=shot["data"],
            )
        )
    db.flush()
    return {
        "beats": plan.beats,
        "shots": plan.shots,
        "total_seconds": round(sum(b["est_seconds"] for b in plan.beats), 2),
        "provider_max_clip_s": body.provider_max_clip_s,
        "note": "Locución continua: los cortes solo responden a la capacidad del proveedor, no al texto.",
    }


@router.get("/projects/{project_id}/takes/{take_id}/flow-package")
def flow_manual_package(
    project_id: int, take_id: int, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """FlowManualPackage (cap. 9, modo manual): instrucciones completas para
    generar la toma en Flow a mano. Descarga JSON; jamás llama a Flow."""
    project = _get_project(db, project_id)
    take = db.get(GeneratedTake, take_id)
    if take is None or take.project_id != project.id:
        raise HTTPException(status_code=404, detail="Esa toma no pertenece al proyecto")

    prompt = db.scalars(
        select(PromptPackage)
        .where(PromptPackage.take_id == take.id)
        .order_by(PromptPackage.version.desc())
        .limit(1)
    ).first()
    if prompt is None:
        raise HTTPException(
            status_code=409,
            detail="La toma no tiene prompt todavía: genera el prompt de la toma antes de exportar el paquete",
        )

    shot = db.get(Shot, take.shot_id) if take.shot_id else None
    media_refs: list[dict] = []
    prompt_only: list[dict] = []
    referencias_rev = (project.step_revisions or {}).get("referencias", 0)
    if referencias_rev:
        ref_row = db.scalars(
            select(StudioStepRevision)
            .where(
                StudioStepRevision.project_id == project.id,
                StudioStepRevision.step == "referencias",
                StudioStepRevision.revision == referencias_rev,
            )
            .order_by(StudioStepRevision.revision.desc())
            .limit(1)
        ).first()
        if ref_row is not None:
            for ref in (ref_row.payload or {}).get("visualReferences", []) or []:
                if not isinstance(ref, dict):
                    continue
                if ref.get("status") != "aprobado":
                    continue  # F-02: solo se adjunta lo aprobado por el usuario
                entry = {
                    "identifier": ref.get("identifier"),
                    "name": ref.get("name"),
                    "category": ref.get("category"),
                }
                if ref.get("mediaId"):
                    entry["media_id"] = ref["mediaId"]
                    media_refs.append(entry)
                else:
                    entry["uso"] = "PROMPT_ONLY"
                    prompt_only.append(entry)

    warnings: list[str] = []
    sheet = db.get(MediaAsset, take.imported_media_id) if take.imported_media_id else None

    package = {
        "package": "FlowManualPackage.v1",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "take": {"id": take.id, "take_number": take.take_number, "status": take.status,
                 "shot_id": take.shot_id,
                 "shot_kind": shot.shot_kind if shot else None,
                 "rationale": shot.rationale if shot else None,
                 "est_duration_s": (shot.data or {}).get("est_duration_s") if shot else None},
        "project": {"id": project.id, "name": project.name, "ratio": project.ratio},
        "personaje": {
            "a_escoger_en_flow": "maxDotAi",
            "handle": "@maxDotAi (pendiente de confirmar en cuenta)",
            "estado_vinculo": "PENDIENTE_DE_VINCULAR",
            "nota": "No describas un personaje nuevo: usa la ficha canónica guardada en Flow.",
        },
        "referencias": {
            "adjuntables_con_mediaid": media_refs,
            "solo_textuales_prompt_only": prompt_only,  # PROMPT_ONLY: nunca adjunto (F-07)
            "regla": "mediaId solo vale en la galería de Flow; lo textual nunca se presenta como adjunto (F-07).",
        },
        "prompt": {
            "version": prompt.version,
            "prompt_en": prompt.prompt_en,
            "explanation_es": prompt.explanation_es,
            "constraints": prompt.constraints or [],
            "content_hash": prompt.content_hash,
        },
        "ratio": project.ratio,
        "checklist": {
            "1_personaje_seleccionado": "maxDotAi",
            "2_referencias_adjuntadas": "según el manifiesto de referencias",
            "3_prompt_copiado_literal": True,
            "4_ratio": project.ratio,
            "5_importar_mp4_resultado": "Resultado → Importar MP4 (queda asociado a esta toma y revisión)",
        },
        "warnings": warnings,
        "descargo": "Prompt preparado ≠ vídeo generado. Este paquete no llama a Flow ni simula conexión.",
    }
    if sheet is None and take.status in ("PLANIFICADA", "PROMPT_LISTO"):
        warnings.append("La toma aún no tiene MP4 importado; tras generar en Flow, impórtalo en Resultado.")
    return package
