"""NN-110.a — Leases de la cola: reserva visible, renovación, barrido y liberación.

El lease solo sirve si la reserva es visible desde el principio. Antes, la
reserva y la finalización del trabajo se confirmaban en la MISMA transacción:
mientras el trabajo se ejecutaba, para el resto del sistema el trabajo seguía
en `QUEUED`, así que:

  - el lease no significaba nada (nadie veía `RUNNING`);
  - `recover_stale_jobs` no encontraba nada que recuperar;
  - un trabajo largo podía perder el lease a mitad sin que nada lo renovara
    (hallazgo P4 de la auditoría, closed en NN-110.a).

Cada prueba de este fichero falla con el código anterior al arreglo.
"""
from __future__ import annotations

from datetime import timedelta

from neuralnews.db import get_session_factory
from neuralnews.models import Job, utcnow
from neuralnews.queue import (
    claim_next_job,
    recover_stale_jobs,
    release_job,
    renew_lease,
)


def _encolar(tipo: str = "process_source", dedupe: str | None = None) -> int:
    from neuralnews.queue import enqueue

    with get_session_factory()() as db:
        job, _ = enqueue(db, tipo, {"source_id": 1}, dedupe_key=dedupe)
        job_id = job.id
        db.commit()
    return job_id


def _estado(job_id: int) -> tuple[str, int, object]:
    with get_session_factory()() as db:
        job = db.get(Job, job_id)
        assert job is not None
        return job.status, job.attempt, job.lease_until


# ---------------------------------------------------------------------------
# La reserva se confirma de inmediato
# ---------------------------------------------------------------------------


def test_la_reserva_es_visible_para_otros_inmediatamente(app_env):
    """Tras reclamar, otra sesión ve RUNNING con su lease: no solo QUEUED."""
    job_id = _encolar()

    with get_session_factory()() as db:
        job = claim_next_job(db, lease_seconds=60)
        assert job is not None and job.id == job_id
        # El worker confirma la reserva en el momento: aquí es donde ocurre.
        db.commit()

    estado, intento, lease = _estado(job_id)
    assert estado == "RUNNING", (
        "la reserva debe quedar confirmada antes de ejecutar el trabajo: "
        "si no, el lease no significa nada y el trabajo puede duplicarse"
    )
    assert intento == 1
    assert lease is not None


# ---------------------------------------------------------------------------
# Renovación del lease
# ---------------------------------------------------------------------------


def test_renew_lease_extiende_el_lease(app_env):
    """Renovar un trabajo en marcha mueve `lease_until` hacia adelante."""
    job_id = _encolar()
    with get_session_factory()() as db:
        claim_next_job(db, lease_seconds=60)
        db.commit()

    _, _, lease_antes = _estado(job_id)
    assert lease_antes is not None

    with get_session_factory()() as db:
        ok = renew_lease(db, job_id, lease_seconds=900)
        db.commit()
    assert ok is True

    _, _, lease_despues = _estado(job_id)
    assert lease_despues is not None
    assert lease_despues > lease_antes, "el lease debe extenderse"


def test_renew_lease_no_toca_un_trabajo_que_no_esta_en_marcha(app_env):
    """Un trabajo terminado no se renueva: el lease solo existe en RUNNING."""
    job_id = _encolar()
    with get_session_factory()() as db:
        job = claim_next_job(db, lease_seconds=60)
        job.status = "DONE"
        db.commit()

    with get_session_factory()() as db:
        ok = renew_lease(db, job_id, lease_seconds=900)
        db.commit()
    assert ok is False


# ---------------------------------------------------------------------------
# Barrido de trabajos vencidos
# ---------------------------------------------------------------------------


def test_un_trabajo_con_lease_caducado_se_recupera(app_env):
    """Un trabajo cuyo lease caducó vuelve a la cola, sin reiniciar el worker."""
    job_id = _encolar()
    with get_session_factory()() as db:
        job = claim_next_job(db, lease_seconds=60)
        job.lease_until = utcnow() - timedelta(seconds=1)
        db.commit()

    with get_session_factory()() as db:
        recuperados = recover_stale_jobs(db, lease_seconds=60)
        db.commit()

    assert job_id in recuperados
    estado, _, lease = _estado(job_id)
    assert estado == "RETRYABLE_FAILED"
    assert lease is None, "un trabajo recuperable no debe conservar el lease"


def test_la_recuperacion_no_toca_los_trabajos_que_ejecuta_este_worker(app_env):
    """El worker no recupera lo que él mismo está ejecutando."""
    job_id = _encolar()
    with get_session_factory()() as db:
        job = claim_next_job(db, lease_seconds=60)
        job.lease_until = utcnow() - timedelta(seconds=1)
        db.commit()

    with get_session_factory()() as db:
        recuperados = recover_stale_jobs(db, lease_seconds=60, skip_ids={job_id})
        db.commit()

    assert job_id not in recuperados
    estado, _, _ = _estado(job_id)
    assert estado == "RUNNING", "un trabajo activo no debe pasar a la cola"


def test_el_barrido_del_worker_recupera_los_vencidos(app_env):
    """El barrido periódico del worker recupera lo vencido sin reiniciarlo."""
    from neuralnews import worker as worker_mod

    job_id = _encolar()
    with get_session_factory()() as db:
        job = claim_next_job(db, lease_seconds=60)
        job.lease_until = utcnow() - timedelta(seconds=1)
        db.commit()

    recuperados = worker_mod.sweep_stale_jobs(lease_seconds=60)

    assert job_id in recuperados
    estado, _, _ = _estado(job_id)
    assert estado == "RETRYABLE_FAILED"


# ---------------------------------------------------------------------------
# Liberación del trabajo
# ---------------------------------------------------------------------------


def test_release_job_limpia_lease_y_reinicia_el_intento(app_env):
    """Al devolver un trabajo a la cola no queda lease ni intento acumulado."""
    job_id = _encolar()
    with get_session_factory()() as db:
        claim_next_job(db, lease_seconds=60)
        db.commit()

    with get_session_factory()() as db:
        release_job(db, job_id)
        db.commit()

    estado, intento, lease = _estado(job_id)
    assert estado == "QUEUED"
    assert intento == 0, "un trabajo re-encolado empieza de cero"
    assert lease is None, "no debe quedar un lease viejo"


def test_release_job_no_inventa_trabajos(app_env):
    """Liberar un trabajo inexistente no revienta ni crea nada."""
    with get_session_factory()() as db:
        release_job(db, 999999)
        db.commit()
    with get_session_factory()() as db:
        assert db.get(Job, 999999) is None
