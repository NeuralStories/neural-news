"""Rutas de modelo por tarea, con instantánea en el trabajo (NN-117.4).

Port de `app/domain/routes.py` del hermano congelado
(`archive/neuralnews-20261101`, commit `e03ad0c`, migración `c0f68f32807d`).

Una ruta es la combinación **(tarea, proveedor, modelo, prioridad)**:

- la **tarea** es el tipo de trabajo (`editorial_llm`, `search`, `gemini`…);
- el **proveedor** es la clave de la bóveda (`llm_api_key`, `search_api_key`…);
- el **modelo** es el modelo concreto que se usará, si la ruta lo fija;
- la **prioridad** ordena las rutas: gana la de menor número entre las
  habilitadas.

**Instantánea:** cuando se encola un trabajo se resuelve su ruta y se guarda
en `jobs.model_snapshot`. Si después se cambia (o desactiva) la ruta, el trabajo
que ya está en marcha **no** cambia: usó la configuración que tenía al encolarse.
Sin esto, cambiar una ruta a mitad de un trabajo haría que el mismo trabajo
usara dos modelos distintos.

Si no hay ninguna ruta configurada para la tarea, se usa el modelo de la
configuración (`NEURAL_LLM_MODEL`): **el comportamiento no cambia** por tener
esta tabla.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ModelRoute, utcnow

# Tareas que resuelven modelo en este producto.
TAREAS = ("editorial_llm", "search", "gemini", "extraction")

# Qué tarea de modelo corresponde a cada tipo de trabajo del worker.
TAREA_POR_TRABAJO = {
    "draft_script": "editorial_llm",
    "research_story": "search",
    "analyze_video": "gemini",
    "process_source": "extraction",
}


def resolver_ruta(db: Session, tarea: str) -> ModelRoute | None:
    """Ruta habilitada de mayor prioridad (menor número) para la tarea."""
    rutas = db.scalars(
        select(ModelRoute)
        .where(ModelRoute.task == tarea, ModelRoute.enabled.is_(True))
        .order_by(ModelRoute.priority, ModelRoute.id)
    ).all()
    return rutas[0] if rutas else None


def instantanea(db: Session, tarea: str, modelo_por_defecto: str | None = None) -> dict:
    """Instantánea de la ruta de la tarea, tal y como se guarda en el trabajo."""
    ruta = resolver_ruta(db, tarea)
    if ruta is None:
        return {
            "task": tarea,
            "route_id": None,
            "provider": None,
            "model": modelo_por_defecto,
            "config_revision": 0,
            "source": "configuracion",
            "resolved_at": utcnow().isoformat(),
        }
    return {
        "task": tarea,
        "route_id": ruta.id,
        "provider": ruta.provider,
        "model": ruta.model or modelo_por_defecto,
        "priority": ruta.priority,
        "timeout_seconds": ruta.timeout_seconds,
        "config_revision": ruta.config_revision,
        "source": "ruta",
        "resolved_at": utcnow().isoformat(),
    }


def modelo_del_trabajo(trabajo, modelo_por_defecto: str | None = None) -> str | None:
    """El modelo que debe usar un trabajo: el de su instantánea o el de ahora.

    Si el trabajo no tiene instantánea (encolado antes de existir esta tabla, o
    encolado sin ruta), se usa el modelo configurado: es el comportamiento
    anterior y no se cambia nada por el hecho de que la tabla exista.
    """
    instantanea_trabajo = getattr(trabajo, "model_snapshot", None)
    if isinstance(instantanea_trabajo, dict):
        modelo = instantanea_trabajo.get("model")
        if modelo:
            return str(modelo)
    return modelo_por_defecto


def listar_rutas(db: Session) -> list[ModelRoute]:
    return db.scalars(
        select(ModelRoute).order_by(ModelRoute.task, ModelRoute.priority, ModelRoute.id)
    ).all()


def payload_de_ruta(ruta: ModelRoute) -> dict:
    return {
        "id": ruta.id,
        "task": ruta.task,
        "provider": ruta.provider,
        "model": ruta.model,
        "priority": ruta.priority,
        "enabled": ruta.enabled,
        "timeout_seconds": ruta.timeout_seconds,
        "config_revision": ruta.config_revision,
    }
