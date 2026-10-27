"""Configuración común de pruebas: base de datos temporal, modo demo y almacenamiento aislado."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Variables de entorno ANTES de importar neuralnews (Settings se cachea al importar).
_TMPDIR = Path(tempfile.mkdtemp(prefix="neuralnews-tests-"))
os.environ["NEURAL_DEMO_MODE"] = "true"
os.environ["NEURAL_DATABASE_URL"] = "sqlite:///" + (_TMPDIR / "bootstrap.db").as_posix()
os.environ["NEURAL_ADMIN_PASSWORD"] = "test-password"
os.environ["NEURAL_STORAGE_DIR_UNUSED"] = "1"  # el storage real se redirige por fixture

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def app_env(monkeypatch):
    """Base de datos nueva por prueba + almacenamiento aislado + settings controlables."""
    import neuralnews.config as config
    import neuralnews.db as db_mod
    import neuralnews.services.batches as batches_mod
    from neuralnews.models import Base

    db_path = _TMPDIR / f"test-{os.urandom(4).hex()}.db"
    engine = db_mod.make_engine("sqlite:///" + db_path.as_posix())
    Base.metadata.create_all(engine)
    db_mod.set_engine(engine)

    storage = _TMPDIR / f"storage-{os.urandom(4).hex()}"
    storage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "STORAGE_DIR", storage)
    monkeypatch.setattr(batches_mod, "STORAGE_DIR", storage)

    settings = config.get_settings()
    snapshot = {
        "demo_mode": settings.demo_mode,
        "paid_services_enabled": settings.paid_services_enabled,
        "budget_daily_eur": settings.budget_daily_eur,
        "allowed_hosts": list(settings.allowed_hosts),
        "admin_password": settings.admin_password,
    }
    yield {"settings": settings, "storage": storage, "engine": engine, "db_path": db_path}
    for key, value in snapshot.items():
        setattr(settings, key, value)
    engine.dispose()


@pytest.fixture()
def client(app_env):
    from neuralnews.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture()
def demo_client(client):
    """Cliente con sesión de demostración iniciada."""
    response = client.post("/api/v1/auth/demo")
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def worker():
    """Ejecuta la cola hasta vaciarla (máx. 30 ciclos)."""
    from neuralnews.worker import tick

    def drain(max_cycles: int = 30) -> int:
        ran = 0
        for _ in range(max_cycles):
            try:
                if tick() == 0:
                    break
                ran += 1
            except Exception:
                ran += 1
                continue
        return ran

    return drain
