"""Fase 8 — control de presupuesto por lote (T514).

Verifica el techo **agregado** del lote sobre la base de `max_cost_eur` y
`enqueue_av_render`:

- un trabajo cuyo coste estimado cabe en el techo se encola y reserva presupuesto;
- el trabajo siguiente que no cabe **no se encola** (no queda nada pendiente);
- el presupuesto liberado al fallar un trabajo vuelve a estar disponible;
- el resumen de presupuesto del lote refleja reservado, gastado y disponible.
"""
from __future__ import annotations

import pytest

from neuralnews.db import session_scope
from neuralnews.models import Batch, BatchItem, Job, Story
from neuralnews.services.av_jobs import (
    batch_budget_summary,
    enqueue_av_render,
    release_batch_budget,
    set_batch_budget,
)
from neuralnews.services.budget import BudgetExceeded


def _lote_con_noticias(db, count: int = 3) -> int:
    batch = Batch(name="Lote con presupuesto", target_size=5)
    db.add(batch)
    db.flush()
    for i in range(count):
        story = Story(topic_key=f"lote-precio-{i}", title=f"Noticia del lote {i}", summary="Resumen.")
        db.add(story)
        db.flush()
        db.add(BatchItem(batch_id=batch.id, story_id=story.id, position=i))
    db.flush()
    return batch.id


def _plan(index: int) -> dict:
    return {
        "projectId": f"proj-presupuesto-{index}",
        "storyRef": {"storyId": str(index), "title": "Noticia", "revision": 1},
        "profileId": "neuralnews-canon-v1",
        "profileVersion": "1.0.0",
        "outputFormat": "9:16",
        "scenes": [
            {
                "sceneIndex": 1,
                "sceneType": "cierre",
                "scriptSnippet": "Cierre de prueba.",
                "imagePrompt": "s",
                "framing": "pecho",
                "movement": "chest_punch_zoom",
                "transition": "corte_directo",
                "estDurationSeconds": 1.5,
                "referenceIds": [],
            }
        ],
        "warnings": [],
    }


def test_el_techo_por_lote_bloquea_el_encolado_de_lo_que_no_cabe(app_env):
    with session_scope() as db:
        batch_id = _lote_con_noticias(db)
        set_batch_budget(db, batch_id, limit_eur=0.10)

        # 1) Este trabajo cabe (0,08 € de 0,10 €).
        job1, created1 = enqueue_av_render(
            db, _plan(1), batch_id=batch_id, estimated_cost_eur=0.08
        )
        assert created1 is True
        assert job1.id is not None

        # 2) Este NO cabe (0,08 + 0,05 > 0,10): no debe encolarse.
        with pytest.raises(BudgetExceeded) as excinfo:
            enqueue_av_render(db, _plan(2), batch_id=batch_id, estimated_cost_eur=0.05)
        assert "presupuesto" in str(excinfo.value).lower()

        # 3) No queda ningún trabajo pendiente del plan rechazado.
        jobs = db.query(Job).filter_by(type="av_render").all()
        assert [j.payload["plan"]["projectId"] for j in jobs] == ["proj-presupuesto-1"]

        # 4) El resumen del lote refleja la reserva.
        summary = batch_budget_summary(db, batch_id)
        assert summary["limit_eur"] == pytest.approx(0.10)
        assert summary["committed_eur"] == pytest.approx(0.08)
        assert summary["available_eur"] == pytest.approx(0.02)


def test_el_presupuesto_liberado_vuelve_a_estar_disponible(app_env):
    with session_scope() as db:
        batch_id = _lote_con_noticias(db)
        set_batch_budget(db, batch_id, limit_eur=0.10)
        enqueue_av_render(db, _plan(1), batch_id=batch_id, estimated_cost_eur=0.08)
        assert batch_budget_summary(db, batch_id)["committed_eur"] == pytest.approx(0.08)

        # Si el trabajo falla, la reserva se libera y otro trabajo puede entrar.
        release_batch_budget(db, batch_id, 0.08)
        summary = batch_budget_summary(db, batch_id)
        assert summary["committed_eur"] == pytest.approx(0.0)
        assert summary["available_eur"] == pytest.approx(0.10)

        job2, created = enqueue_av_render(db, _plan(2), batch_id=batch_id, estimated_cost_eur=0.10)
        assert created is True


def test_un_lote_sin_techo_no_limita_el_encolado(app_env):
    with session_scope() as db:
        batch_id = _lote_con_noticias(db)
        for i in range(3):
            job, created = enqueue_av_render(
                db, _plan(i + 10), batch_id=batch_id, estimated_cost_eur=5.0
            )
            assert created is True
        summary = batch_budget_summary(db, batch_id)
        assert summary["limit_eur"] is None
        assert summary["available_eur"] is None


def test_el_endpoint_expone_y_actualiza_el_techo_del_lote(demo_client, worker, app_env):
    with session_scope() as db:
        batch_id = _lote_con_noticias(db)

    detalle = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert detalle["budget"]["limit_eur"] is None

    respuesta = demo_client.put(f"/api/v1/batches/{batch_id}/budget", json={"limit_eur": 2.5})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["limit_eur"] == pytest.approx(2.5)

    detalle2 = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert detalle2["budget"]["limit_eur"] == pytest.approx(2.5)

    # Techo negativo: se rechaza con mensaje claro.
    negativo = demo_client.put(f"/api/v1/batches/{batch_id}/budget", json={"limit_eur": -1})
    assert negativo.status_code == 400
