"""Etapa 1 — base funcional: auth, alta de fuentes, deduplicación e idempotencia."""
from __future__ import annotations

from sqlalchemy import select

VIDEO_ID = "dQw4w9WgXcQ"


def test_health_is_public(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["demo_mode"] is True


def test_sources_require_session(client):
    assert client.get("/api/v1/sources").status_code == 401
    assert client.post("/api/v1/sources", json={"text": "hola"}).status_code == 401


def test_demo_login_marks_session(client):
    response = client.post("/api/v1/auth/demo")
    assert response.status_code == 200
    me = client.get("/api/v1/auth/me").json()
    assert me["is_demo"] is True and me["demo_mode"] is True


def test_login_with_password(app_env, client):
    client.post("/api/v1/auth/demo")
    client.post("/api/v1/auth/logout")
    response = client.post(
        "/api/v1/auth/login", json={"username": "editor", "password": "test-password"}
    )
    assert response.status_code == 200
    me = client.get("/api/v1/auth/me").json()
    assert me["is_demo"] is False


def test_manual_text_source_created_once(demo_client):
    text = "Texto de prueba para la primera fuente manual."
    first = demo_client.post("/api/v1/sources", json={"text": text}).json()
    assert first["created"] is True
    second = demo_client.post("/api/v1/sources", json={"text": text}).json()
    assert second["created"] is False
    assert second["source"]["id"] == first["source"]["id"]
    assert "registrad" in second["message"]


def test_youtube_url_normalization_and_dedupe(demo_client):
    urls = [
        f"https://www.youtube.com/watch?v={VIDEO_ID}&t=30s",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
    ]
    ids = []
    for url in urls:
        payload = demo_client.post("/api/v1/sources", json={"url": url}).json()
        ids.append(payload["source"]["id"])
    assert ids[0] == ids[1] == ids[2]
    assert ids[0] is not None
    detail = demo_client.get(f"/api/v1/sources/{ids[0]}").json()
    assert detail["provider"] == "youtube"
    assert detail["canonical_url"] == f"https://www.youtube.com/watch?v={VIDEO_ID}"
    assert detail["external_id"] == VIDEO_ID


def test_idempotency_key_reuses_job(demo_client):
    headers = {"Idempotency-Key": "clave-estable-1"}
    first = demo_client.post("/api/v1/sources", json={"text": "fuente idempotente"}, headers=headers).json()
    second = demo_client.post("/api/v1/sources", json={"text": "fuente idempotente"}, headers=headers).json()
    assert first["job_id"] == second["job_id"]


def test_process_twice_does_not_duplicate_job(demo_client):
    payload = demo_client.post("/api/v1/sources", json={"text": "fuente para reprocesar"}).json()
    source_id = payload["source"]["id"]
    # La creación ya encoló el trabajo; reprocesar sin cambios reutiliza el mismo trabajo.
    first = demo_client.post(f"/api/v1/sources/{source_id}/process", json={}).json()
    second = demo_client.post(f"/api/v1/sources/{source_id}/process", json={}).json()
    assert first["job_id"] == payload["job_id"] == second["job_id"]
    assert second["created"] is False


def test_invalid_url_rejected(demo_client):
    response = demo_client.post("/api/v1/sources", json={"url": "ftp://ejemplo.com/video"})
    assert response.status_code == 400
    assert "URL" in response.json()["detail"]


def test_empty_input_rejected(demo_client):
    response = demo_client.post("/api/v1/sources", json={})
    assert response.status_code == 400
