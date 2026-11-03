"""Funciones nuevas: storyboard, detección de duplicados, contrato OpenAPI y consumos."""
from __future__ import annotations

import json
from pathlib import Path

from neuralnews.providers.image_prompt import build_storyboard
from neuralnews.services.dedupe import find_possible_duplicates, title_similarity

CORTEXA = (
    "Cortexa Labs ha anunciado Radar, su modelo multimodal con un 12% más de acierto en razonamiento "
    "visual según la ficha técnica; lista de espera para demo web."
)
ACME = (
    "La empresa ficticia Acme Instruments ha presentado hoy el dispositivo X1 con mejoras documentadas "
    "y disponibilidad inmediata en su web de demostración."
)


def _story_with_script(demo_client, worker, text: str) -> int:
    payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
    return detail["stories"][0]["id"]


# ------------------------------------------------------------------ storyboard
def test_storyboard_endpoint_returns_scenes_and_prompts(demo_client, worker):
    story_id = _story_with_script(demo_client, worker, CORTEXA)
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()

    response = demo_client.get(f"/api/v1/stories/{story_id}/storyboard")
    assert response.status_code == 200, response.text
    board = response.json()
    assert board["scenes"], "debe haber al menos una escena"
    scene = board["scenes"][0]
    assert scene["seconds"] > 0
    assert scene["visual"]
    assert scene["image_prompt"]
    assert "9:16" in scene["image_prompt"], "el prompt debe indicar el formato vertical"
    assert "Prompts preliminares" in board["note"]
    assert "No se han generado imágenes ni vídeo" in board["note"]
    assert board["approved"] is False


def test_storyboard_requires_a_script(demo_client, worker):
    story_id = _story_with_script(demo_client, worker, ACME)
    response = demo_client.get(f"/api/v1/stories/{story_id}/storyboard")
    assert response.status_code == 404
    assert "guion" in response.json()["detail"].lower()


def test_storyboard_marks_approved_script(demo_client, worker):
    story_id = _story_with_script(demo_client, worker, CORTEXA)
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    version_id = detail["script_versions"][-1]["id"]
    demo_client.post(f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version_id})

    board = demo_client.get(f"/api/v1/stories/{story_id}/storyboard").json()
    assert board["approved"] is True
    assert all("guion aprobado" in (s["data_source"] or "") for s in board["scenes"])


def test_build_storyboard_handles_empty_script(demo_client, worker):
    from neuralnews.models import ScriptVersion, Story

    story_id = _story_with_script(demo_client, worker, ACME)
    from neuralnews.db import session_scope

    with session_scope() as db:
        story = db.get(Story, story_id)
        version = ScriptVersion(
            story_id=story.id, version=99, content="   ", target_duration_s=10,
            language="es-ES", author_type="HUMAN", content_hash="x" * 64,
        )
        db.add(version)
        db.flush()
        board = build_storyboard(story, version, None)
    assert board.scenes, "debe devolver al menos una escena de reserva"


# ------------------------------------------------------------------ duplicados
def test_title_similarity_detects_same_topic():
    assert title_similarity("Cortexa Labs presenta Radar", "Cortexa Labs presenta Radar") == 1.0
    assert title_similarity("Cortexa Labs presenta Radar", "Vireo AI levy una ronda") < 0.2


def test_possible_duplicates_are_reported(app_env, demo_client):
    """Dos historias con títulos parecidos deben señalarse (sin fusionar automáticamente)."""
    from neuralnews.db import session_scope
    from neuralnews.models import Story

    with session_scope() as db:
        first = Story(
            topic_key="cortexa-radar-uno",
            title="Cortexa Labs presenta Radar, su modelo multimodal",
            status="CANDIDATE",
        )
        second = Story(
            topic_key="cortexa-radar-dos",
            title="Cortexa Labs presenta Radar, el modelo multimodal",
            status="CANDIDATE",
        )
        third = Story(
            topic_key="otro-tema",
            title="Vireo AI levy una ronda de inversión",
            status="CANDIDATE",
        )
        db.add_all([first, second, third])
        db.flush()
        first_id, second_id, third_id = first.id, second.id, third.id

    detail = demo_client.get(f"/api/v1/stories/{first_id}").json()
    assert detail["possible_duplicates"], "debe avisar de un posible duplicado"
    assert any(d["story_id"] == second_id for d in detail["possible_duplicates"])
    assert not any(d["story_id"] == third_id for d in detail["possible_duplicates"])

    listing = demo_client.get("/api/v1/stories").json()["items"]
    entry = next(s for s in listing if s["id"] == first_id)
    assert entry["possible_duplicates"], "el listado también debe avisar"


