"""Fase 8 — lotes de 5 y 10 noticias con proveedores simulados (T800-T810).

Comprueba: handoff de lote (cardinalidad 5/10), trabajos de composición
independientes por noticia, techo de presupuesto por trabajo en lote,
deduplicación ante reintentos, reanudación sólo de lo fallido y exportación
individual. Sin servicios de pago.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "contracts" / "consumer"))

from sqlalchemy import select  # noqa: E402

from neural_handoff_consumer import HandoffRegistry, import_handoff  # noqa: E402
from neuralnews.db import session_scope  # noqa: E402
from neuralnews.models import Job, RenderOutput  # noqa: E402
from neuralnews.services.av_jobs import enqueue_av_render  # noqa: E402
from neuralnews.services.handoff import emit_batch_handoff  # noqa: E402


def _create_approved_stories(demo_client, worker, count: int) -> list[int]:
    ids: list[int] = []
    for i in range(count):
        # Texto único por noticia: el extractor demo fusiona candidatos por tema.
        text = (
            f"Noticia de lote número {i}: la empresa ficticia Acme Instruments ha presentado "
            f"el dispositivo L{i} con mejoras documentadas en su web de demostración."
        )
        payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
        worker()
        detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
        story_id = detail["stories"][0]["id"]
        demo_client.post(f"/api/v1/stories/{story_id}/research")
        demo_client.post(f"/api/v1/stories/{story_id}/draft")
        worker()
        detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
        version_id = detail["script_versions"][-1]["id"]
        response = demo_client.post(
            f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version_id}
        )
        assert response.status_code == 200, response.text
        ids.append(story_id)
    return ids


def _plan_for(story: dict, index: int) -> dict:
    return {
        "projectId": f"proj-lote-{story['story_id']}",
        "storyRef": {"storyId": story["story_id"], "title": story["title"], "revision": story["revision"]},
        "profileId": "neuralnews-canon-v1",
        "profileVersion": "1.0.0",
        "outputFormat": "9:16",
        "glitch": False,
        "scenes": [
            {
                "sceneIndex": 1,
                "sceneType": "apertura",
                "scriptSnippet": story["script"][:120] or "Entrada del noticiario.",
                "imagePrompt": "simulado",
                "framing": "pecho",
                "movement": "lateral_slide_in",
                "transition": "corte_directo",
                "estDurationSeconds": 1.5,
                "referenceIds": [],
            },
            {
                "sceneIndex": 2,
                "sceneType": "cierre",
                "scriptSnippet": story["script"][-100:] or "Cierre del noticiario.",
                "imagePrompt": "simulado",
                "framing": "pecho",
                "movement": "chest_punch_zoom",
                "transition": "corte_directo",
                "estDurationSeconds": 1.5,
                "referenceIds": [],
            },
        ],
        "warnings": [],
    }


@pytest.mark.parametrize("size", [5, 10])
def test_lote_completo_simulado(demo_client, worker, app_env, size):
    # T800/T801: importación de 5 y 10 noticias mediante el handoff de lote.
    story_ids = _create_approved_stories(demo_client, worker, size)
    created = demo_client.post(
        "/api/v1/batches",
        json={"name": f"Lote {size}", "target_size": size, "story_ids": story_ids},
    )
    assert created.status_code == 200, created.text
    batch_id = created.json()["id"]

    with session_scope() as db:
        document = emit_batch_handoff(db, batch_id)
    assert document["mode"] == "batch" and len(document["stories"]) == size
    imported = import_handoff(document, HandoffRegistry())
    assert len(imported) == size

    # T802: trabajos de composición independientes por noticia.
    job_ids: list[int] = []
    for index, story in enumerate(imported):
        with session_scope() as db:
            job, created = enqueue_av_render(db, _plan_for(story, index))
            job_ids.append(job.id)
            assert created is True
    worker()
    with session_scope() as db:
        jobs = {j.id: j for j in db.scalars(select(Job).where(Job.id.in_(job_ids))).all()}
        assert all(jobs[jid].status == "DONE" for jid in job_ids), \
            {jid: jobs[jid].error for jid in job_ids if jobs[jid].status != "DONE"}

    # T805/T807: revisión y exportación individual por noticia.
    for story in imported:
        project_id = f"proj-lote-{story['story_id']}"
        with session_scope() as db:
            row = db.scalars(
                select(RenderOutput).where(RenderOutput.project_id == project_id)
            ).first()
            assert row is not None, f"falta el render de {project_id}"
            assert row.scene_count == 2
        download = demo_client.get("/api/v1/av/renders", params={"project_id": project_id})
        assert download.status_code == 200 and download.json()["total"] >= 1

    # T810: coste 0 € registrado por cada trabajo del lote.
    from neuralnews.models import UsageEvent
    with session_scope() as db:
        for jid in job_ids:
            usage = db.scalars(select(UsageEvent).where(UsageEvent.job_id == jid)).all()
            assert usage and all(u.cost_estimate == 0.0 for u in usage)


def test_dedupe_y_reanudacion_solo_de_lo_fallido(demo_client, worker, app_env):
    # T804: reintentar el mismo plan no duplica trabajo ni artefacto.
    stories = _create_approved_stories(demo_client, worker, 2)
    detail = demo_client.get(f"/api/v1/stories/{stories[0]}").json()
    plan = {
        "projectId": "proj-reintento",
        "storyRef": {"storyId": str(stories[0]), "title": detail["title"], "revision": None},
        "profileId": "neuralnews-canon-v1",
        "profileVersion": "1.0.0",
        "outputFormat": "9:16",
        "glitch": False,
        "scenes": [
            {
                "sceneIndex": 1, "sceneType": "cierre",
                "scriptSnippet": "Cierre único de prueba.",
                "imagePrompt": "s", "framing": "pecho", "movement": "chest_punch_zoom",
                "transition": "corte_directo", "estDurationSeconds": 1.5, "referenceIds": [],
            }
        ],
        "warnings": [],
    }
    with session_scope() as db:
        job1, created1 = enqueue_av_render(db, plan)
        job2, created2 = enqueue_av_render(db, plan)
        assert created1 is True and created2 is False and job1.id == job2.id
    worker()
    with session_scope() as db:
        assert db.get(Job, job1.id).status == "DONE"
        rows = db.scalars(select(RenderOutput).where(RenderOutput.project_id == "proj-reintento")).all()
        assert len(rows) == 1

    # T806: un plan inválido falla definitivamente; sólo él se vuelve a enviar corregido.
    bad_plan = dict(plan, projectId="proj-reintento-roto", scenes=[dict(plan["scenes"][0], scriptSnippet = "   ")])
    with session_scope() as db:
        bad_job, _ = enqueue_av_render(db, bad_plan)
        bad_id = bad_job.id
    worker()
    with session_scope() as db:
        assert db.get(Job, bad_id).status == "FAILED"
        # el trabajo bueno no se re-ejecuta ni cambia de estado
        assert db.get(Job, job1.id).status == "DONE"
    fixed_plan = dict(bad_plan, scenes=[dict(bad_plan["scenes"][0], scriptSnippet="Cierre corregido.")])
    with session_scope() as db:
        fixed_job, created = enqueue_av_render(db, fixed_plan)
        assert created is True
        fixed_id = fixed_job.id
    worker()
    with session_scope() as db:
        assert db.get(Job, fixed_id).status == "DONE"
        assert db.get(Job, job1.id).status == "DONE", "el trabajo bueno no debía reejecutarse"


def test_techo_de_presupuesto_en_lote_es_por_trabajo(demo_client, worker, app_env):
    # T803: cada trabajo del lote lleva su propio techo; fallar uno no afecta al resto.
    stories = _create_approved_stories(demo_client, worker, 2)
    plans = []
    for n, story_id in enumerate(stories):
        detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
        plans.append({
            "projectId": f"proj-techo-{n}",
            "storyRef": {"storyId": str(story_id), "title": detail["title"], "revision": None},
            "profileId": "neuralnews-canon-v1", "profileVersion": "1.0.0",
            "outputFormat": "9:16", "glitch": False,
            "scenes": [{
                "sceneIndex": 1, "sceneType": "cierre",
                "scriptSnippet": "Cierre con techo de coste.",
                "imagePrompt": "s", "framing": "pecho", "movement": "chest_punch_zoom",
                "transition": "corte_directo", "estDurationSeconds": 1.5, "referenceIds": [],
            }],
            "warnings": [],
        })
    ids = []
    with session_scope() as db:
        job1, _ = enqueue_av_render(db, plans[0])  # sin techo: simulated 0 € pasa
        ids.append(job1.id)
        job2, _ = enqueue_av_render(db, plans[1], max_cost_eur=-1.0)
        ids.append(job2.id)
    worker()
    with session_scope() as db:
        statuses = {jid: db.get(Job, jid).status for jid in ids}
    assert statuses[ids[0]] == "DONE"
    assert statuses[ids[1]] == "FAILED"
