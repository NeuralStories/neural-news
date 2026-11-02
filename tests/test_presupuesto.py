"""NN-116 — El presupuesto se verifica ANTES de la llamada y se consume de verdad.

Dos huecos reales (hallazgo P6 de la auditoría):

  1. La redacción del guion (`draft_script`) **no comprobaba el presupuesto**
     antes de llamar al modelo: el límite diario no le afectaba.
  2. Las llamadas de búsqueda y de modelo se registraban con `cost_estimate=0.0`:
     el gasto acumulado nunca crecía y **el límite diario no llegaba a dispararse**.
"""
from __future__ import annotations

import pytest

from neuralnews.db import get_session_factory
from neuralnews.models import Job, Story, UsageEvent
from neuralnews.queue import enqueue
from neuralnews.services import budget as budget_service


def _rechazar(*_args, **_kwargs):
    raise budget_service.BudgetExceeded("Presupuesto diario agotado (5.00 de 0.50 €).")


@pytest.fixture()
def sin_demo(monkeypatch):
    """El worker fuera del modo demo: es cuando hay llamada de pago de verdad."""
    from neuralnews import worker_tasks
    from neuralnews.services import budget as budget_mod

    class _Ajustes:
        demo_mode = False
        llm_model = "m"
        paid_services_enabled = True
        budget_daily_eur = 0.0

    monkeypatch.setattr(worker_tasks, "get_settings", lambda: _Ajustes())
    monkeypatch.setattr(budget_mod, "get_settings", lambda: _Ajustes())
    return _Ajustes()


def test_los_costes_por_proveedor_estan_declarados():
    """Cada proveedor de pago tiene un coste estimado declarado."""
    for proveedor in ("search", "editorial_llm", "gemini", "extraction"):
        assert budget_service.coste_estimado(proveedor) > 0, proveedor
    assert budget_service.coste_estimado("desconocido") == 0.0


def test_el_gasto_acumulado_impide_superar_el_limite(demo_client, sin_demo):
    """Con el límite consumido, la llamada se bloquea ANTES de gastar."""
    with get_session_factory()() as db:
        db.add(
            UsageEvent(
                provider="editorial_llm",
                model="m",
                cost_estimate=0.0,
                cost_actual=1.0,
                event="call",
            )
        )
        db.commit()
        budget_service.set_budget(
            db, paid_services_enabled=True, daily_limit_eur=0.5
        )
        db.commit()

        with pytest.raises(budget_service.BudgetExceeded) as exc:
            budget_service.assert_paid_call_allowed(
                db, "editorial_llm", estimated_cost_eur=0.01
            )
        assert "agotado" in str(exc.value).lower()


def test_el_borrador_se_bloquea_si_el_presupuesto_esta_agotado(
    demo_client, worker, sin_demo, monkeypatch
):
    """La ruta del guion comprueba el presupuesto ANTES de llamar al modelo."""
    from neuralnews import worker_tasks

    demo_client.post(
        "/api/v1/sources",
        json={"text": "Cortexa Labs ha anunciado Radar y Vireo AI ha levantado 40 millones."},
    )
    worker()
    historias = demo_client.get("/api/v1/stories").json()["items"]
    assert historias, "debe haber una noticia candidata"
    story_id = historias[0]["id"]

    with get_session_factory()() as db:
        db.add(
            UsageEvent(
                provider="editorial_llm",
                model="m",
                cost_estimate=0.0,
                cost_actual=5.0,
                event="call",
            )
        )
        db.commit()

    monkeypatch.setattr(
        worker_tasks.budget_service, "assert_paid_call_allowed", _rechazar
    )

    with get_session_factory()() as db:
        job, _ = enqueue(
            db,
            worker_tasks.DRAFT_SCRIPT,
            {"story_id": story_id},
            dedupe_key=f"test-presupuesto-{story_id}",
        )
        job_id = job.id
        db.commit()
    worker()

    with get_session_factory()() as db:
        trabajo = db.get(Job, job_id)
        assert trabajo is not None
        assert trabajo.status == "FAILED", trabajo.error
        assert trabajo.error_kind == "budget"
        assert "agotado" in (trabajo.error or "").lower()


def test_la_creacion_del_borrador_no_llega_a_hacerse(demo_client, worker, sin_demo, monkeypatch):
    """Si el presupuesto corta, **no** se crea una versión de guion."""
    from neuralnews import worker_tasks

    demo_client.post(
        "/api/v1/sources",
        json={"text": "Cortexa Labs ha anunciado Radar y Vireo AI ha levantado 40 millones."},
    )
    worker()
    historias = demo_client.get("/api/v1/stories").json()["items"]
    story_id = historias[0]["id"]

    with get_session_factory()() as db:
        db.add(
            UsageEvent(
                provider="editorial_llm",
                model="m",
                cost_estimate=0.0,
                cost_actual=5.0,
                event="call",
            )
        )
        db.commit()

    monkeypatch.setattr(
        worker_tasks.budget_service, "assert_paid_call_allowed", _rechazar
    )

    with get_session_factory()() as db:
        job, _ = enqueue(
            db,
            worker_tasks.DRAFT_SCRIPT,
            {"story_id": story_id},
            dedupe_key=f"test-presupuesto-b-{story_id}",
        )
        job_id = job.id
        db.commit()
    worker()

    with get_session_factory()() as db:
        historia = db.get(Story, story_id)
        assert historia is not None
        assert not historia.script_versions, (
            "no debe existir ninguna versión de guion si el presupuesto cortó la llamada"
        )
