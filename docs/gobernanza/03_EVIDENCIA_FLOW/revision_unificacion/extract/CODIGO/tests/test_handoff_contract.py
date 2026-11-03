"""Contrato `production_handoff.v1`: esquema, productor editorial y consumidor independiente.

Cubre: validación del esquema (fixtures válidos e inválidos), productor sobre datos
editoriales reales (aprobado / no aprobado / revisión desfasada / sin resumen),
consumidor independiente (integridad de hash, duplicados) e integración editorial → consumidor.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / "packages" / "contracts"
FIXTURES = REPO_ROOT / "fixtures" / "handoff"
sys.path.insert(0, str(CONTRACTS_DIR / "consumer"))

from neural_handoff_consumer import (  # noqa: E402
    DuplicateHandoffError,
    HandoffRegistry,
    HandoffValidationError,
    import_handoff,
    load_schema,
)
from neuralnews.db import session_scope  # noqa: E402
from neuralnews.models import Story  # noqa: E402
from neuralnews.services.handoff import (  # noqa: E402
    HandoffError,
    emit_batch_handoff,
    emit_single_handoff,
)

SCHEMA = load_schema()


def _schema_errors(document) -> list[str]:
    validator = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
    return [e.message for e in validator.iter_errors(document)]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _create_story(demo_client, worker, index: int = 0) -> int:
    # Texto único por noticia: el extractor demo fusiona candidatos por tema.
    text = (
        f"Noticia de prueba del contrato número {index}: la empresa ficticia Acme Instruments ha "
        f"presentado hoy el dispositivo C{index} con mejoras documentadas en su web de demostración."
    )
    payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
    assert detail["stories"], "la fuente no ha producido candidato"
    return detail["stories"][0]["id"]


def _approve(demo_client, worker, story_id: int) -> dict:
    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    version_id = detail["script_versions"][-1]["id"]
    response = demo_client.post(
        f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version_id}
    )
    assert response.status_code == 200, response.text
    return detail


def _draft_only(demo_client, worker, story_id: int) -> None:
    """Genera guion y resumen sin aprobar: deja la noticia pendiente de aprobación."""
    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()


# ---------------------------------------------------------------- esquema (T101/T102/T116)

def test_schema_accepts_single_fixture():
    assert _schema_errors(_load_fixture("single_valid.json")) == []


def test_schema_accepts_batch5_fixture():
    assert _schema_errors(_load_fixture("batch5_valid.json")) == []


def test_schema_rejects_batch_of_three():
    errors = _schema_errors(_load_fixture("invalid_batch3.json"))
    assert any("5" in e or "10" in e for e in errors)


def test_schema_rejects_single_with_two_stories():
    doc = _load_fixture("single_valid.json")
    doc["stories"] = [doc["stories"][0], dict(doc["stories"][0], story_id="otra")]
    errors = _schema_errors(doc)
    assert any("maxItems" in e or "1" in e for e in errors)


def test_schema_rejects_unapproved_status():
    errors = _schema_errors(_load_fixture("invalid_not_approved.json"))
    assert any("approved" in e for e in errors)


def test_schema_rejects_source_without_any_identifier():
    errors = _schema_errors(_load_fixture("invalid_source_without_identifier.json"))
    assert errors, "una fuente sin url, external_id ni título debe rechazarse"


# ---------------------------------------------------------------- consumidor (T204-T206)

def test_consumer_accepts_valid_fixture(tmp_path):
    registry = HandoffRegistry(tmp_path / "registro.json")
    stories = import_handoff(_load_fixture("single_valid.json"), registry)
    assert len(stories) == 1
    imported = stories[0]
    assert imported["script"]  # el guion llega íntegro
    assert imported["content_hash"] == hashlib.sha256(imported["script"].encode("utf-8")).hexdigest()
    assert imported["approval"]["status"] == "approved"
    assert registry.entries and (tmp_path / "registro.json").exists()


@pytest.mark.parametrize(
    "name",
    ["invalid_not_approved.json", "invalid_batch3.json", "invalid_source_without_identifier.json"],
)
def test_consumer_rejects_invalid_fixtures(tmp_path, name):
    with pytest.raises(HandoffValidationError):
        import_handoff(_load_fixture(name), HandoffRegistry(tmp_path / "r.json"))


def test_consumer_rejects_tampered_script_even_if_schema_valid(tmp_path):
    doc = _load_fixture("schema_valid_tampered_hash.json")
    assert _schema_errors(doc) == []  # el esquema por sí solo no detecta la manipulación
    with pytest.raises(HandoffValidationError) as excinfo:
        import_handoff(doc, HandoffRegistry(tmp_path / "r.json"))
    assert "hash" in str(excinfo.value)


def test_consumer_rejects_duplicate_handoff(tmp_path):
    registry = HandoffRegistry(tmp_path / "r.json")
    doc = _load_fixture("single_valid.json")
    import_handoff(doc, registry)
    with pytest.raises(DuplicateHandoffError):
        import_handoff(doc, registry)


def test_consumer_rejects_same_story_revision_in_other_handoff(tmp_path):
    registry = HandoffRegistry(tmp_path / "r.json")
    first = _load_fixture("single_valid.json")
    second = json.loads(json.dumps(first, ensure_ascii=False))
    second["handoff_id"] = first["handoff_id"] + "-variante"
    second["created_at"] = "2026-10-28T12:00:00+00:00"
    import_handoff(first, registry)
    with pytest.raises(DuplicateHandoffError):
        import_handoff(second, registry)


# ---------------------------------------------------------------- productor (T201-T203)

def test_endpoint_emits_valid_handoff_for_approved_story(demo_client, worker):
    story_id = _create_story(demo_client, worker, index=1)
    _approve(demo_client, worker, story_id)

    response = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    assert response.status_code == 200, response.text
    document = response.json()
    assert _schema_errors(document) == []

    story = document["stories"][0]
    assert story["story_id"] == str(story_id)
    assert story["revision"] >= 1
    assert story["editorial_approval"]["status"] == "approved"
    assert story["content_hash"] == hashlib.sha256(story["approved_script"].encode("utf-8")).hexdigest()
    assert story["sources"], "la noticia traspasada debe conservar sus fuentes"
    manual = [s for s in story["sources"] if s["provider"] == "manual"]
    assert manual and manual[0]["url"] is None and manual[0]["title"]
    assert all(s["accessed_at"] for s in story["sources"])


def test_endpoint_emission_is_idempotent(demo_client, worker):
    story_id = _create_story(demo_client, worker, index=2)
    _approve(demo_client, worker, story_id)
    first = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    second = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    assert first.json()["handoff_id"] == second.json()["handoff_id"]
    assert first.json()["created_at"] == second.json()["created_at"]


def test_endpoint_blocks_story_without_approval(demo_client, worker):
    story_id = _create_story(demo_client, worker, index=3)
    _draft_only(demo_client, worker, story_id)  # guion listo, aprobación pendiente
    response = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    assert response.status_code == 409
    assert "aprobación" in response.json()["detail"]


def test_endpoint_blocks_when_approved_version_is_superseded(demo_client, worker):
    story_id = _create_story(demo_client, worker, index=4)
    _approve(demo_client, worker, story_id)
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    response = demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": detail["script_versions"][-1]["content"] + "\n\nPárrafo añadido tras aprobar.",
              "expected_version": detail["script_versions"][-1]["version"]},
    )
    assert response.status_code == 200, response.text
    handoff = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    assert handoff.status_code == 409
    # La edición anuló la aprobación: el traspaso se bloquea y lo explica.
    assert "aprobación" in handoff.json()["detail"]


def test_endpoint_blocks_story_without_summary(demo_client, worker):
    story_id = _create_story(demo_client, worker, index=5)
    _approve(demo_client, worker, story_id)
    with session_scope() as db:
        story = db.get(Story, story_id)
        story.summary = None
    response = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    assert response.status_code == 409
    assert "resumen" in response.json()["detail"]


def test_handoff_id_changes_when_script_content_changes(demo_client, worker):
    story_id = _create_story(demo_client, worker, index=6)
    _approve(demo_client, worker, story_id)
    first = demo_client.get(f"/api/v1/stories/{story_id}/handoff").json()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": detail["script_versions"][-1]["content"] + "\n\nNuevo cierre.",
              "expected_version": detail["script_versions"][-1]["version"]},
    )
    _approve(demo_client, worker, story_id)
    second = demo_client.get(f"/api/v1/stories/{story_id}/handoff").json()
    assert second["handoff_id"] != first["handoff_id"]
    assert second["stories"][0]["revision"] > first["stories"][0]["revision"]


# ---------------------------------------------------------------- lote (T201 modo batch)

def test_batch_handoff_validates_and_rejects_partial_batches(demo_client, worker, app_env):
    from neuralnews.config import STORAGE_DIR

    story_ids = [_create_story(demo_client, worker, index=10 + i) for i in range(5)]
    for story_id in story_ids[:4]:  # la quinta queda con guion pero sin aprobar
        _approve(demo_client, worker, story_id)
    _draft_only(demo_client, worker, story_ids[4])
    created = demo_client.post(
        "/api/v1/batches",
        json={"name": "Lote contrato", "target_size": 5, "story_ids": story_ids},
    )
    assert created.status_code == 200, created.text
    batch_id = created.json()["id"]

    with pytest.raises(HandoffError) as excinfo:
        with session_scope() as db:
            emit_batch_handoff(db, batch_id, persist=False)
    assert "aprobación" in str(excinfo.value)
    assert not (STORAGE_DIR / "handoffs").exists(), "un lote con bloqueos no debe emitir nada"

    _approve(demo_client, worker, story_ids[4])
    with session_scope() as db:
        document = emit_batch_handoff(db, batch_id)
    assert _schema_errors(document) == []
    assert document["mode"] == "batch"
    assert len(document["stories"]) == 5


# ---------------------------------------------------------------- integración editorial → consumidor (T209)

def test_full_editorial_to_consumer_roundtrip(demo_client, worker, tmp_path):
    story_id = _create_story(demo_client, worker, index=20)
    _approve(demo_client, worker, story_id)
    document = demo_client.get(f"/api/v1/stories/{story_id}/handoff").json()

    registry = HandoffRegistry(tmp_path / "studio-registro.json")
    imported = import_handoff(document, registry)
    assert imported[0]["story_id"] == str(story_id)
    assert imported[0]["title"] and imported[0]["summary"]
    assert imported[0]["script"]
    assert all("accessed_at" in s for s in imported[0]["sources"])
    # Reimportar el mismo traspaso se rechaza: sin duplicados.
    with pytest.raises(DuplicateHandoffError):
        import_handoff(document, registry)
