"""Trabajos, consumo, configuración y estado de proveedores."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..config import get_settings
from ..db import get_db
from ..models import Job, Setting
from ..schemas import BudgetUpdate, JobOut
from ..security import get_current_actor
from ..services.budget import get_budget, set_budget, usage_summary
from ..states import JOB_LABELS

router = APIRouter(prefix="/api/v1", tags=["ops"])


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ese trabajo no existe")
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "status_label": JOB_LABELS.get(job.status, job.status),
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "progress": job.progress,
        "error": job.error,
        "payload": job.payload,
        "created_at": job.created_at.isoformat(),
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.get("/jobs")
def list_jobs(db=Depends(get_db), actor=Depends(get_current_actor), limit: int = 50) -> dict:
    rows = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(min(limit, 200))).all()
    return {
        "items": [
            {
                "id": j.id,
                "type": j.type,
                "status": j.status,
                "status_label": JOB_LABELS.get(j.status, j.status),
                "attempt": j.attempt,
                "error": j.error,
                "created_at": j.created_at.isoformat(),
            }
            for j in rows
        ]
    }


@router.get("/usage")
def usage(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    return usage_summary(db)


@router.put("/config/budget")
def update_budget(
    payload: BudgetUpdate, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    if actor["is_demo"]:
        return {"warning": "Sesión de demostración: los cambios no afectan a servicios reales",
                **get_budget(db)}
    return set_budget(
        db,
        paid_services_enabled=payload.paid_services_enabled,
        daily_limit_eur=payload.daily_limit_eur,
    )


@router.get("/provider-status")
def provider_status(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    settings = get_settings()
    keys = settings.secrets_status()
    demo = settings.demo_mode
    items = [
        {
            "key": "manual",
            "name": "Texto y archivos aportados",
            "configured": True,
            "state": "probado",
            "note": "Implementado y verificado con pruebas automáticas; funciona sin claves.",
        },
        {
            "key": "web_rss",
            "name": "Artículos web y RSS",
            "configured": True,
            "state": "probado",
            "note": "Implementado y verificado con servidor de prueba local (protecciones SSRF activas).",
        },
        {
            "key": "youtube",
            "name": "YouTube (metadatos)",
            "configured": keys["youtube_api_key"],
            "state": "implementado" if keys["youtube_api_key"] else "sin_clave",
            "note": "Adaptador real preparado con YouTube Data API v3; no validado con credenciales en este MVP.",
        },
        {
            "key": "gemini_video",
            "name": "Análisis de vídeo (Gemini)",
            "configured": keys["gemini_api_key"],
            "state": "implementado" if keys["gemini_api_key"] else "mock",
            "note": "Adaptador preparado (salida marcada como análisis, nunca transcripción literal); no validado sin clave.",
        },
        {
            "key": "spotify",
            "name": "Spotify / pódcast (metadatos)",
            "configured": keys["spotify_access_token"],
            "state": "implementado" if keys["spotify_access_token"] else "sin_clave",
            "note": "Adaptador preparado (get-an-episode exige autorización de usuario); no validado. Sin transcripción: estado «Solo información básica».",
        },
        {
            "key": "search",
            "name": "Búsqueda para investigación",
            "configured": keys["search_api_key"],
            "state": "implementado" if keys["search_api_key"] else "mock",
            "note": "Adaptador Brave preparado; no validado. En demo, evidencia ficticia marcada (dominio .invalid).",
        },
        {
            "key": "editorial_llm",
            "name": "Modelo editorial (extracción y guiones)",
            "configured": keys["llm_api_key"],
            "state": "implementado" if keys["llm_api_key"] else "mock",
            "note": "Adaptador REST compatible OpenAI preparado; no validado. Modo demo determinista verificado.",
        },
        {
            "key": "asr",
            "name": "Transcripción de audio (ASR)",
            "configured": False,
            "state": "mock",
            "note": "Sólo interfaz preparada: falta proveedor. Puedes aportar transcripciones manualmente.",
        },
        {
            "key": "video_production",
            "name": "Producción de vídeo (Google Flow/APIMart)",
            "configured": False,
            "state": "fuera_de_mvp",
            "note": "Fuera del MVP. Se entregan prompts y storyboard para uso manual.",
        },
    ]
    return {"demo_mode": demo, "paid_services_enabled": get_budget(db)["paid_services_enabled"], "providers": items}


@router.get("/settings/score-weights")
def get_score_weights(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    row = db.get(Setting, "score_weights")
    from ..services.research import DEFAULT_SCORE_WEIGHTS

    return {**DEFAULT_SCORE_WEIGHTS, **(row.value if row and isinstance(row.value, dict) else {})}


@router.put("/settings/score-weights")
def put_score_weights(payload: dict, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    from ..services.research import DEFAULT_SCORE_WEIGHTS

    clean = {k: float(payload.get(k, DEFAULT_SCORE_WEIGHTS[k])) for k in DEFAULT_SCORE_WEIGHTS}
    db.merge(Setting(key="score_weights", value=clean))
    db.flush()
    return clean
