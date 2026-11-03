"""Servicio de trabajos audiovisuales (Fase 5, T504-T507) y presupuesto por lote (T514).

Ciclo de vida: `QUEUED → RUNNING → DONE` con reintentos `RETRYABLE_FAILED`
y fallo definitivo `FAILED`, reutilizando la cola persistente existente
(`queue.py`: dedupe_key, leases, recuperación tras reinicio). La deduplicación
de la generación es por huella de contenido (tipo + proyecto + escena + prompt +
formato), de modo que reintentar o repetir un encargo no genera artefactos
duplicados.

**Presupuesto (T514).** Hay dos niveles:

- `max_cost_eur`: techo **por trabajo**; si el coste estimado del trabajo lo
  supera, el trabajo falla de forma definitiva sin generar artefacto.
- Techo **agregado del lote** (`batch_budgets.limit_eur`): al encolar un trabajo
  se *reserva* su coste estimado; si la reserva supera el techo, el encolado se
  rechaza antes de crear el trabajo (nada se genera ni se cobra). Al terminar
  el trabajo, la reserva se liquida con el coste real; si falla, se libera.
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from ..models import BatchBudget, Job
from ..queue import enqueue


def av_dedupe_key(request_payload: dict) -> str:
    fingerprint = hashlib.sha256(
        json.dumps(request_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"avgen:{fingerprint[:24]}"


def enqueue_av_generation(db: Session, request_payload: dict) -> tuple[Job, bool]:
    """Encola la generación de un artefacto audiovisual simulado.

    Devuelve (job, created): un encargo idéntico mientras esté vivo reutiliza el
    mismo trabajo (sin duplicar generación); si el anterior terminó, se crea un
    trabajo nuevo con sufijo de reintento.
    """
    return enqueue(db, "av_generate", {"request": request_payload}, dedupe_key=av_dedupe_key(request_payload))


def av_render_fingerprint(plan: dict) -> str:
    from .av_render import plan_fingerprint

    return plan_fingerprint(plan)


# --------------------------------------------------------------------- presupuesto


def get_batch_budget(db: Session, batch_id: int) -> BatchBudget | None:
    return db.get(BatchBudget, batch_id)


def set_batch_budget(db: Session, batch_id: int, limit_eur: float | None) -> BatchBudget:
    """Fija (o cambia) el techo agregado de presupuesto de un lote."""
    row = db.get(BatchBudget, batch_id)
    if row is None:
        row = BatchBudget(batch_id=batch_id, limit_eur=limit_eur)
        db.add(row)
    else:
        row.limit_eur = limit_eur
    db.flush()
    return row


def batch_budget_summary(db: Session, batch_id: int) -> dict:
    """Estado del presupuesto del lote: techo, reservado y gastado."""
    row = db.get(BatchBudget, batch_id)
    if row is None:
        return {
            "batch_id": batch_id,
            "limit_eur": None,
            "committed_eur": 0.0,
            "spent_eur": 0.0,
            "available_eur": None,
        }
    limit = row.limit_eur
    available = None if limit is None else max(0.0, round(limit - row.committed_eur - row.spent_eur, 6))
    return {
        "batch_id": batch_id,
        "limit_eur": limit,
        "committed_eur": round(row.committed_eur, 6),
        "spent_eur": round(row.spent_eur, 6),
        "available_eur": available,
    }


def reserve_batch_budget(db: Session, batch_id: int, estimated_cost_eur: float) -> None:
    """Reserva coste estimado para un trabajo del lote.

    Lanza `BudgetExceeded` si la reserva supera el techo agregado: en ese caso el
    trabajo NO se encola (no se genera ni se cobra nada).
    """
    from .budget import BudgetExceeded

    row = db.get(BatchBudget, batch_id)
    if row is None or row.limit_eur is None:
        return  # sin techo de lote: el control por trabajo sigue aplicando
    amount = float(estimated_cost_eur or 0.0)
    if amount <= 0:
        return
    projected = row.committed_eur + row.spent_eur + amount
    if projected > float(row.limit_eur) + 1e-9:
        raise BudgetExceeded(
            f"El lote no tiene presupuesto suficiente: {row.committed_eur + row.spent_eur:.2f} € ya "
            f"comprometidos de un techo de {float(row.limit_eur):.2f} € y este trabajo estima "
            f"{amount:.2f} €. Reduce el coste del trabajo o aumenta el presupuesto del lote."
        )
    row.committed_eur = round(row.committed_eur + amount, 6)
    db.flush()


def settle_batch_budget(
    db: Session, batch_id: int | None, estimated_cost_eur: float, actual_cost_eur: float
) -> None:
    """Liquida la reserva con el coste real (al terminar el trabajo)."""
    if batch_id is None:
        return
    row = db.get(BatchBudget, batch_id)
    if row is None:
        return
    estimated = float(estimated_cost_eur or 0.0)
    actual = float(actual_cost_eur or 0.0)
    row.committed_eur = round(max(0.0, row.committed_eur - estimated), 6)
    row.spent_eur = round(row.spent_eur + actual, 6)
    db.flush()


def release_batch_budget(db: Session, batch_id: int | None, estimated_cost_eur: float) -> None:
    """Libera la reserva cuando el trabajo falla (no se consumió presupuesto)."""
    if batch_id is None:
        return
    row = db.get(BatchBudget, batch_id)
    if row is None:
        return
    row.committed_eur = round(max(0.0, row.committed_eur - float(estimated_cost_eur or 0.0)), 6)
    db.flush()


# --------------------------------------------------------------------- encolado


def enqueue_av_render(
    db: Session,
    plan: dict,
    max_cost_eur: float | None = None,
    *,
    batch_id: int | None = None,
    estimated_cost_eur: float = 0.0,
) -> tuple[Job, bool]:
    """Encola la composición del vídeo de un plan (Fase 6).

    Dedupe por huella del plan: el mismo plan mientras su trabajo esté vivo se
    reutiliza; `max_cost_eur` fija el techo de presupuesto del trabajo (T514) y
    `batch_id` lo somete al techo agregado del lote.

    Si el lote no tiene presupuesto suficiente, la excepción `BudgetExceeded` se
    propaga **antes** de crear el trabajo: no queda ningún trabajo pendiente.
    """
    payload: dict = {"plan": plan}
    if max_cost_eur is not None:
        payload["max_cost_eur"] = float(max_cost_eur)
    if batch_id is not None:
        payload["batch_id"] = int(batch_id)
    payload["estimated_cost_eur"] = float(estimated_cost_eur or 0.0)

    # El techo POR TRABAJO se comprueba al ejecutar el trabajo (falla de forma
    # definitiva sin generar artefacto); aquí sólo se bloquea el ENCOLADO cuando
    # el techo AGREGADO del lote no admite la reserva.
    if batch_id is not None:
        reserve_batch_budget(db, batch_id, estimated_cost_eur)

    job, created = enqueue(
        db, "av_render", payload, dedupe_key=f"avrender:{av_render_fingerprint(plan)[:24]}"
    )
    if not created:
        # El plan ya estaba encolado: no se duplica la reserva.
        settle_batch_budget(db, batch_id, estimated_cost_eur, 0.0)
    return job, created
