"""Trabajos, consumo, configuración y estado de proveedores."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..config import get_settings
from ..db import get_db
from ..errors import error_kind_label
from ..models import Job, Setting
from ..schemas import BudgetUpdate, JobOut, SecretPayload
from ..security import get_current_actor, require_demo_disabled
from ..services import secrets as secrets_service
from ..services.budget import get_budget, set_budget, usage_summary
from ..states import JOB_LABELS
from .. import vault

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
        "error_kind": job.error_kind,
        "error_kind_label": error_kind_label(job.error_kind),
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
                "error_kind": j.error_kind,
                "error_kind_label": error_kind_label(j.error_kind),
                "created_at": j.created_at.isoformat(),
            }
            for j in rows
        ]
    }


@router.get("/usage")
def usage(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    return usage_summary(db)


@router.get("/metrics")
def metricas(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Métricas y alertas del sistema (NN-115.3 y NN-115.4).

    Todo se calcula de la base de datos (no de memoria): las métricas sobreviven
    a un reinicio y funcionan con varios workers.
    """
    from ..metrics import estado_operativo

    return estado_operativo(db)


@router.get("/model-routes")
def listar_model_routes(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Rutas de modelo por tarea y cómo se resolvería cada una (NN-117.4)."""
    from ..services import model_routes

    rutas = model_routes.listar_rutas(db)
    return {
        "items": [model_routes.payload_de_ruta(ruta) for ruta in rutas],
        "tareas": list(model_routes.TAREAS),
        "resolucion": {
            tarea: model_routes.instantanea(db, tarea).get("model")
            for tarea in model_routes.TAREAS
        },
    }


@router.put("/model-routes")
def guardar_model_route(
    payload: dict, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """Crea o actualiza la ruta de una tarea (NN-117.4).

    Cambiar una ruta **no** altera los trabajos ya encolados: cada uno guarda su
    instantánea.
    """
    from ..models import ModelRoute
    from ..services import model_routes

    tarea = str(payload.get("task") or "").strip()
    proveedor = str(payload.get("provider") or "").strip()
    if not tarea or not proveedor:
        raise HTTPException(status_code=422, detail="Indica «task» y «provider».")
    if tarea not in model_routes.TAREAS:
        raise HTTPException(
            status_code=422,
            detail=f"Tarea desconocida: {tarea}. Conocidas: {list(model_routes.TAREAS)}",
        )
    require_demo_disabled()
    if actor["is_demo"]:
        raise HTTPException(
            status_code=403,
            detail="En sesión de demostración los cambios no afectan a servicios reales",
        )
    modelo = payload.get("model")
    ruta = db.scalar(
        select(ModelRoute).where(ModelRoute.task == tarea, ModelRoute.provider == proveedor)
    )
    if ruta is None:
        ruta = ModelRoute(task=tarea, provider=proveedor)
        db.add(ruta)
    ruta.model = str(modelo) if modelo else None
    ruta.priority = int(payload.get("priority", ruta.priority) or 0)
    ruta.enabled = bool(payload.get("enabled", True))
    ruta.timeout_seconds = payload.get("timeout_seconds")
    # Cada cambio de configuración sube la revisión: es lo que se ve en la
    # instantánea de los trabajos que se encolen a partir de ahora.
    ruta.config_revision = ruta.config_revision + 1
    db.flush()
    db.commit()
    return model_routes.payload_de_ruta(ruta)


@router.put("/config/budget")
def update_budget(
    payload: BudgetUpdate, db=Depends(get_db), actor=Depends(get_current_actor)
) -> dict:
    """Activa o ajusta el presupuesto de los servicios de pago.

    Con el modo demo activo el cambio **no** surte efecto (todo se simula), así
    que se rechaza en lugar de devolver un «ok» que engaña.
    """
    require_demo_disabled()
    return set_budget(
        db,
        paid_services_enabled=payload.paid_services_enabled,
        daily_limit_eur=payload.daily_limit_eur,
    )


@router.get("/config/secrets")
def listar_secretos(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Estado de las claves de proveedor: de dónde viene cada una, nunca su valor."""
    return {
        "vault_available": vault.clave_maestra_configurada(),
        "providers": secrets_service.estado(db),
    }


@router.put("/config/secrets/{clave}")
def guardar_secreto(
    clave: str,
    payload: SecretPayload,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Guarda una clave de proveedor **cifrada** en la bóveda.

    Requiere clave maestra (`NEURAL_MASTER_KEY`) y una sesión que no sea de
    demostración: en demo el cambio no surtiría efecto sobre nada real.
    """
    if clave not in secrets_service.PROVEEDORES:
        raise HTTPException(
            status_code=404,
            detail=f"Clave desconocida: {clave}. Conocidas: {sorted(secrets_service.PROVEEDORES)}",
        )
    require_demo_disabled()
    if actor["is_demo"]:
        raise HTTPException(
            status_code=403,
            detail="En sesión de demostración los cambios no afectan a servicios reales",
        )
    if not vault.clave_maestra_configurada():
        raise HTTPException(
            status_code=503,
            detail=(
                "No hay clave maestra configurada (NEURAL_MASTER_KEY): "
                "no se pueden guardar secretos cifrados"
            ),
        )
    if not payload.value.strip():
        raise HTTPException(status_code=422, detail="El valor está vacío")
    try:
        secrets_service.guardar_clave(db, clave, payload.value.strip())
    except vault.ClaveMaestraAusente as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, "provider": secrets_service.nombre_proveedor(clave)}


@router.delete("/config/secrets/{clave}")
def borrar_secreto(
    clave: str,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Borra el secreto de la bóveda (vuelve al valor del entorno, si lo hay)."""
    if clave not in secrets_service.PROVEEDORES:
        raise HTTPException(status_code=404, detail=f"Clave desconocida: {clave}")
    require_demo_disabled()
    if actor["is_demo"]:
        raise HTTPException(
            status_code=403,
            detail="En sesión de demostración los cambios no afectan a servicios reales",
        )
    borrado = secrets_service.borrar_clave(db, clave)
    db.commit()
    return {"ok": True, "deleted": borrado, "provider": secrets_service.nombre_proveedor(clave)}


@router.get("/provider-status")
def provider_status(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    settings = get_settings()
    # Estado **efectivo**: la bóveda tiene prioridad sobre el entorno.
    efectivo = {
        clave: bool(secrets_service.clave_de_proveedor(clave))
        for clave in secrets_service.PROVEEDORES
    }
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
            "configured": efectivo["youtube_api_key"],
            "state": "implementado" if efectivo["youtube_api_key"] else "sin_clave",
            "note": "Adaptador real preparado con YouTube Data API v3; no validado con credenciales en este MVP.",
        },
        {
            "key": "gemini_video",
            "name": "Análisis de vídeo (Gemini)",
            "configured": efectivo["gemini_api_key"],
            "state": "implementado" if efectivo["gemini_api_key"] else "mock",
            "note": "Adaptador preparado (salida marcada como análisis, nunca transcripción literal); no validado sin clave.",
        },
        {
            "key": "spotify",
            "name": "Spotify / pódcast (metadatos)",
            "configured": efectivo["spotify_access_token"],
            "state": "implementado" if efectivo["spotify_access_token"] else "sin_clave",
            "note": "Adaptador preparado (get-an-episode exige autorización de usuario); no validado. Sin transcripción: estado «Solo información básica».",
        },
        {
            "key": "search",
            "name": "Búsqueda para investigación",
            "configured": efectivo["search_api_key"],
            "state": "implementado" if efectivo["search_api_key"] else "mock",
            "note": "Adaptador Brave preparado; no validado. En demo, evidencia ficticia marcada (dominio .invalid).",
        },
        {
            "key": "editorial_llm",
            "name": "Modelo editorial (extracción y guiones)",
            "configured": efectivo["llm_api_key"],
            "state": "implementado" if efectivo["llm_api_key"] else "mock",
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
    return {
        "demo_mode": demo,
        "paid_services_enabled": get_budget(db)["paid_services_enabled"],
        "providers": items,
        "vault_available": vault.clave_maestra_configurada(),
    }


@router.get("/settings/score-weights")
def get_score_weights(db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    row = db.get(Setting, "score_weights")
    from ..services.research import DEFAULT_SCORE_WEIGHTS

    return {**DEFAULT_SCORE_WEIGHTS, **(row.value if row and isinstance(row.value, dict) else {})}


@router.put("/settings/score-weights")
def put_score_weights(payload: dict, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Guarda los pesos de puntuación.

    Un peso que no es un número (por ejemplo «0,75» con coma decimal) devolvía
    un **500**: la excepción se escapaba sin traducir. Ahora se rechaza con un
    422 que dice qué peso falla y por qué (hallazgo B29).
    """
    from ..services.research import DEFAULT_SCORE_WEIGHTS

    clean: dict[str, float] = {}
    for clave, por_defecto in DEFAULT_SCORE_WEIGHTS.items():
        bruto = payload.get(clave, por_defecto)
        try:
            valor = float(bruto)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"El peso «{clave}» no es un número: {bruto!r}. "
                    "Usa punto decimal (0.75)."
                ),
            ) from None
        if valor != valor or valor in (float("inf"), float("-inf")):
            raise HTTPException(
                status_code=422,
                detail=f"El peso «{clave}» no es un número finito: {bruto!r}.",
            )
        clean[clave] = valor
    db.merge(Setting(key="score_weights", value=clean))
    db.flush()
    return clean
