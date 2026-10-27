"""Cola de trabajos persistente en la base de datos.

Contrato: trabajos con dedupe_key única (idempotencia), reserva por lease con
caducidad, reintentos acotados y recuperación tras reinicio. Nunca se reintenta
a ciegas una operación de pago tras un timeout (ver handlers).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update

from .models import Job, utcnow
from .states import JOB_TRANSITIONS


class JobConflict(Exception):
    """Ya existe un trabajo con la misma clave de deduplicación."""


def enqueue(db, job_type: str, payload: dict, dedupe_key: str | None = None) -> tuple[Job, bool]:
    """Devuelve (job, created). Si la dedupe_key existe, devuelve el trabajo original."""
    if dedupe_key:
        existing = db.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
        if existing is not None:
            return existing, False
    job = Job(
        type=job_type,
        payload=payload,
        dedupe_key=dedupe_key,
        max_attempts=3,
        status="QUEUED",
    )
    db.add(job)
    db.flush()
    return job, True


def recover_stale_jobs(db, lease_seconds: int) -> list[int]:
    """Al arrancar el worker: marca como reintenables los trabajos con lease caducado.

    Los reintentos son seguros porque los handlers son idempotentes y las
    llamadas de pago no se repiten automáticamente (ver presupuesto/handlers).
    """
    now = utcnow()
    stale = db.scalars(
        select(Job).where(Job.status == "RUNNING", Job.lease_until < now)
    ).all()
    recovered: list[int] = []
    for job in stale:
        job.status = "RETRYABLE_FAILED"
        job.error = "El trabajo se interrumpió (reinicio o caída); quedará en cola de reintento"
        job.lease_until = None
        job.next_run_at = now
        recovered.append(job.id)
    return recovered


def claim_next_job(db, lease_seconds: int) -> Job | None:
    """Reserva el siguiente trabajo disponible (QUEUED o reintento vencido)."""
    now = utcnow()
    job = db.scalar(
        select(Job)
        .where(
            Job.status.in_(["QUEUED", "RETRYABLE_FAILED"]),
            (Job.next_run_at.is_(None)) | (Job.next_run_at <= now),
        )
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status = "RUNNING"
    job.attempt += 1
    job.started_at = job.started_at or now
    job.lease_until = now + timedelta(seconds=lease_seconds)
    job.error = None
    return job


def mark_done(db, job: Job) -> None:
    job.status = "DONE"
    job.finished_at = utcnow()
    job.lease_until = None


def mark_retryable(db, job: Job, error: str, backoff_seconds: int = 30) -> None:
    job.status = "RETRYABLE_FAILED"
    job.error = error
    job.lease_until = None
    if job.attempt >= job.max_attempts:
        job.status = "FAILED"
        job.finished_at = utcnow()
        job.next_run_at = None
    else:
        job.next_run_at = utcnow() + timedelta(seconds=backoff_seconds * job.attempt)


def mark_failed(db, job: Job, error: str) -> None:
    """Fallo definitivo: no se reintenta (p. ej., presupuesto agotado o entrada inválida)."""
    job.status = "FAILED"
    job.error = error
    job.lease_until = None
    job.finished_at = utcnow()
    job.next_run_at = None


def release_job(db, job_id: int) -> None:
    db.execute(update(Job).where(Job.id == job_id).values(status="QUEUED"))
