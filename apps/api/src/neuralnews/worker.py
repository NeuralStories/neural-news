"""Worker: bucle que reclama trabajos de la cola persistente y los ejecuta.

Arranque: `neuralnews-worker` (entrypoint) o `python -m neuralnews.worker`.
Al arrancar recupera trabajos con lease caducado (recuperación tras reinicio).
"""
from __future__ import annotations

import sys
import time

from .config import get_settings
from .db import session_scope
from .queue import claim_next_job, recover_stale_jobs
from .worker_tasks import run_job


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


def tick() -> int:
    """Reclama y ejecuta un trabajo. Devuelve 1 si hubo trabajo, 0 si la cola está vacía."""
    with session_scope() as db:
        job = claim_next_job(db, lease_seconds=get_settings().job_lease_seconds)
        if job is None:
            return 0
        print(f"[worker] job #{job.id} tipo={job.type} intento={job.attempt}", flush=True)
        run_job(db, job)
        job_id, status, error = job.id, job.status, job.error
    # Fuera de la transacción: escribir el estado no puede revertir un trabajo
    # que ya ha terminado.
    try:
        print(
            f"[worker] job #{job_id} → {status}" + (f" — {error}" if error else ""),
            flush=True,
        )
    except Exception:  # noqa: BLE001 — el log nunca puede tumbar el bucle
        pass
    return 1


def run(poll_seconds: float = 1.0, once: bool = False) -> None:
    configure_streams()
    settings = get_settings()
    with session_scope() as db:
        recovered = recover_stale_jobs(db, settings.job_lease_seconds)
        if recovered:
            print(f"[worker] recuperados {len(recovered)} trabajos interrumpidos: {recovered}", flush=True)
    print(
        f"[worker] neural.news worker arrancado (demo={settings.demo_mode}, "
        f"pagos={'ON' if settings.paid_services_enabled else 'OFF'})",
        flush=True,
    )
    while True:
        try:
            worked = tick()
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
