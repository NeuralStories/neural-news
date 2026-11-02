"""NN-110 / B23 — Reinvestigar una noticia aprobada no debe fallar.

Antes: `APPROVED → RESEARCHING` no era una transición válida, así que el
trabajo «Investigar» sobre una noticia ya aprobada moría con un
`ValueError` confuso y se **reintentaba tres veces** sin explicar nada.

Ahora: reinvestigar es legítimo (puede haber evidencia nueva) y la aprobación
queda anulada, igual que cuando se edita el guion: hay que volver a aprobarla.
"""
from __future__ import annotations

from neuralnews.db import get_session_factory
from neuralnews.models import Approval, Story
from neuralnews.services import research as research_service
from neuralnews.states import STORY_TRANSITIONS, assert_transition


def test_la_transicion_aprobada_a_investigando_existe():
    """La transición está declarada y es coherente con el resto."""
    assert "RESEARCHING" in STORY_TRANSITIONS["APPROVED"]
    assert_transition("story", "APPROVED", "RESEARCHING")


def test_reinvestigar_una_noticia_aprobada_no_falla(demo_client, worker):
    """El trabajo termina bien y la aprobación queda anulada."""
    # 1) Una noticia con guion aprobado.
    demo_client.post(
        "/api/v1/sources",
        json={"text": "Cortexa Labs ha anunciado Radar y Vireo AI ha levantado 40 millones."},
    )
    worker()
    historias = demo_client.get("/api/v1/stories").json()["items"]
    assert historias
    story_id = historias[0]["id"]

    r = demo_client.post(f"/api/v1/stories/{story_id}/draft")
    assert r.status_code == 200
    worker()
    detalle = demo_client.get(f"/api/v1/stories/{story_id}").json()
    version_id = detalle["script_versions"][-1]["id"]

    r = demo_client.post(f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version_id})
    assert r.status_code == 200, r.text
    detalle = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detalle["status"] == "APPROVED"
    assert detalle["active_approval"] is not None

    # 2) Reinvestigar: no debe fallar, y deja la noticia sin aprobación.
    r = demo_client.post(f"/api/v1/stories/{story_id}/research")
    assert r.status_code == 200, r.text
    worker()

    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    trabajo = next(j for j in jobs if j["type"] == "research_story")
    assert trabajo["status"] == "DONE", trabajo.get("error")

    detalle = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detalle["active_approval"] is None, (
        "reinvestigar una noticia aprobada debe anular su aprobación"
    )

    with get_session_factory()() as db:
        aprobaciones = db.query(Approval).filter(Approval.story_id == story_id).all()
        assert any(a.status == "INVALIDATED" for a in aprobaciones)
        historia = db.get(Story, story_id)
        assert historia is not None
