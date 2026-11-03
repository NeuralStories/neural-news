"""Composición audiovisual: endpoints para renderizar el plan y descargar el vídeo.

Los mensajes al usuario van en castellano natural; los códigos HTTP sólo se usan
por debajo. Sin generación de proveedores externos: FFmpeg local con activos
simulados (Fase 6).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from ..db import get_db
from ..models import Job, RenderOutput
from ..security import get_current_actor
from ..services import av_jobs
from ..services.av_render import validate_render_plan

router = APIRouter(prefix="/api/v1/av", tags=["av"])


@router.post("/render")
def request_render(payload: dict, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Encola la composición del vídeo de un plan de producción.

    Devuelve el trabajo creado (o el ya existente si el plan idéntico estaba en
    cola o en marcha). Los problemas del plan se devuelven con 400 y el motivo
    concreto; nada se compone a medias.
    """
    errors = validate_render_plan(payload)
    if errors:
        raise HTTPException(status_code=400, detail="El plan no es válido:\n- " + "\n- ".join(errors))
    job, created = av_jobs.enqueue_av_render(db, payload)
    return {
        "job_id": job.id,
        "created": created,
        "fingerprint": av_jobs.av_render_fingerprint(payload),
        "message": (
            "Composición en cola: recibirás el vídeo cuando termine."
            if created
            else "Este plan ya estaba en cola o en composición; se ha reutilizado el trabajo."
        ),
    }


@router.get("/renders")
def list_renders(project_id: str | None = None, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Vídeos ya compuestos, opcionalmente de un proyecto."""
    query = select(RenderOutput).order_by(RenderOutput.created_at.desc())
    if project_id:
        query = query.where(RenderOutput.project_id == project_id)
    rows = db.scalars(query).all()
    return {
        "total": len(rows),
        "items": [
            {
                "render_id": row.id,
                "job_id": row.job_id,
                "project_id": row.project_id,
                "output_format": row.output_format,
                "duration_s": row.duration_s,
                "scene_count": row.scene_count,
                "sha256": row.sha256,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.get("/renders/{render_id}")
def download_render(render_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> FileResponse:
    """Descarga el vídeo compuesto y verificado."""
    row = db.get(RenderOutput, render_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ese vídeo no existe")
    path = row.storage_path
    if not Path(path).exists():
        raise HTTPException(status_code=410, detail="El fichero del vídeo ya no está disponible")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.split("/")[-1].split("\\")[-1],
        headers={
            "X-Content-Sha256": row.sha256,
            "X-Duration-Seconds": f"{row.duration_s:.3f}",
            "X-Output-Format": row.output_format,
        },
    )