def test_stories_with_same_topic_key_are_merged_not_duplicated(demo_client, worker):
    """Dos fuentes del mismo tema producen UNA historia con dos referencias."""
    base = _story_with_script(demo_client, worker, CORTEXA)
    similar = "Cortexa Labs presenta Radar, su modelo multimodal con mejoras en razonamiento visual"
    other = _story_with_script(demo_client, worker, similar)
    assert base == other, "el mismo tema debe fusionarse en una sola historia"

    detail = demo_client.get(f"/api/v1/stories/{base}").json()
    assert len(detail["sources"]) == 2, "deben conservarse las dos referencias"


def test_unrelated_stories_have_no_duplicates(app_env, demo_client):
    from neuralnews.db import session_scope
    from neuralnews.models import Story

    with session_scope() as db:
        first = Story(topic_key="tema-a", title="Cortexa Labs presenta Radar", status="CANDIDATE")
        second = Story(topic_key="tema-b", title="Vireo AI levy una ronda", status="CANDIDATE")
        db.add_all([first, second])
        db.flush()
        first_id, second_id = first.id, second.id

    detail = demo_client.get(f"/api/v1/stories/{first_id}").json()
    assert not any(d["story_id"] == second_id for d in detail["possible_duplicates"])


# ------------------------------------------------------------------ contrato OpenAPI
def test_openapi_contract_contains_required_routes():
    from neuralnews.main import app

    schema = app.openapi()
    paths = schema["paths"]
    required = [
        "/api/v1/sources",
        "/api/v1/sources/{source_id}",
        "/api/v1/sources/{source_id}/process",
        "/api/v1/jobs/{job_id}",
        "/api/v1/stories",
        "/api/v1/stories/{story_id}",
        "/api/v1/stories/{story_id}/research",
        "/api/v1/stories/{story_id}/draft",
        "/api/v1/stories/{story_id}/script",
        "/api/v1/stories/{story_id}/approve",
        "/api/v1/stories/{story_id}/reject",
        "/api/v1/batches",
        "/api/v1/batches/{batch_id}",
        "/api/v1/batches/{batch_id}/export",
        "/api/v1/usage",
    ]
    for route in required:
        assert route in paths, f"falta la ruta {route} en el contrato"


def test_openapi_file_is_exported_and_current():
    contract = Path(__file__).resolve().parents[1] / "packages" / "contracts" / "openapi.json"
    assert contract.exists(), "falta packages/contracts/openapi.json"
    data = json.loads(contract.read_text(encoding="utf-8"))
    assert data["openapi"].startswith("3.")
    assert "/api/v1/stories" in data["paths"]
    assert "/api/v1/stories/{story_id}/storyboard" in data["paths"]


# ------------------------------------------------------------------ consumos
def test_usage_records_demo_calls(demo_client, worker):
    demo_client.post("/api/v1/sources", json={"text": CORTEXA})
    worker()
    usage = demo_client.get("/api/v1/usage").json()
    assert usage["today_calls"] >= 1
    assert "demo_extraction" in usage["by_provider"]
    assert usage["today_spent_eur"] == 0.0, "en demo no hay coste"


def test_reinvestigating_an_approved_story_invalidates_the_approval(demo_client, worker):
    """Reinvestigar una noticia aprobada es válido y anula la aprobación vigente."""
    story_id = _story_with_script(demo_client, worker, CORTEXA)
    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    version_id = detail["script_versions"][-1]["id"]
    demo_client.post(f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version_id})
    assert demo_client.get(f"/api/v1/stories/{story_id}").json()["status"] == "APPROVED"

    demo_client.post(f"/api/v1/stories/{story_id}/research")
    worker()
    despues = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert despues["status"] == "REVIEW_REQUIRED"
    assert despues["active_approval"] is None, "la aprobación debe quedar anulada"


def test_story_list_scales_without_scanning_all_history(app_env, demo_client):
    """El listado no debe recorrer todo el histórico para calcular duplicados."""
    from neuralnews.db import session_scope
    from neuralnews.models import Story
    from neuralnews.services import dedupe

    with session_scope() as db:
        for i in range(5):
            db.add(Story(topic_key=f"k{i}", title=f"Historia número {i} sobre IA", status="CANDIDATE"))
        db.flush()

    original = dedupe.MAX_COMPARISON_SET
    try:
        dedupe.MAX_COMPARISON_SET = 2
        response = demo_client.get("/api/v1/stories?limit=10")
        assert response.status_code == 200
        assert response.json()["total"] >= 5
    finally:
        dedupe.MAX_COMPARISON_SET = original
