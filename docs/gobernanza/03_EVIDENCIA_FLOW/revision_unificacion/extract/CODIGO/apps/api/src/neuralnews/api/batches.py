"""Lotes editoriales, exportación y descarga del paquete."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from ..db import get_db
from ..models import Batch, BatchItem, Job, ProductionPackage, Story
from ..queue import enqueue
from ..schemas import BatchCreate
from ..security import get_current_actor
from ..services.av_jobs import batch_budget_summary, set_batch_budget
from ..services.batches import BATCH_SIZES, BatchError, batch_overview, create_batch, export_batch, read_package
from ..worker_tasks import EXPORT_BATCH

router = APIRouter(prefix="/api/v1/batches", tags=["batches"])


@router.post("")
def create(payload: BatchCreate, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    try:
        batch = create_batch(db, name=payload.name, target_size=payload.target_size, story_ids=payload.story_ids)
    except BatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": batch.id, "name": batch.name, "target_size": batch.target_size, "status": batch.status}


@router.get("")
def list_batches(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    rows = db.scalars(select(Batch).order_by(Batch.created_at.desc())).all()
    return {
        "items": [
            {"id": b.id, "name": b.name, "target_size": b.target_size, "status": b.status,
             "created_at": b.created_at.isoformat()}
            for b in rows
        ]
    }


@router.get("/{batch_id}")
def detail(batch_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Ese lote no existe")
    overview = batch_overview(db, batch)
    packages = db.scalars(
        select(ProductionPackage).where(ProductionPackage.batch_id == batch.id)
    ).all()
    overview["budget"] = batch_budget_summary(db, batch_id)
    overview["packages"] = [
        {"id": p.id, "version": p.package_version, "sha256": p.sha256, "state": p.state,
         "created_at": p.created_at.isoformat()}
        for p in packages
    ]
    return overview


@router.patch("/{batch_id}/order")
def reorder(
    batch_id: int,
    payload: dict,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """payload: {"story_ids": [orden deseado]}"""
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Ese lote no existe")
    order = payload.get("story_ids", [])
    items = db.scalars(select(BatchItem).where(BatchItem.batch_id == batch.id)).all()
    by_story = {item.story_id: item for item in items}
    if sorted(order) != sorted(by_story.keys()):
        raise HTTPException(status_code=400, detail="La lista de orden no coincide con las noticias del lote")
    for position, story_id in enumerate(order):
        by_story[story_id].position = position
    db.flush()
    return {"ok": True}


@router.post("/{batch_id}/export")
def export(batch_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Ese lote no existe")
    # Si ya hay una exportación en marcha para este lote, se reutiliza; si no, se crea una nueva.
    pending = db.scalar(
        select(Job).where(
            Job.type == EXPORT_BATCH,
            Job.status.in_(["QUEUED", "RUNNING", "RETRYABLE_FAILED"]),
        )
    )
    if pending is not None:
        db.flush()
        return {"job_id": pending.id, "created": False}
    job, _ = enqueue(db, EXPORT_BATCH, {"batch_id": batch.id}, dedupe_key=None)
    db.flush()
    return {"job_id": job.id, "created": True}


@router.get("/{batch_id}/package")
def download(batch_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> Response:
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Ese lote no existe")
    package = db.scalar(
        select(ProductionPackage)
        .where(ProductionPackage.batch_id == batch.id, ProductionPackage.state == "EXPORTED")
        .order_by(ProductionPackage.package_version.desc())
        .limit(1)
    )
    if package is None:
        raise HTTPException(status_code=404, detail="Todavía no hay paquete exportado para este lote")
    data = read_package(package)
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="lote-{batch.id}-v{package.package_version}.zip"',
            "X-Package-Sha256": package.sha256,
        },
    )


@router.put("/{batch_id}/budget")
def update_budget(
    batch_id: int,
    payload: dict,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Fija el techo agregado de presupuesto del lote (T514).

    `limit_eur` nulo quita el techo. El encolado de un trabajo cuyo coste
    estimado no quepa en el presupuesto se rechaza antes de crear el trabajo.
    """
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Ese lote no existe")
    raw = payload.get("limit_eur")
    limit = None if raw is None else float(raw)
    if limit is not None and limit < 0:
        raise HTTPException(status_code=400, detail="El techo del lote no puede ser negativo.")
    set_batch_budget(db, batch_id, limit)
    return batch_budget_summary(db, batch_id)
