"""Etapa 4/5 — presupuesto, consumos y E2E del recorrido crítico completo."""
from __future__ import annotations

import io
import json
import zipfile

from neuralnews.services.budget import BudgetExceeded, assert_paid_call_allowed, record_usage


def test_budget_blocks_paid_calls_by_default(app_env, demo_client, db=None):
    from neuralnews.db import session_scope

    with session_scope() as db:
        # Modo demo activo: todo lo de pago está bloqueado.
        try:
            assert_paid_call_allowed(db, "gemini")
            raise AssertionError("debía bloquearse en modo demo")
        except BudgetExceeded as exc:
            assert "demo" in str(exc)


def test_budget_blocks_when_disabled_or_zero(app_env):
    from neuralnews.config import get_settings
    from neuralnews.db import session_scope

    settings = get_settings()
    settings.demo_mode = False
    try:
        with session_scope() as db:
            try:
                assert_paid_call_allowed(db, "search")
                raise AssertionError("debía bloquearse con servicios de pago desactivados")
            except BudgetExceeded as exc:
                assert "desactivados" in str(exc)

            with session_scope() as db2:
                from neuralnews.services.budget import set_budget

                set_budget(db2, paid_services_enabled=True, daily_limit_eur=0.0)
            with session_scope() as db3:
                try:
                    assert_paid_call_allowed(db3, "search")
                    raise AssertionError("debía bloquearse con presupuesto 0")
                except BudgetExceeded as exc:
                    assert "0" in str(exc)
    finally:
        settings.demo_mode = True


def test_budget_stops_when_daily_limit_spent(app_env):
    from neuralnews.config import get_settings
    from neuralnews.db import session_scope
    from neuralnews.services.budget import set_budget

    settings = get_settings()
    settings.demo_mode = False
    try:
        with session_scope() as db:
            set_budget(db, paid_services_enabled=True, daily_limit_eur=0.10)
            record_usage(db, provider="search", cost_actual=0.09, event="call")
        with session_scope() as db:
            # 0.01 € restantes: una llamada de 0.02 se bloquea.
            try:
                assert_paid_call_allowed(db, "search", estimated_cost_eur=0.02)
                raise AssertionError("debía bloquearse por presupuesto agotado")
            except BudgetExceeded as exc:
                assert "Presupuesto diario agotado" in str(exc) or "agotado" in str(exc)
            # Una llamada de 0.01 cabe exactamente.
            assert_paid_call_allowed(db, "search", estimated_cost_eur=0.01)
    finally:
        settings.demo_mode = True


def test_usage_summary_records_calls(demo_client, worker):
    demo_client.post("/api/v1/sources", json={"text": "Cortexa Labs anuncia Radar hoy mismo."})
    worker()
    usage = demo_client.get("/api/v1/usage").json()
    assert usage["budget"]["paid_services_enabled"] is False
    assert usage["today_calls"] >= 0


# ------------------------------------------------------------------ E2E recorrido crítico
def test_e2e_full_critical_path(demo_client, worker, app_env):
    client = demo_client

    # 1) Alta de dos fuentes: un vídeo demo de YouTube + un texto manual.
    video = client.post("/api/v1/sources", json={"url": "https://youtu.be/e2eVid12345"}).json()
    assert video["created"] is True
    manual = client.post(
        "/api/v1/sources",
        json={"text": "Vireo AI levanta 40 millones de dólares liderados por Meridian Capital."},
    ).json()
    worker()

    # 2) El vídeo demo produce candidatos con procedencia; el texto manual, el suyo.
    video_detail = client.get(f"/api/v1/sources/{video['source']['id']}").json()
    assert video_detail["status"] == "READY"
    content_types = {c["content_type"] for c in video_detail["contents"]}
    assert "VIDEO_ANALYSIS" in content_types
    assert len(video_detail["stories"]) >= 2  # Cortexa + opinión

    # 3) Investigación de la noticia de Cortexa (prefijo exacto; la opinión del vídeo
    #    también menciona «radar» en su topic_key y debe excluirse).
    stories = client.get("/api/v1/stories").json()["items"]
    radar = next(s for s in stories if s["topic_key"].startswith("cortexa-labs-radar"))
    client.post(f"/api/v1/stories/{radar['id']}/research")
    worker()
    detail = client.get(f"/api/v1/stories/{radar['id']}").json()
    assert detail["status"] == "REVIEW_REQUIRED"
    assert any(claim["evidence"] for claim in detail["claims"])

    # 4) Guion, edición humana y aprobación.
    client.post(f"/api/v1/stories/{radar['id']}/draft")
    worker()
    detail = client.get(f"/api/v1/stories/{radar['id']}").json()
    version = detail["script_versions"][-1]
    edited = version["content"] + "\n\nCierre ajustado para la locución."
    patch = client.patch(
        f"/api/v1/stories/{radar['id']}/script",
        json={"content": edited, "expected_version": version["version"]},
    )
    assert patch.status_code == 200, patch.text
    detail = client.get(f"/api/v1/stories/{radar['id']}").json()
    last = detail["script_versions"][-1]
    approve = client.post(
        f"/api/v1/stories/{radar['id']}/approve", json={"script_version_id": last["id"]}
    )
    assert approve.status_code == 200

    # 5) Completar un lote de 5 con historias aprobadas.
    extra_ids = []
    for i in range(4):
        payload = client.post(
            "/api/v1/sources",
            json={
                "text": f"Noticia de relleno de prueba {i}: la empresa ficticia Acme presenta el "
                f"dispositivo Y{i} hoy, disponible en demo web."
            },
        ).json()
        worker()
        s_detail = client.get(f"/api/v1/sources/{payload['source']['id']}").json()
        extra_ids.append(s_detail["stories"][0]["id"])
    batch_ids = [radar["id"]] + extra_ids
    for sid in batch_ids[1:]:
        client.post(f"/api/v1/stories/{sid}/research")
        client.post(f"/api/v1/stories/{sid}/draft")
        worker()
        d = client.get(f"/api/v1/stories/{sid}").json()
        client.post(
            f"/api/v1/stories/{sid}/approve",
            json={"script_version_id": d["script_versions"][-1]["id"]},
        )

    batch = client.post(
        "/api/v1/batches", json={"name": "E2E", "target_size": 5, "story_ids": batch_ids}
    )
    assert batch.status_code == 200, batch.text
    batch_id = batch.json()["id"]

    # 6) Exportación y descarga del paquete.
    export = client.post(f"/api/v1/batches/{batch_id}/export")
    worker()
    assert client.get(f"/api/v1/jobs/{export.json()['job_id']}").json()["status"] == "DONE"
    download = client.get(f"/api/v1/batches/{batch_id}/package")
    assert download.status_code == 200
    with zipfile.ZipFile(io.BytesIO(download.content)) as zf:
        manifest = json.loads(zf.read("lote/manifiesto.json"))
    assert manifest["batch"]["target_size"] == 5
    assert manifest["approved_count"] == 5

    # 7) Errores y consumo visibles.
    jobs = client.get("/api/v1/jobs").json()["items"]
    assert jobs, "debe haber historial de trabajos"
    usage = client.get("/api/v1/usage").json()
    assert "budget" in usage
