"""Cola de trabajos persistente en la base de datos.

Contrato: trabajos con dedupe_key única (idempotencia), reserva por lease con
caducidad, reintentos acotados y recuperación tras reinicio. Nunca se reintenta
a ciegas una operación de pago tras un timeout (ver handlers).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_, select, update

from .models import Job, utcnow
from .states import JOB_TRANSITIONS


class JobConflict(Exception):
    """Ya existe un trabajo con la misma clave de deduplicación."""


def enqueue(db, job_type: str, payload: dict, dedupe_key: str | None = None) -> tuple[Job, bool]:
    """Devuelve (job, created). Reutiliza el trabajo más reciente con esa dedupe_key (o sus
    reintentos «:rN») mientras esté vivo (en cola, en marcha o reintenable); si el último ya
    terminó (DONE/FAILED), un nuevo uso de la clave crea un trabajo nuevo (reinvestigar,
    reprocesar), con un sufijo libre que nunca choca."""
    if dedupe_key:
        existing = db.scalar(
            select(Job)
            .where(
                or_(
                    Job.dedupe_key == dedupe_key,
                    Job.dedupe_key.like(f"{dedupe_key}:r%"),
                )
            )
            .order_by(Job.id.desc())
            .limit(1)
        )
        if existing is not None:
            if existing.status in ("DONE", "FAILED", "UNKNOWN"):
                suffix = 1
                while (
                    db.scalar(select(Job.id).where(Job.dedupe_key == f"{dedupe_key}:r{suffix}"))
                    is not None
                ):
                    suffix += 1
                dedupe_key = f"{dedupe_key}:r{suffix}"
            else:
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


def recover_stale_jobs(
    db, lease_seconds: int, skip_ids: set[int] | None = None
) -> list[int]:
    """Marca como reintenables los trabajos con lease caducado.

    Los reintentos son seguros porque los handlers son idempotentes y las
    llamadas de pago no se repiten automáticamente (ver presupuesto/handlers).

    `skip_ids` son los trabajos que el worker actual tiene en marcha: no se
    tocan aunque su lease haya caducado. En SQLite las escrituras se serializan
    y la renovación del lease puede quedar bloqueada mientras el manejador
    escribe; sin esta salvedad, un trabajo largo se recuperaría a sí mismo.
    """
    now = utcnow()
    stale = db.scalars(
        select(Job).where(Job.status == "RUNNING", Job.lease_until < now)
    ).all()
    recovered: list[int] = []
    for job in stale:
        if skip_ids and job.id in skip_ids:
            continue
        job.status = "RETRYABLE_FAILED"
        job.error = "El trabajo se interrumpió (reinicio o caída); quedará en cola de reintento"
        job.lease_until = None
        job.next_run_at = now
        recovered.append(job.id)
    return recovered


def renew_lease(db, job_id: int, lease_seconds: int) -> bool:
    """Renueva el lease de un trabajo en marcha.

    Devuelve `False` si el trabajo ya no está en `RUNNING` (terminó o fue
    recuperado): en ese caso no hay nada que renovar.
    """
    now = utcnow()
    result = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == "RUNNING")
        .values(lease_until=now + timedelta(seconds=lease_seconds))
        .execution_options(synchronize_session=False)
    )
    return bool(result.rowcount)


def claim_next_job(db, lease_seconds: int) -> Job | None:
    """Reserva el siguiente trabajo disponible (QUEUED o reintento vencido).

    La reserva se CONFIRMA dentro de la función: el trabajo pasa a `RUNNING` con
    su lease antes de ejecutar nada. Antes la reserva y la finalización se
    confirmaban juntas, así que mientras el trabajo se ejecutaba seguía
    pareciendo `QUEUED` para el resto del sistema: el lease no significaba
    nada, la recuperación no encontraba nada que recuperar y un trabajo largo
    perdía el lease a mitad sin que nada lo renovara.
    """
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
    db.commit()
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
    """Devuelve un trabajo a la cola.

    Se limpian el lease y el intento acumulado: un trabajo re-encolado no puede
    arrastrar un lease viejo (que lo dejaría «vencido» al instante) ni un
    contador de intentos que lo empujaría a `FAILED` sin haberlo intentado.
    """
    db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status="QUEUED", lease_until=None, next_run_at=None, attempt=0)
        .execution_options(synchronize_session=False)
    )
