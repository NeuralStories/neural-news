"""Control de presupuesto y registro de consumos.

Por defecto los servicios de pago están desactivados y el presupuesto diario es 0:
cualquier llamada facturable se bloquea hasta configuración explícita. Cuando el
presupuesto diario se agota, se detienen las llamadas pagadas y se sugiere modo demo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Setting, UsageEvent, utcnow


class BudgetExceeded(RuntimeError):
    """Se ha alcanzado el límite de gasto o los servicios de pago están desactivados."""


def get_budget(db: Session) -> dict:
    settings = get_settings()
    row = db.get(Setting, "budget")
    stored = row.value if row and isinstance(row.value, dict) else {}
    return {
        "paid_services_enabled": stored.get("paid_services_enabled", settings.paid_services_enabled),
        "daily_limit_eur": stored.get("daily_limit_eur", settings.budget_daily_eur),
    }


def set_budget(db: Session, *, paid_services_enabled: bool | None, daily_limit_eur: float | None) -> dict:
    current = get_budget(db)
    if paid_services_enabled is not None:
        current["paid_services_enabled"] = paid_services_enabled
    if daily_limit_eur is not None:
        current["daily_limit_eur"] = daily_limit_eur
    db.merge(Setting(key="budget", value=current))
    db.flush()
    return current


def assert_paid_call_allowed(db: Session, provider: str, estimated_cost_eur: float = 0.0) -> None:
    """Comprueba si se puede hacer una llamada de pago; lanza BudgetExceeded si no."""
    settings = get_settings()
    if settings.demo_mode:
        raise BudgetExceeded(
            "El modo demo está activado: las llamadas de pago están deshabilitadas. "
            "Desactiva el modo demo y configura las claves para usar servicios reales."
        )
    budget = get_budget(db)
    if not budget["paid_services_enabled"]:
        raise BudgetExceeded(
            "Los servicios de pago están desactivados. Actívalos en Configuración cuando quieras usarlos."
        )
    if estimated_cost_eur > 0 and not budget["paid_services_enabled"]:
        raise BudgetExceeded("Operación de pago no permitida con la configuración actual")

    limit = float(budget["daily_limit_eur"] or 0)
    if limit <= 0:
        raise BudgetExceeded(
            "El presupuesto diario está a 0 €. Configura un límite en Configuración para permitir llamadas de pago."
        )
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    spent = db.scalar(
        select(func.coalesce(func.sum(func.coalesce(UsageEvent.cost_actual, UsageEvent.cost_estimate)), 0.0)).where(
            UsageEvent.created_at >= start_of_day,
            UsageEvent.provider != "demo",
        )
    ) or 0.0
    if spent + estimated_cost_eur > limit:
        raise BudgetExceeded(
            f"Presupuesto diario agotado ({spent:.2f} de {limit:.2f} €). Puedes seguir trabajando en "
            "modo demo o esperar a mañana."
        )


def record_usage(
    db: Session,
    *,
    provider: str,
    model: str | None = None,
    job_id: int | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost_estimate: float = 0.0,
    cost_actual: float | None = None,
    event: str = "call",
) -> None:
    db.add(
        UsageEvent(
            provider=provider,
            model=model,
            job_id=job_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_estimate=cost_estimate,
            cost_actual=cost_actual,
            event=event,
        )
    )


def usage_summary(db: Session) -> dict:
    start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.scalars(select(UsageEvent).where(UsageEvent.created_at >= start_of_day)).all()
    total_calls = len(today)
    blocked = sum(1 for e in today if e.event == "blocked")
    spent = sum(e.cost_actual or e.cost_estimate for e in today)
    by_provider: dict[str, int] = {}
    for e in today:
        by_provider[e.provider] = by_provider.get(e.provider, 0) + 1
    return {
        "today_calls": total_calls,
        "today_blocked": blocked,
        "today_spent_eur": round(spent, 4),
        "by_provider": by_provider,
        "budget": get_budget(db),
    }
