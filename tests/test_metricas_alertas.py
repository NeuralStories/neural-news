"""NN-115.3, .4 y .5 — métricas, alertas y su visibilidad en la UI.

Criterios:
  - **NN-115.3**: métricas consultables (p95, tasa de fallo, duración, cola).
  - **NN-115.4**: alertas visibles (cola parada, lease vencido, presupuesto al
    80 %, fallo repetido).
  - **NN-115.5**: un fallo de proveedor se ve en la UI en **menos de 60 s**
    (prueba cronometrada).
"""
from __future__ import annotations

import time
from datetime import timedelta

import pytest

from neuralnews.db import get_session_factory
from neuralnews.models import Job, Setting, UsageEvent, utcnow
from neuralnews.queue import enqueue


def _crear_trabajo(tipo: str, **campos) -> int:
    session_factory = get_session_factory()
    with session_factory() as db:
        trabajo, _ = enqueue(db, tipo, {"demo": True}, dedupe_key=f"{tipo}-{utcnow().timestamp()}-{campos}")
        for clave, valor in campos.items():
            setattr(trabajo, clave, valor)
        db.add(trabajo)
        db.commit()
        return trabajo.id


def test_las_metricas_se_consultan(demo_client) -> None:
    respuesta = demo_client.get("/api/v1/metrics")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    metricas = cuerpo["metricas"]
    for clave in (
        "p95_duracion_s",
        "tasa_fallo",
        "duracion_media_s",
        "profundidad_cola",
        "jobs_total",
        "ventana_horas",
    ):
        assert clave in metricas, f"falta la métrica {clave}"
    assert "alertas" in cuerpo


def test_la_tasa_de_fallo_y_el_p95_son_reales(demo_client) -> None:
    """Dos trabajos terminados (uno lento) y uno fallido."""
    ahora = utcnow()
    _crear_trabajo(
        "job_rapido",
        status="DONE",
        started_at=ahora - timedelta(seconds=10),
        finished_at=ahora - timedelta(seconds=9),
    )
    _crear_trabajo(
        "job_lento",
        status="DONE",
        started_at=ahora - timedelta(seconds=100),
        finished_at=ahora,
    )
    _crear_trabajo("job_fallido", status="FAILED", error="se rompió", error_kind="connector")

    metricas = demo_client.get("/api/v1/metrics").json()["metricas"]
    assert metricas["jobs_total"] >= 3
    assert metricas["jobs_fallidos"] >= 1
    assert 0 < metricas["tasa_fallo"] < 1
    assert metricas["p95_duracion_s"] is not None
    assert metricas["p95_duracion_s"] >= metricas["duracion_media_s"]
    assert metricas["por_error_kind"].get("connector", 0) >= 1


def test_la_profundidad_de_cola_cuenta_lo_pendiente(demo_client) -> None:
    antes = demo_client.get("/api/v1/metrics").json()["metricas"]["profundidad_cola"]
    _crear_trabajo("job_en_cola", status="QUEUED")
    despues = demo_client.get("/api/v1/metrics").json()["metricas"]["profundidad_cola"]
    assert despues == antes + 1


def test_alerta_de_cola_parada(demo_client) -> None:
    """Un trabajo en cola viejo y sin recoger = el worker está parado."""
    viejo = utcnow() - timedelta(minutes=30)
    _crear_trabajo("job_olvidado", status="QUEUED", created_at=viejo)
    alertas = demo_client.get("/api/v1/metrics").json()["alertas"]
    codigos = [a["codigo"] for a in alertas]
    assert "cola_parada" in codigos
    aviso = next(a for a in alertas if a["codigo"] == "cola_parada")
    assert aviso["severidad"] == "error"
    assert "worker" in aviso["mensaje"]


def test_alerta_de_lease_vencido(demo_client) -> None:
    _crear_trabajo(
        "job_en_marcha",
        status="RUNNING",
        lease_until=utcnow() - timedelta(seconds=300),
    )
    alertas = demo_client.get("/api/v1/metrics").json()["alertas"]
    codigos = [a["codigo"] for a in alertas]
    assert "lease_vencido" in codigos


def test_alerta_de_presupuesto_al_80_por_ciento(demo_client) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        db.merge(Setting(key="budget", value={"paid_services_enabled": True, "daily_limit_eur": 1.0}))
        db.add(
            UsageEvent(
                provider="editorial_llm",
                cost_estimate=0.9,
                cost_actual=0.9,
                event="call",
            )
        )
        db.commit()
    alertas = demo_client.get("/api/v1/metrics").json()["alertas"]
    aviso = next((a for a in alertas if a["codigo"] == "presupuesto_cercano"), None)
    assert aviso is not None, alertas
    assert "90" in aviso["mensaje"] or "89" in aviso["mensaje"]


def test_alerta_de_fallo_repetido(demo_client) -> None:
    for _ in range(3):
        _crear_trabajo(
            "transcribe_source",
            status="FAILED",
            error="fallo del conector",
            error_kind="connector",
        )
    alertas = demo_client.get("/api/v1/metrics").json()["alertas"]
    aviso = next((a for a in alertas if a["codigo"] == "fallo_repetido"), None)
    assert aviso is not None, alertas
    assert "transcribe_source" in aviso["mensaje"]


def test_sin_problemas_no_hay_alertas(demo_client) -> None:
    """Con la cola vacía y sin fallos no se inventan avisos."""
    alertas = demo_client.get("/api/v1/metrics").json()["alertas"]
    assert alertas == [], alertas


def test_nn115_5_el_fallo_de_proveedor_se_ve_en_menos_de_60_segundos(demo_client) -> None:
    """Prueba cronometrada: el fallo se ve en la UI (lo que consume `/ops`)."""
    inicio = time.monotonic()

    # 1. Falla el proveedor: tres trabajos con el mismo motivo.
    for _ in range(3):
        _crear_trabajo(
            "research_story",
            status="FAILED",
            error="el proveedor no responde",
            error_kind="connector",
        )

    # 2. El operador mira la página de operación.
    respuesta = demo_client.get("/api/v1/metrics")
    elapsed = time.monotonic() - inicio

    assert respuesta.status_code == 200
    alertas = respuesta.json()["alertas"]
    assert any(a["codigo"] == "fallo_repetido" for a in alertas), alertas
    assert elapsed < 60, f"tardó {elapsed:.1f} s en verse el fallo"


@pytest.mark.parametrize("codigo", ["cola_parada", "lease_vencido", "fallo_repetido"])
def test_las_alertas_declaran_su_codigo_y_su_mensaje(demo_client, codigo) -> None:
    """Cada alerta dice qué es y qué hacer: sin mensaje no es una alerta."""
    alertas = demo_client.get("/api/v1/metrics").json()["alertas"]
    for alerta in alertas:
        assert alerta["codigo"]
        assert alerta["mensaje"]
        assert alerta["severidad"] in {"aviso", "error"}
