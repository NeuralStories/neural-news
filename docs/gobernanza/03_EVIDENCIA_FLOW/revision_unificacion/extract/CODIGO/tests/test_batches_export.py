"""Etapa 4 — lotes de 5/10 y exportación del paquete editorial (ZIP/MD/JSON)."""
from __future__ import annotations

import io
import json
import zipfile

CORTEXA = (
    "Cortexa Labs ha anunciado Radar, su modelo multimodal con un 12% más de acierto en razonamiento "
    "visual según la ficha técnica; lista de espera para demo web."
)


def _create_stories(demo_client, worker, count: int) -> list[int]:
    ids = []
    for i in range(count):
        text = (
            f"Noticia de prueba independiente número {i}: la empresa ficticia Acme Instruments ha "
            f"presentado hoy el dispositivo X{i} con mejoras documentadas y disponible en su web de demostración."
        )
        payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
        worker()
        detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
        assert detail["stories"], f"la fuente {i} no ha producido candidatos"
        ids.append(detail["stories"][0]["id"])
    return ids


def _approve(demo_client, worker, story_id: int) -> None:
    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    version_id = detail["script_versions"][-1]["id"]
    response = demo_client.post(f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version_id})
    assert response.status_code == 200, response.text


def test_batch_wrong_size_rejected(demo_client):
    response = demo_client.post(
        "/api/v1/batches", json={"name": "malo", "target_size": 7, "story_ids": [1, 2, 3]}
    )
    assert response.status_code in (400, 422)  # 422 = validación de esquema (sólo se admite 5 o 10)


def test_batch_of_ten_with_pending_approval_exports_with_flags(demo_client, worker):
    story_ids = _create_stories(demo_client, worker, 10)
    # Aprobamos 8; dejamos 2 pendientes deliberadamente.
    for story_id in story_ids[:8]:
        _approve(demo_client, worker, story_id)

    created = demo_client.post(
        "/api/v1/batches",
        json={"name": "Lote de prueba 10", "target_size": 10, "story_ids": story_ids},
    )
    assert created.status_code == 200, created.text
    batch_id = created.json()["id"]

    overview = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert overview["ready_count"] == 8
    assert overview["pending_count"] == 2
    pending = [s for s in overview["stories"] if not s["approved"]]
    assert all("aprobación" in (s["pending_reason"] or "") for s in pending)

    export = demo_client.post(f"/api/v1/batches/{batch_id}/export")
    assert export.status_code == 200
    worker()
    job = demo_client.get(f"/api/v1/jobs/{export.json()['job_id']}").json()
    assert job["status"] == "DONE", job

    download = demo_client.get(f"/api/v1/batches/{batch_id}/package")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    sha = download.headers["x-package-sha256"]

    with zipfile.ZipFile(io.BytesIO(download.content)) as zf:
        names = zf.namelist()
        assert "lote/manifiesto.json" in names
        assert "lote/guiones.md" in names
        manifest = json.loads(zf.read("lote/manifiesto.json"))
        markdown = zf.read("lote/guiones.md").decode("utf-8")
        per_story = [n for n in names if n.startswith("lote/guiones/")]
        # Sólo las historias CON guion generan fichero (las 2 pendientes aún no tienen borrador).
        assert len(per_story) == 8

    assert manifest["approved_count"] == 8
    assert manifest["pending_count"] == 2
    assert manifest["batch"]["target_size"] == 10
    for story in manifest["stories"]:
        script = story["script"]
        if script is None:
            # Historia pendiente sin borrador: debe figurar como no aprobada.
            assert story["status_label"] != "Aprobada"
            continue
        assert script["content_hash"]
        if story["approval"] and story["approval"]["status"] == "ACTIVE":
            assert script["approved"] is True
        else:
            assert script["approved"] is False, "un guion sin aprobación no puede figurar como aprobado"
    # El Markdown marca claramente las pendientes.
    assert "PENDIENTE DE APROBACIÓN" in markdown
    assert markdown.count("(aprobada, lista para locución)") == 8
    assert len(download.content) > 1000


def test_batch_of_five_all_approved(demo_client, worker):
    story_ids = _create_stories(demo_client, worker, 5)
    for story_id in story_ids:
        _approve(demo_client, worker, story_id)
    created = demo_client.post(
        "/api/v1/batches",
        json={"name": "Lote de prueba 5", "target_size": 5, "story_ids": story_ids},
    )
    assert created.status_code == 200
    batch_id = created.json()["id"]
    overview = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert overview["ready_count"] == 5 and overview["pending_count"] == 0

    demo_client.post(f"/api/v1/batches/{batch_id}/export")
    worker()
    download = demo_client.get(f"/api/v1/batches/{batch_id}/package")
    assert download.status_code == 200
    manifest = json.loads(
        zipfile.ZipFile(io.BytesIO(download.content)).read("lote/manifiesto.json")
    )
    assert manifest["approved_count"] == 5
    # Cada historia del lote debe incluir storyboard y prompts de imagen preliminares.
    for story in manifest["stories"]:
        assert story["storyboard"]["scenes"], "falta storyboard"
        assert all(scene["image_prompt"] for scene in story["storyboard"]["scenes"])
        assert story["visual_note"].startswith("Prompts preliminares")
        assert isinstance(story["claims"], list), "el paquete debe incluir la trazabilidad de afirmaciones"


def test_export_package_sha256_is_recorded(demo_client, worker):
    story_ids = _create_stories(demo_client, worker, 5)
    created = demo_client.post(
        "/api/v1/batches", json={"name": "Lote hash", "target_size": 5, "story_ids": story_ids}
    )
    batch_id = created.json()["id"]
    demo_client.post(f"/api/v1/batches/{batch_id}/export")
    worker()
    overview = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert overview["packages"], "debe existir un paquete registrado"
    pkg = overview["packages"][0]
    assert len(pkg["sha256"]) == 64
    assert pkg["state"] == "EXPORTED"
