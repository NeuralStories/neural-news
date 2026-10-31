"""NN-107 F1 — Proyectos de producción, Studio con CAS y biblioteca de medios.

Entrega obligatoria de la fase: crear un proyecto, modificarlo, «reiniciar» la
aplicación (motor nuevo sobre la misma base) y recuperarlo sin pérdida.
"""
from __future__ import annotations

import hashlib

import pytest

DEMO_NOTICIA = (
    "Cortexa Labs presentó hoy Radar, un modelo de razonamiento en tiempo real. "
    "La empresa afirma que reduce la latencia un 40 por ciento. Dos laboratorios "
    "independientes replicaron la prueba con resultados similares."
)


def _story_with_script(demo_client, worker) -> int:
    payload = demo_client.post("/api/v1/sources", json={"text": DEMO_NOTICIA}).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
    return detail["stories"][0]["id"]


# ------------------------------------------------------------------ creación


def test_create_project_fixes_ratio_at_creation(demo_client):
    """R-BUG-2 (base): el ratio se fija en la creación y no existe ruta que lo muta."""
    response = demo_client.post(
        "/api/v1/projects",
        json={"name": "Radar — Short", "ratio": "16:9", "target_duration_s": 45},
    )
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["ratio"] == "16:9"
    assert project["format_profile"]["ratio"] == "16:9"
    assert project["status"] == "DRAFT"
    # el ratio inválido se rechaza
    bad = demo_client.post("/api/v1/projects", json={"name": "x", "ratio": "4:3"})
    assert bad.status_code == 422


