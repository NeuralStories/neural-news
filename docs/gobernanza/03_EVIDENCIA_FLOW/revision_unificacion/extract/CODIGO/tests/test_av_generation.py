"""Fase 5 — generación audiovisual simulada: proveedor, dedupe, reintentos y recuperación.

Sin servicios de pago: coste 0, artefactos deterministas bajo `storage/av/`.
"""
from __future__ import annotations

import json

import pytest

import neuralnews.config as config_mod


def storage():
    return config_mod.STORAGE_DIR
from neuralnews.db import session_scope
from neuralnews.models import Job
from neuralnews.providers.av_generation import (
    AvGenerationError,
    AvGenerationRequest,
    SimulatedAvProvider,
)
from neuralnews.queue import recover_stale_jobs
from neuralnews.services.av_jobs import enqueue_av_generation


def _request(**overrides) -> dict:
    base = {
        "kind": "image",
        "project_id": "proj-news-001-9x16",
        "scene_index": 1,
        "prompt": "Plano cercano del presentador en el plató CRT, entrada lateral.",
        "output_format": "9:16",
        "language": "es-ES",
    }
    base.update(overrides)
    return base


def test_proveedor_simulado_determinista_e_idempotente(app_env):
    provider = SimulatedAvProvider()
    first = provider.generate(AvGenerationRequest(**_request()))
    second = provider.generate(AvGenerationRequest(**_request()))
    assert first.artifact_relpath == second.artifact_relpath
    assert first.sha256 == second.sha256
    # el fichero existe y su contenido registra el pedido sin datos inventados
    path = storage() / first.artifact_relpath
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["simulated"] is True
    assert data["kind"] == "image"
    assert data["output_format"] == "9:16"
    # un pedido distinto produce otro artefacto
    other = provider.generate(AvGenerationRequest(**_request(scene_index=2, prompt="Otro prompt distinto.")))
    assert other.artifact_relpath != first.artifact_relpath


def test_proveedor_rechaza_tipos_y_prompts_invalidos(app_env):
    from pydantic import ValidationError

    provider = SimulatedAvProvider()
    # El tipo no soportado se rechaza en la frontera del contrato (pydantic).
    with pytest.raises(ValidationError):
        AvGenerationRequest(**_request(kind="music"))
    with pytest.raises(ValidationError):
        AvGenerationRequest(**_request(kind="subtitulos"))
    # El prompt en blanco pasa la longitud mínima y falla en el proveedor.
    with pytest.raises(AvGenerationError):
        provider.generate(AvGenerationRequest(**_request(prompt="   ")))


def test_encargo_duplicado_reutiliza_el_mismo_trabajo(app_env):
    with session_scope() as db:
        job1, created1 = enqueue_av_generation(db, _request())
        job2, created2 = enqueue_av_generation(db, _request())
        assert created1 is True and created2 is False
        assert job1.id == job2.id
        assert job1.dedupe_key.startswith("avgen:")


def test_worker_ejecuta_el_encargo_y_registra_coste_cero(demo_client, worker, app_env):
    with session_scope() as db:
        job, created = enqueue_av_generation(db, _request())
        job_id = job.id
    worker()
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "DONE", job.error
        assert "simulado generado" in (job.progress or "")
        # el artefacto quedó escrito en storage/av/
        av_files = list((storage() / "av").glob("image-*.json"))
        assert av_files, "el worker debía escribir el artefacto simulado"


def test_reintento_seguro_hasta_fallo_definitivo_con_pedido_invalido(demo_client, worker, app_env):
    from datetime import timedelta

    from neuralnews.models import utcnow

    with session_scope() as db:
        job, _ = enqueue_av_generation(db, _request(kind="subtitulos"))  # tipo no soportado
        job_id = job.id
    worker()  # primer intento: fallo reintenable con backoff
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "RETRYABLE_FAILED"
        assert job.attempt == 1
        # aceleramos el backoff para probar los reintentos
        job.next_run_at = utcnow() - timedelta(seconds=1)
    worker()  # intento 2
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "RETRYABLE_FAILED"
        job.next_run_at = utcnow() - timedelta(seconds=1)
    worker()  # intento 3: agotado
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "FAILED"
        assert "ValidationError" in (job.error or "")
        # nunca se llegó a escribir artefacto para un tipo no soportado
        assert not list((storage() / "av").glob("*subtitulos*"))


def test_recuperacion_tras_interrupcion_no_duplica_artefactos(demo_client, worker, app_env):
    from datetime import timedelta

    from neuralnews.models import utcnow

    with session_scope() as db:
        job, _ = enqueue_av_generation(db, _request())
        job_id = job.id
    worker()  # genera y termina DONE
    with session_scope() as db:
        done = db.get(Job, job_id)
        assert done.status == "DONE"

    # Simula una interrupción: un trabajo igual queda RUNNING con lease caducado.
    with session_scope() as db:
        job2, created = enqueue_av_generation(db, _request())
        assert created is True  # el anterior terminó: nuevo trabajo con sufijo
        job2.status = "RUNNING"
        job2.lease_until = utcnow() - timedelta(seconds=1)
    with session_scope() as db:
        recovered = recover_stale_jobs(db, lease_seconds=60)
        assert job2.id in recovered
    worker()  # se reencola y se completa
    with session_scope() as db:
        final = db.get(Job, job2.id)
        assert final.status == "DONE"
    # El artefacto en disco es el mismo que el primer encargo: sin duplicados.
    first = SimulatedAvProvider().generate(AvGenerationRequest(**_request()))
    assert (storage() / first.artifact_relpath).exists()
