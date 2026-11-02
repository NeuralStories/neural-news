"""NN-117.4 — Rutas de modelo por tarea, con instantánea en el trabajo.

Port de `model_routes` del hermano congelado (`c0f68f32807d`).

Reglas comprobadas:

  - la ruta que gana es la de **menor prioridad** entre las habilitadas;
  - el trabajo guarda la **instantánea** al encolarse (ruta, modelo, revisión);
  - **cambiar la ruta después no altera el trabajo en marcha**: es el motivo de
    que exista la instantánea;
  - sin rutas configuradas, el comportamiento es el de siempre (el modelo de
    la configuración): la tabla no cambia nada por existir.
"""
from __future__ import annotations

import pytest

from neuralnews.db import get_session_factory
from neuralnews.models import Job, ModelRoute
from neuralnews.queue import enqueue
from neuralnews.services import model_routes


def _ruta(tarea: str, proveedor: str, modelo: str | None, prioridad: int, activa: bool = True) -> ModelRoute:
    session_factory = get_session_factory()
    with session_factory() as db:
        ruta = ModelRoute(
            task=tarea,
            provider=proveedor,
            model=modelo,
            priority=prioridad,
            enabled=activa,
        )
        db.add(ruta)
        db.commit()
        return ruta.id


def test_sin_rutas_se_usa_el_modelo_de_la_configuracion(app_env) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        instantanea = model_routes.instantanea(db, "editorial_llm", "modelo-configurado")
    assert instantanea["route_id"] is None
    assert instantanea["model"] == "modelo-configurado"
    assert instantanea["source"] == "configuracion"


def test_la_ruta_de_menor_prioridad_gana(app_env) -> None:
    _ruta("editorial_llm", "llm_api_key", "modelo-principal", 10)
    _ruta("editorial_llm", "otra_clave", "modelo-alternativo", 1)
    session_factory = get_session_factory()
    with session_factory() as db:
        ruta = model_routes.resolver_ruta(db, "editorial_llm")
        assert ruta is not None
        assert ruta.model == "modelo-alternativo"


def test_una_ruta_desactivada_no_gana(app_env) -> None:
    _ruta("editorial_llm", "llm_api_key", "modelo-principal", 1, activa=False)
    _ruta("editorial_llm", "otra_clave", "modelo-alternativo", 5)
    session_factory = get_session_factory()
    with session_factory() as db:
        ruta = model_routes.resolver_ruta(db, "editorial_llm")
        assert ruta is not None
        assert ruta.model == "modelo-alternativo"


def test_el_trabajo_guarda_la_instantanea_al_encolarse(app_env) -> None:
    _ruta("editorial_llm", "llm_api_key", "modelo-de-la-ruta", 1)
    session_factory = get_session_factory()
    with session_factory() as db:
        trabajo, _ = enqueue(db, "draft_script", {"story_id": 1})
        db.commit()
        instantanea = trabajo.model_snapshot
    assert instantanea is not None
    assert instantanea["model"] == "modelo-de-la-ruta"
    assert instantanea["source"] == "ruta"
    assert instantanea["config_revision"] >= 1


def test_cambiar_la_ruta_no_altera_el_trabajo_ya_encolado(app_env) -> None:
    """El motivo de la instantánea: el trabajo en marcha no cambia de modelo."""
    identificador = _ruta("editorial_llm", "llm_api_key", "modelo-original", 1)
    session_factory = get_session_factory()
    with session_factory() as db:
        trabajo, _ = enqueue(db, "draft_script", {"story_id": 1})
        db.commit()
        trabajo_id = trabajo.id

    # Se cambia la ruta (incluso se desactiva).
    with session_factory() as db:
        ruta = db.get(ModelRoute, identificador)
        ruta.model = "modelo-cambiado"
        ruta.enabled = False
        ruta.config_revision = ruta.config_revision + 1
        db.commit()

    with session_factory() as db:
        trabajo = db.get(Job, trabajo_id)
        assert model_routes.modelo_del_trabajo(trabajo, "modelo-configurado") == "modelo-original"


def test_un_trabajo_sin_instantanea_usa_el_modelo_actual(app_env) -> None:
    """Lo encolado antes de existir la tabla no se rompe."""
    session_factory = get_session_factory()
    with session_factory() as db:
        trabajo = Job(type="draft_script", payload={}, status="QUEUED")
        db.add(trabajo)
        db.commit()
        assert model_routes.modelo_del_trabajo(trabajo, "modelo-configurado") == "modelo-configurado"


def test_las_rutas_se_consultan_por_la_api(demo_client) -> None:
    _ruta("editorial_llm", "llm_api_key", "modelo-visible", 1)
    respuesta = demo_client.get("/api/v1/model-routes")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "editorial_llm" in cuerpo["tareas"]
    assert any(r["model"] == "modelo-visible" for r in cuerpo["items"])
    assert cuerpo["resolucion"]["editorial_llm"] == "modelo-visible"


def test_en_demo_no_se_cambian_las_rutas(demo_client) -> None:
    respuesta = demo_client.put(
        "/api/v1/model-routes",
        json={"task": "editorial_llm", "provider": "llm_api_key", "model": "otro"},
    )
    assert respuesta.status_code == 400
    assert "demo" in respuesta.json()["detail"].lower()


def test_una_tarea_desconocida_se_rechaza(demo_client) -> None:
    respuesta = demo_client.put(
        "/api/v1/model-routes", json={"task": "tarea_imaginaria", "provider": "llm_api_key"}
    )
    assert respuesta.status_code == 422
    assert "desconocida" in respuesta.json()["detail"].lower()
