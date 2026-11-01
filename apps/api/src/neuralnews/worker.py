"""Worker: bucle que reclama trabajos de la cola persistente y los ejecuta.

Arranque: `neuralnews-worker` (entrypoint) o `python -m neuralnews.worker`.
Al arrancar recupera trabajos con lease caducado (recuperación tras reinicio) y
después los va barriendo periódicamente, sin necesidad de reiniciar.

El lease de un trabajo se renueva mientras se ejecuta: un trabajo largo (un
montaje con FFmpeg, por ejemplo) no debe perderlo a mitad y acabar ejecutándose
dos veces.
"""
from __future__ import annotations

import logging
import sys
import threading
import time
from contextlib import contextmanager
from typing import Iterator

from .config import get_settings
from .db import session_scope
from .models import Job
from .queue import claim_next_job, recover_stale_jobs, renew_lease
from .worker_tasks import run_job

logger = logging.getLogger(__name__)

# Trabajos que este worker tiene en marcha. Permite que el barrido no recupere
# lo que este mismo proceso está ejecutando.
_ACTIVE_JOBS: set[int] = set()


def configure_streams() -> None:
    """Deja los flujos del worker en UTF-8 con sustitución.

    En Windows la salida redirigida a un fichero usa la codificación ANSI
    (cp1252) y un carácter como «→» provoca UnicodeEncodeError. Como el
    mensaje se escribía DENTRO de la transacción, el error la revertía entera:
    el trabajo se ejecutaba, pero nunca se marcaba como terminado y el bucle
    lo reclamaba otra vez para siempre (hallazgo B19).
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # flujos no reconfigurables
            pass


def _renovar_lease(job_id: int, stop: threading.Event, intervalo: float) -> None:
    """Renueva el lease del trabajo mientras dure su ejecución."""
    lease_seconds = get_settings().job_lease_seconds
    while not stop.wait(intervalo):
        try:
            with session_scope() as db:
                renew_lease(db, job_id, lease_seconds)
        except Exception as exc:  # noqa: BLE001 — la renovación es best effort
            # En SQLite las escrituras se serializan: si el manejador está
            # escribiendo, la renovación puede quedar bloqueada. No es fatal:
            # el barrido ignora los trabajos que este worker tiene activos.
            logger.debug("No se pudo renovar el lease del trabajo %s: %s", job_id, exc)


@contextmanager
def active_job(job_id: int) -> Iterator[None]:
    """Marca el trabajo como activo y renueva su lease mientras dure."""
    _ACTIVE_JOBS.add(job_id)
    stop = threading.Event()
    intervalo = max(5.0, get_settings().job_lease_seconds / 3)
    hilo = threading.Thread(
        target=_renovar_lease, args=(job_id, stop, intervalo), daemon=True
    )
    hilo.start()
    try:
        yield
    finally:
        stop.set()
        hilo.join(timeout=2)
        _ACTIVE_JOBS.discard(job_id)


def sweep_stale_jobs(lease_seconds: int | None = None) -> list[int]:
    """Recupera los trabajos cuyo lease caducó, sin tocar los de este worker."""
    if lease_seconds is None:
        lease_seconds = get_settings().job_lease_seconds
    with session_scope() as db:
        return recover_stale_jobs(db, lease_seconds, skip_ids=set(_ACTIVE_JOBS))


def tick() -> int:
    """Reclama y ejecuta un trabajo. Devuelve 1 si hubo trabajo, 0 si la cola está vacía."""
    settings = get_settings()
    # La reserva se confirma al instante (dentro de `claim_next_job`): desde
    # aquí el trabajo es visible como RUNNING con su lease.
    with session_scope() as db:
        job = claim_next_job(db, lease_seconds=settings.job_lease_seconds)
        if job is None:
            return 0
        job_id, job_type, intento = job.id, job.type, job.attempt
    with active_job(job_id):
        with session_scope() as db:
            job = db.get(Job, job_id)
            if job is None:
                return 0
            print(f"[worker] job #{job.id} tipo={job.type} intento={job.attempt}", flush=True)
            run_job(db, job)
            estado, error = job.status, job.error
    # Fuera de la transacción: escribir el estado no puede revertir un trabajo
    # que ya ha terminado.
    try:
        print(
            f"[worker] job #{job_id} → {estado}" + (f" — {error}" if error else ""),
            flush=True,
        )
    except Exception:  # noqa: BLE001 — el log nunca puede tumbar el bucle
        pass
    return 1


def run(poll_seconds: float = 1.0, once: bool = False) -> None:
    configure_streams()
    settings = get_settings()
    recovered = sweep_stale_jobs(settings.job_lease_seconds)
    if recovered:
        print(
            f"[worker] recuperados {len(recovered)} trabajos interrumpidos: {recovered}",
            flush=True,
        )
    print(
        f"[worker] neural.news worker arrancado (demo={settings.demo_mode}, "
        f"pagos={'ON' if settings.paid_services_enabled else 'OFF'})",
        flush=True,
    )
    # Barrido periódico: un trabajo que se quedó con el lease caducado (worker
    # caído, proceso terminado) se recupera sin tener que reiniciar el worker.
    intervalo_barrido = max(30.0, settings.job_lease_seconds / 2)
    ultimo_barrido = time.monotonic()
    while True:
        try:
            worked = tick()
            ahora = time.monotonic()
            if ahora - ultimo_barrido >= intervalo_barrido:
                ultimo_barrido = ahora
                vencidos = sweep_stale_jobs(settings.job_lease_seconds)
                if vencidos:
                    print(
                        f"[worker] barrido: recuperados {len(vencidos)} trabajos vencidos: {vencidos}",
                        flush=True,
                    )
        except KeyboardInterrupt:
            print("[worker] parando por interrupción del usuario", flush=True)
            return
        except Exception as exc:  # noqa: BLE001 — el bucle nunca muere por un trabajo
            try:
                print(f"[worker] error fuera del trabajo: {exc}", file=sys.stderr, flush=True)
            except Exception:  # noqa: BLE001 — ni el log puede tumbar el bucle
                pass
            worked = 0
        if once and worked == 0:
            return
        if not worked:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run(once="--once" in sys.argv)


def run_cli() -> None:
    """Entrypoint de consola."""
    run(once="--once" in sys.argv)