def test_link_story_activates_it_immediately(demo_client, worker):
    """R-BUG-1: vincular/importar una noticia la deja activa sin pasos extra."""
    story_id = _story_with_script(demo_client, worker)
    created = demo_client.post("/api/v1/projects", json={"name": "P1"}).json()
    assert created["story_id"] is None

    linked = demo_client.post(f"/api/v1/projects/{created['id']}/link-story", json={"story_id": story_id})
    assert linked.status_code == 200, linked.text
    assert linked.json()["story_id"] == story_id
    assert linked.json()["story"]["id"] == story_id

    # Y lo mismo al guardar el paso Noticias con story_id en el payload:
    created2 = demo_client.post("/api/v1/projects", json={"name": "P2"}).json()
    saved = demo_client.put(
        f"/api/v1/projects/{created2['id']}/studio/noticias",
        json={"payload": {"story_id": story_id}, "expected_revision": 0},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["story_id"] == story_id


# ------------------------------------------------------------------ CAS


def test_step_save_requires_current_revision_and_gives_409_when_stale(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "CAS"}).json()
    pid = project["id"]

    ok = demo_client.put(
        f"/api/v1/projects/{pid}/studio/personaje",
        json={"payload": {"character": "maxDotAi"}, "expected_revision": 0},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["revision"] == 1

    stale = demo_client.put(
        f"/api/v1/projects/{pid}/studio/personaje",
        json={"payload": {"character": "otro"}, "expected_revision": 0},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["current_revision"] == 1

    follow = demo_client.put(
        f"/api/v1/projects/{pid}/studio/personaje",
        json={"payload": {"character": "maxDotAi", "v": 2}, "expected_revision": 1},
    )
    assert follow.status_code == 200
    assert follow.json()["revision"] == 2

    history = demo_client.get(f"/api/v1/projects/{pid}/studio/personaje/history").json()
    assert history["current_revision"] == 2
    assert [item["revision"] for item in history["items"]] == [2, 1]


def test_unknown_step_returns_404(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "x"}).json()
    response = demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/navegacion",
        json={"payload": {}, "expected_revision": 0},
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ persistencia (entrega obligatoria)


def test_project_survives_application_restart(app_env):
    """Crear → modificar → cerrar la aplicación → reiniciar → recuperar sin pérdida."""
    from fastapi.testclient import TestClient
    import neuralnews.db as db_mod
    from neuralnews.main import app
    from neuralnews.models import Base

    engine = app_env["engine"]
    db_path = app_env["db_path"]
    db_mod.set_engine(engine)

    with TestClient(app) as client:
        client.post("/api/v1/auth/demo")
        project = client.post(
            "/api/v1/projects", json={"name": "Persistencia", "ratio": "9:16"}
        ).json()
        pid = project["id"]
        assert client.put(
            f"/api/v1/projects/{pid}/studio/guion",
            json={"payload": {"texto": "locución continua"}, "expected_revision": 0},
        ).status_code == 200
        take = client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()
        mp4 = b"fake-mp4-bytes-for-persistence-test"
        upload = client.post(
            f"/api/v1/projects/{pid}/takes/{take['id']}/media",
            files={"file": ("toma1.mp4", mp4, "video/mp4")},
        )
        assert upload.status_code == 200, upload.text
        asset_sha = upload.json()["media"]["sha256"]

    # --- reinicio: motor nuevo, misma base ---
    engine.dispose()
    engine2 = db_mod.make_engine("sqlite:///" + db_path.as_posix())
    Base.metadata.create_all(engine2)
    db_mod.set_engine(engine2)
    try:
        with TestClient(app) as client2:
            client2.post("/api/v1/auth/demo")
            restored = client2.get(f"/api/v1/projects/{pid}").json()
            assert restored["name"] == "Persistencia"
            assert restored["steps"]["guion"] == {"revision": 1, "payload": {"texto": "locución continua"}}
            assert restored["takes"][0]["status"] == "IMPORTADA"
            assert restored["takes"][0]["imported_media"]["sha256"] == asset_sha
    finally:
        engine2.dispose()
        db_mod.set_engine(engine)


# ------------------------------------------------------------------ medios


def test_take_media_upload_is_idempotent_and_never_autoapproved(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "Medios"}).json()
    pid = project["id"]
    take = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()

    payload = b"\x00\x01\x02\x03fake-mp4-content"
    first = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/media",
        files={"file": ("toma.mp4", payload, "video/mp4")},
    )
    assert first.status_code == 200, first.text
    asset = first.json()["media"]
    assert asset["sha256"] == hashlib.sha256(payload).hexdigest()
    assert asset["license_state"] == "PENDING"  # F-02: nada aprobado por defecto
    assert first.json()["status"] == "IMPORTADA"  # y nunca APROBADA automáticamente

    # La misma subida no duplica el asset
    again = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/media",
        files={"file": ("tota-otra-vez.mp4", payload, "video/mp4")},
    )
    assert again.status_code == 200
    assert again.json()["media"]["id"] == asset["id"]

    listing = demo_client.get("/api/v1/media").json()
    assert listing["total"] == 1

    # Tipo no permitido se rechaza
    bad = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/media",
        files={"file": ("script.exe", b"MZ", "application/x-msdownload")},
    )
    assert bad.status_code == 422


def test_prompt_makes_take_prompt_ready_but_approval_needs_video(demo_client):
    """Un prompt listo nunca equivale a un vídeo generado (cap. 13)."""
    project = demo_client.post("/api/v1/projects", json={"name": "Prompts"}).json()
    pid = project["id"]
    take = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()

    premature = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/approval", json={"status": "APROBADA"}
    )
    assert premature.status_code == 409

    prompt = demo_client.post(
        f"/api/v1/projects/{pid}/prompts",
        json={"take_id": take["id"], "prompt_en": "Static CRT studio shot, maxDotAI speaking.",
              "explanation_es": "Plano fijo del plató."},
    )
    assert prompt.status_code == 200, prompt.text
    assert prompt.json()["take_status"] == "PROMPT_LISTO"

    # Sigue sin poder aprobarse: PROMPT_LISTO no es IMPORTADA
    still = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/approval", json={"status": "APROBADA"}
    )
    assert still.status_code == 409

    uploaded = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/media",
        files={"file": ("toma.mp4", b"mp4-bytes", "video/mp4")},
    )
    assert uploaded.status_code == 200
    approved = demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/approval", json={"status": "APROBADA"}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APROBADA"


