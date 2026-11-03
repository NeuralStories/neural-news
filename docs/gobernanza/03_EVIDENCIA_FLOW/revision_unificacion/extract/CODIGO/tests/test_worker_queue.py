"""Etapa 1/2 — cola de trabajos: dedupe, leases, reintentos y recuperación tras reinicio."""
from __future__ import annotations

from datetime import timedelta

from neuralnews.db import session_scope
from neuralnews.models import Job, Story, utcnow
from neuralnews.queue import (
    claim_next_job,
    enqueue,
    mark_done,
    mark_retryable,
    recover_stale_jobs,
)
from neuralnews.worker_tasks import PROCESS_SOURCE, run_job


def _create_source(client, text: str) -> int:
    payload = client.post("/api/v1/sources", json={"text": text}).json()
    return payload["source"]["id"]


def test_enqueue_dedupes_by_key(app_env):
    with session_scope() as db:
        job1, created1 = enqueue(db, "tipo", {"x": 1}, dedupe_key="k-1")
        job2, created2 = enqueue(db, "tipo", {"x": 1}, dedupe_key="k-1")
        assert created1 is True and created2 is False
        assert job1.id == job2.id


def test_claim_sets_running_and_lease(app_env):
    with session_scope() as db:
        enqueue(db, "tipo", {}, dedupe_key="claim-1")
        job = claim_next_job(db, lease_seconds=60)
        assert job is not None
        assert job.status == "RUNNING"
        assert job.attempt == 1
        assert job.lease_until is not None
        mark_done(db, job)
        assert job.status == "DONE"


def test_retry_until_max_attempts(app_env):
    with session_scope() as db:
        enqueue(db, "tipo", {}, dedupe_key="retry-1", )
        job = claim_next_job(db, 60)
        for expected_attempt in range(1, 4):
            assert job.attempt == expected_attempt
            mark_retryable(db, job, "error simulado")
            if job.status == "FAILED":
                break
            job.next_run_at = utcnow() - timedelta(seconds=1)  # vence el backoff
            job.status = "RETRYABLE_FAILED"
            job = claim_next_job(db, 60)
            assert job is not None
        assert job.status == "FAILED"
        assert job.attempt == 3


def test_stale_lease_recovered_on_restart(app_env):
    with session_scope() as db:
        job, _ = enqueue(db, "tipo", {}, dedupe_key="stale-1")
        job.status = "RUNNING"
        job.lease_until = utcnow() - timedelta(seconds=10)
        db.flush()
        recovered = recover_stale_jobs(db, 300)
        assert job.id in recovered
        assert job.status == "RETRYABLE_FAILED"


def test_process_job_creates_candidates_once(worker, demo_client):
    source_id = _create_source(demo_client, "Cortexa Labs ha anunciado Radar y Vireo AI ha levantado 40 millones.")
    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    job_id = next(j["id"] for j in jobs if j["type"] == PROCESS_SOURCE)
    worker()

    job = demo_client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "DONE", job
    assert "candidato" in job["progress"]

    stories = demo_client.get("/api/v1/stories").json()["items"]
    topics = {s["topic_key"] for s in stories}
    assert len(topics) == len(stories), "topic_key repetidos: extracción no idempotente"
    assert any("radar" in t for t in topics)


def test_worker_restart_does_not_duplicate_candidates(worker, demo_client):
    source_id = _create_source(demo_client, "Cortexa Labs anuncia Radar otra vez con detalles.")
    worker()
    before = demo_client.get("/api/v1/stories").json()["total"]

    # Reinicio: el trabajo DONE no se reejecuta; reprocesar la fuente es idempotente por topic_key.
    demo_client.post(f"/api/v1/sources/{source_id}/process", json={})
    worker()
    after = demo_client.get("/api/v1/stories").json()["total"]
    assert after == before


def test_unknown_job_type_fails_cleanly(app_env):
    with session_scope() as db:
        job, _ = enqueue(db, "tipo_inexistente", {}, dedupe_key="unknown-1")
        job = claim_next_job(db, 60)
        run_job(db, job)
        assert job.status == "FAILED"
        assert "desconocido" in job.error


def test_metadata_only_source_is_not_retried(app_env, demo_client, worker):
    """Una fuente sin transcripción termina el trabajo con un mensaje claro, sin reintentos."""
    from neuralnews.models import Source, SourceContent

    with session_scope() as db:
        source = Source(
            provider="spotify",
            external_id="ep-demo-sin-transcripcion",
            canonical_url="https://open.spotify.com/episode/ep-demo-sin-transcripcion",
            title="Episodio de ejemplo (DEMO)",
            status="NEW",
            demo=True,
            metadata_json={},
        )
        db.add(source)
        db.flush()
        db.add(
            SourceContent(
                source_id=source.id,
                content_type="METADATA_ONLY",
                is_verbatim=False,
                provider="demo",
                text="Descripción del episodio de ejemplo, sin transcripción.",
                content_hash="f" * 64,
            )
        )
        db.flush()
        source_id = source.id
        job, _ = enqueue(db, "process_source", {"source_id": source_id}, dedupe_key="meta-only-1")
        job_id = job.id

    with session_scope() as db:
        job = claim_next_job(db, lease_seconds=60)  # el worker reclama antes de ejecutar
        assert job is not None and job.id == job_id
        run_job(db, job)
        assert job.status == "DONE", "no debe fallar ni reintentarse"
        assert job.attempt == 1, "no debe reintentar"
        assert "información básica" in (job.progress or "")
        assert job.error is None


def test_all_job_handlers_execute_without_name_errors(app_env, demo_client, worker):
    """Cada handler del worker debe ejecutarse sin errores de nombre (p. ej. imports olvidados)."""
    from neuralnews.worker_tasks import HANDLERS

    for job_type in HANDLERS:
        assert job_type, "no debe haber handlers vacíos"

    # guion: ejercita handle_draft_script (registra consumo y crea versión)
    payload = demo_client.post(
        "/api/v1/sources", json={"text": "Acme Instruments ha lanzado hoy el chip Z9 con un 30 por ciento mas de potencia."}
    ).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
    story_id = detail["stories"][0]["id"]

    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()

    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    fallidos = [j for j in jobs if j["status"] in ("FAILED", "RETRYABLE_FAILED")]
    assert not fallidos, f"trabajos con error: {[(j['id'], j['type'], j.get('error')) for j in fallidos]}"
    assert demo_client.get(f"/api/v1/stories/{story_id}").json()["script_versions"], "debe haber guion"


def test_retry_after_permanent_failure_creates_new_job(app_env):
    """Repetir una clave cuyo trabajo ya falló debe permitir un trabajo nuevo, no bloquearse."""
    with session_scope() as db:
        job1, created1 = enqueue(db, "tipo", {}, dedupe_key="retry-after-fail")
        job1 = claim_next_job(db, 60)
        from neuralnews.queue import mark_failed

        mark_failed(db, job1, "fallo definitivo simulado")
        job2, created2 = enqueue(db, "tipo", {}, dedupe_key="retry-after-fail")
        assert created2 is True and job2.id != job1.id
        # Mientras el trabajo sigue vivo (en cola), la clave lo reutiliza.
        job3, created3 = enqueue(db, "tipo", {}, dedupe_key="retry-after-fail")
        assert created3 is False and job3.id == job2.id
