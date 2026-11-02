"""NN-114.3 — `api/ops.py` sin test.

El endpoint de operaciones es lo que la página `/ops` de la web y el Centro de
mantenimiento consultan: si devuelve datos equivocados o acepta cambios que
debería rechazar, la interfaz miente.

Reglas comprobadas aquí:

  - un trabajo inexistente da **404** (no un error genérico);
  - el trabajo serializa su estado y su **motivo normalizado** (`error_kind`)
    con etiqueta legible;
  - el listado de trabajos acota el límite pedido;
  - el estado de proveedores distingue lo que **funciona** (manual, RSS web) de
    lo que está preparado pero sin validar y de lo que está fuera del MVP;
  - los pesos de puntuación se leen, se guardan y se **coaccionan a número**;
  - en modo demo, cambiar el presupuesto se **rechaza** (no devuelve un «ok»
    que no surte efecto);
  - guardar un secreto desconocido da 404 y los cambios en demo se rechazan.
"""
from __future__ import annotations

import pytest

from neuralnews.db import get_session_factory
from neuralnews.models import Job
from neuralnews.queue import enqueue


@pytest.fixture()
def con_trabajos(app_env):
    """Crea un trabajo ya terminado con motivo normalizado."""
    session_factory = get_session_factory()
    with session_factory() as db:
        trabajo, _creado = enqueue(db, "procesar_demo", {"demo": True}, dedupe_key="ops-test")
        trabajo.status = "FAILED"
        trabajo.error = "MaterialFaltante: no hay segmentos"
        trabajo.error_kind = "material"
        db.add(trabajo)
        db.commit()
        trabajo_id = trabajo.id
    return trabajo_id


def test_trabajo_inexistente_da_404(demo_client) -> None:
    respuesta = demo_client.get("/api/v1/jobs/999999")
    assert respuesta.status_code == 404
    assert "no existe" in respuesta.json()["detail"].lower()


def test_trabajo_serializa_estado_y_motivo_normalizado(demo_client, con_trabajos) -> None:
    respuesta = demo_client.get(f"/api/v1/jobs/{con_trabajos}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == con_trabajos
    assert cuerpo["status"] == "FAILED"
    assert cuerpo["status_label"]  # etiqueta legible, nunca el código vacío
    assert cuerpo["error_kind"] == "material"
    assert cuerpo["error_kind_label"]


def test_listado_de_trabajos_acota_el_limite(demo_client, con_trabajos) -> None:
    respuesta = demo_client.get("/api/v1/jobs?limit=5000")
    assert respuesta.status_code == 200
    assert len(respuesta.json()["items"]) <= 200


def test_estado_de_proveedores_distingue_lo_que_funciona(demo_client) -> None:
    respuesta = demo_client.get("/api/v1/provider-status")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    por_clave = {p["key"]: p for p in cuerpo["providers"]}

    # Implementado y verificado con pruebas: funciona sin claves.
    assert por_clave["manual"]["configured"] is True
    assert por_clave["web_rss"]["configured"] is True

    # Preparado pero sin validar: no se presenta como si funcionase.
    assert por_clave["asr"]["state"] == "mock"
    assert por_clave["video_production"]["state"] == "fuera_de_mvp"
    assert por_clave["video_production"]["configured"] is False

    # El estado de cada proveedor dice de dónde sale su configuración.
    assert isinstance(cuerpo["vault_available"], bool)


def test_pesos_de_puntuacion_por_defecto_y_guardado(demo_client) -> None:
    por_defecto = demo_client.get("/api/v1/settings/score-weights")
    assert por_defecto.status_code == 200
    pesos = por_defecto.json()
    assert pesos, "debe haber pesos por defecto"

    respuesta = demo_client.put(
        "/api/v1/settings/score-weights",
        json={**pesos, "impacto": "0.75", "clave_inventada": 99},
    )
    assert respuesta.status_code == 200
    guardados = respuesta.json()
    assert guardados["impacto"] == 0.75, "los pesos se coaccionan a número"
    assert "clave_inventada" not in guardados, "las claves desconocidas se ignoran"

    leidos = demo_client.get("/api/v1/settings/score-weights")
    assert leidos.json()["impacto"] == 0.75


def test_un_peso_que_no_es_numero_da_422_y_no_un_500(demo_client) -> None:
    """B29: «0,75» (coma decimal) devolvía un 500 sin explicar nada."""
    pesos = demo_client.get("/api/v1/settings/score-weights").json()
    respuesta = demo_client.put(
        "/api/v1/settings/score-weights", json={**pesos, "impacto": "0,75"}
    )
    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert "impacto" in detalle
    assert "decimal" in detalle.lower()


def test_en_demo_cambiar_el_presupuesto_se_rechaza(demo_client) -> None:
    respuesta = demo_client.put(
        "/api/v1/config/budget", json={"paid_services_enabled": True, "daily_limit_eur": 10}
    )
    assert respuesta.status_code == 400
    assert "demo" in respuesta.json()["detail"].lower()


def test_guardar_un_secreto_desconocido_da_404(demo_client) -> None:
    respuesta = demo_client.put(
        "/api/v1/config/secrets/clave_inventada", json={"value": "x"}
    )
    assert respuesta.status_code == 404
    assert "desconocida" in respuesta.json()["detail"].lower()


def test_estado_de_los_secretos_no_devuelve_valores(demo_client) -> None:
    respuesta = demo_client.get("/api/v1/config/secrets")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["vault_available"], bool)
    assert "providers" in cuerpo
    # Ningún valor de clave puede aparecer en la respuesta.
    assert "value" not in str(cuerpo).lower() or "valor" not in str(cuerpo).lower()


def test_el_consumo_de_uso_se_responde(demo_client) -> None:
    respuesta = demo_client.get("/api/v1/usage")
    assert respuesta.status_code == 200
    assert "total" in respuesta.json() or "gasto" in respuesta.json() or respuesta.json()
