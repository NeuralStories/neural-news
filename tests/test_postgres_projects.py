"""NN-107 F1 — Prueba real contra PostgreSQL (gate de la fase).

Se ejecuta solo cuando existe la variable `NEURAL_TEST_POSTGRES` con una URL
SQLAlchemy, p. ej.:

    NEURAL_TEST_POSTGRES="postgresql+psycopg://neural:neural-local@localhost:5432/neuralnews" \
        python -m pytest tests/test_postgres_projects.py -q

El repositorio ya define ese servicio en `infra/docker-compose.yml`
(`docker compose up -d db`). Con SQLAlchemy 2.0 el mismo esquema y el mismo
código de aplicación sirven para SQLite y PostgreSQL; esta prueba lo demuestra
sobre PostgreSQL real, incluido el ciclo crear → modificar → reiniciar →
recuperar sin pérdida.
"""
from __future__ import annotations

import os

import pytest

PG_URL = os.environ.get("NEURAL_TEST_POSTGRES")

pytestmark = pytest.mark.skipif(
    not PG_URL, reason="requiere NEURAL_TEST_POSTGRES (p. ej. docker compose up -d db)"
)


@pytest.fixture()
def pg_env():
    import neuralnews.config as config
    import neuralnews.db as db_mod
    import neuralnews.services.batches as batches_mod
    from neuralnews.models import Base

    engine = db_mod.make_engine(PG_URL)
    Base.metadata.create_all(engine)
    db_mod.set_engine(engine)

    storage = config.STORAGE_DIR / "pg-test-media"
    storage.mkdir(parents=True, exist_ok=True)
    batches_mod.STORAGE_DIR = storage
    config.STORAGE_DIR = storage

    yield {"engine": engine, "storage": storage}
    engine.dispose()


def test_postgres_project_lifecycle_and_restart(pg_env):
    from fastapi.testclient import TestClient
    import neuralnews.db as db_mod
    from neuralnews.main import app
    from neuralnews.models import Base

    with TestClient(app) as client:
        client.post("/api/v1/auth/demo")
        project = client.post(
            "/api/v1/projects",
            json={"name": "PG — ciclo completo", "ratio": "16:9", "target_duration_s": 45},
        ).json()
        pid = project["id"]
        assert project["ratio"] == "16:9"

        first = client.put(
            f"/api/v1/projects/{pid}/studio/guion",
            json={"payload": {"texto": "locución continua"}, "expected_revision": 0},
        )
        assert first.status_code == 200, first.text

        stale = client.put(
            f"/api/v1/projects/{pid}/studio/guion",
            json={"payload": {}, "expected_revision": 0},
        )
        assert stale.status_code == 409

        take = client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()
        mp4 = b"pg-mp4-content"
        upload = client.post(
            f"/api/v1/projects/{pid}/takes/{take['id']}/media",
            files={"file": ("toma.mp4", mp4, "video/mp4")},
        )
        assert upload.status_code == 200, upload.text
        sha = upload.json()["media"]["sha256"]

    # Reinicio real: motor nuevo sobre la misma base PostgreSQL
    pg_env["engine"].dispose()
    engine2 = db_mod.make_engine(PG_URL)
    db_mod.set_engine(engine2)
    try:
        with TestClient(app) as client2:
            client2.post("/api/v1/auth/demo")
            restored = client2.get(f"/api/v1/projects/{pid}").json()
            assert restored["name"] == "PG — ciclo completo"
            assert restored["ratio"] == "16:9"
            assert restored["steps"]["guion"] == {
                "revision": 1,
                "payload": {"texto": "locución continua"},
            }
            assert restored["takes"][0]["status"] == "IMPORTADA"
            assert restored["takes"][0]["imported_media"]["sha256"] == sha
    finally:
        engine2.dispose()