def test_media_approval_is_explicit_and_human(demo_client):
    asset = demo_client.post(
        "/api/v1/media", files={"file": ("clip.mp4", b"clip-bytes", "video/mp4")}
    ).json()
    assert asset["license_state"] == "PENDING"

    approved = demo_client.post(
        f"/api/v1/media/{asset['id']}/approval", json={"status": "APPROVED", "note": "derechos ok"}
    )
    assert approved.status_code == 200
    assert approved.json()["license_state"] == "APPROVED"


# ------------------------------------------------------------------ beats y shots


def test_beats_and_shots_persist_without_forced_eight_second_cuts(demo_client):
    """F-05: los beats admiten duraciones libres; los shots declaran su tipo."""
    project = demo_client.post("/api/v1/projects", json={"name": "Guion", "target_duration_s": 45}).json()
    pid = project["id"]
    saved = demo_client.put(
        f"/api/v1/projects/{pid}/beats",
        json={"beats": [
            {"text": "Apertura: presentación del dato.", "est_seconds": 12.5},
            {"text": "Desarrollo con la cifra contrastada.", "est_seconds": 20.0},
            {"text": "Cierre.", "est_seconds": 8.8},
        ]},
    )
    assert saved.status_code == 200, saved.text

    shots = demo_client.put(
        f"/api/v1/projects/{pid}/shots",
        json={"shots": [
            {"shot_kind": "FLOW_MAXDOTAI", "max_duration_s": 8.0, "rationale": "presentador"},
            {"shot_kind": "DATA_GRAPHIC", "max_duration_s": 12.0, "rationale": "cifra exacta"},
        ]},
    )
    assert shots.status_code == 200, shots.text
    assert shots.json()["ratio"] == project["ratio"]  # R-BUG-2: planificar no cambia el ratio

    full = demo_client.get(f"/api/v1/projects/{pid}").json()
    assert [b["est_seconds"] for b in full["beats"]] == [12.5, 20.0, 8.8]
    assert [s["shot_kind"] for s in full["shots"]] == ["FLOW_MAXDOTAI", "DATA_GRAPHIC"]
    assert full["ratio"] == project["ratio"]

    bad_kind = demo_client.put(
        f"/api/v1/projects/{pid}/shots", json={"shots": [{"shot_kind": "MAGIC"}]}
    )
    assert bad_kind.status_code == 422


def test_patch_project_cannot_change_ratio(demo_client):
    """R-BUG-2: el parche de proyecto no expone ratio."""
    project = demo_client.post("/api/v1/projects", json={"name": "Original", "ratio": "16:9"}).json()
    patched = demo_client.put(f"/api/v1/projects/{project['id']}", json={"name": "Nuevo nombre"})
    assert patched.status_code == 200
    assert patched.json()["ratio"] == "16:9"
    assert patched.json()["name"] == "Nuevo nombre"


# ------------------------------------------------------------------ listado y full state


def test_list_and_full_state(demo_client, worker):
    story_id = _story_with_script(demo_client, worker)
    project = demo_client.post(
        "/api/v1/projects", json={"name": "Completo", "story_id": story_id}
    ).json()
    listing = demo_client.get("/api/v1/projects").json()
    assert listing["total"] == 1
    assert listing["items"][0]["story"]["id"] == story_id

    full = demo_client.get(f"/api/v1/projects/{project['id']}").json()
    assert set(full["steps"]) == {
        "noticias", "personaje", "fondo", "guion", "voz", "movimiento", "referencias", "resultado",
    }
    assert all(step["revision"] == 0 for step in full["steps"].values())
