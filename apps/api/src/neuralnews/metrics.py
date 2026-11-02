"""Métricas y alertas del sistema (NN-115.3 y NN-115.4).

Sin esto, el operador sólo podía ver trabajos sueltos: no había forma de
saber «¿está el sistema sano?» de un vistazo ni de que se-enterase de que la
cola se había parado o de que el presupuesto se estaba agotando.

- **Métricas**: p95 y media de duración, tasa de fallo, profundidad de cola y
  desglose por tipo de trabajo y por motivo normalizado de fallo.
- **Alertas**: cola parada (trabajo en cola que nadie recoge), lease vencido,
  presupuesto al 80 % y fallo repetido del mismo tipo de trabajo.

Todo se calcula **de la base de datos**, no de estado en memoria: así las
métricas sobreviven a un reinicio y funcionan con varios workers.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Job, utcnow
from .services import budget as budget_service

# Un trabajo en cola que nadie recoge en este tiempo significa que el worker
# está parado (o que no hay worker).
MINUTOS_SIN_RECOGER = 5
# Un lease que ha vencido es un trabajo que se quedó a medias.
SEGUNDOS_LEASE_VENCIDO = 120
# Porcentaje de presupuesto consumido a partir del cual se avisa.
UMBRAL_PRESUPUESTO = 0.8
# Número de fallos del mismo tipo a partir del cual se avisa.
FALLOS_REPETIDOS = 3
# Ventana de análisis.
VENTANA_HORAS = 24


def _percentil(datos: list[float], percentil: float) -> float | None:
    """Percentil por rango más cercano (método «nearest rank»)."""
    if not datos:
        return None
    ordenados = sorted(datos)
    indice = max(0, min(len(ordenados) - 1, int(round(percentil / 100 * len(ordenados) + 0.5)) - 1))
    return round(ordenados[indice], 3)


def metricas(db: Session) -> dict:
    """Métricas de los trabajos de la ventana (por defecto, las últimas 24 h)."""
    desde = utcnow() - timedelta(hours=VENTANA_HORAS)
    jobs = db.scalars(select(Job).where(Job.created_at >= desde)).all()

    duraciones = [
        (j.finished_at - j.started_at).total_seconds()
        for j in jobs
        if j.finished_at is not None and j.started_at is not None
    ]
    fallos = [j for j in jobs if j.status == "FAILED"]
    reintentables = [j for j in jobs if j.status == "RETRYABLE_FAILED"]
    terminados_ok = [j for j in jobs if j.status == "DONE"]

    por_tipo: dict[str, int] = {}
    for j in jobs:
        por_tipo[j.type] = por_tipo.get(j.type, 0) + 1

    por_error_kind: dict[str, int] = {}
    for j in fallos:
        clave = j.error_kind or "unknown"
        por_error_kind[clave] = por_error_kind.get(clave, 0) + 1

    cola = db.scalar(
        select(func.count()).select_from(Job).where(Job.status.in_(["QUEUED", "RUNNING"]))
    ) or 0

    total = len(jobs)
    return {
        "ventana_horas": VENTANA_HORAS,
        "jobs_total": total,
        "jobs_terminados_ok": len(terminados_ok),
        "jobs_fallidos": len(fallos),
        "jobs_reintentables": len(reintentables),
        "tasa_fallo": round(len(fallos) / total, 4) if total else 0.0,
        "duracion_media_s": round(sum(duraciones) / len(duraciones), 3) if duraciones else None,
        "p95_duracion_s": _percentil(duraciones, 95),
        "profundidad_cola": int(cola),
        "por_tipo": dict(sorted(por_tipo.items())),
        "por_error_kind": dict(sorted(por_error_kind.items())),
    }


def alertas(db: Session) -> list[dict]:
    """Avisos que el operador tiene que ver: cola parada, lease, presupuesto y fallos."""
    avisos: list[dict] = []
    ahora = utcnow()
    desde = ahora - timedelta(hours=VENTANA_HORAS)

    jobs = db.scalars(select(Job).where(Job.created_at >= desde)).all()

    # 1. Cola parada: hay trabajo en cola y nadie lo ha recogido en N minutos.
    sin_recoger = [
        j
        for j in jobs
        if j.status == "QUEUED" and j.created_at <= ahora - timedelta(minutes=MINUTOS_SIN_RECOGER)
    ]
    if sin_recoger:
        avisos.append(
            {
                "codigo": "cola_parada",
                "severidad": "error",
                "mensaje": (
                    f"Hay {len(sin_recoger)} trabajo(s) en cola sin recoger desde hace más de "
                    f"{MINUTOS_SIN_RECOGER} minutos: el worker puede estar parado."
                ),
                "trabajos": [j.id for j in sin_recoger][:20],
            }
        )

    # 2. Lease vencido: un trabajo en marcha cuyo lease ya expiró.
    leases_vencidos = [
        j
        for j in jobs
        if j.status == "RUNNING" and j.lease_until is not None and j.lease_until <= ahora
    ]
    if leases_vencidos:
        avisos.append(
            {
                "codigo": "lease_vencido",
                "severidad": "aviso",
                "mensaje": (
                    f"{len(leases_vencidos)} trabajo(s) en marcha tienen el lease vencido: "
                    "quedaron a medias y pueden quedar atascados."
                ),
                "trabajos": [j.id for j in leases_vencidos][:20],
            }
        )

    # 3. Presupuesto al 80 % (o agotado).
    uso = budget_service.usage_summary(db)
    limite = float(uso["budget"]["daily_limit_eur"] or 0)
    gastado = float(uso["today_spent_eur"] or 0)
    if limite > 0 and gastado >= limite * UMBRAL_PRESUPUESTO:
        porcentaje = round(gastado / limite * 100, 1)
        avisos.append(
            {
                "codigo": "presupuesto_cercano",
                "severidad": "error" if gastado >= limite else "aviso",
                "mensaje": (
                    f"Presupuesto diario consumido al {porcentaje} % "
                    f"({gastado:.2f} de {limite:.2f} €)."
                ),
            }
        )

    # 4. Fallo repetido del mismo tipo de trabajo.
    por_clave: dict[tuple[str, str], list[Job]] = {}
    for j in jobs:
        if j.status != "FAILED":
            continue
        clave = (j.type, j.error_kind or "unknown")
        por_clave.setdefault(clave, []).append(j)
    for (tipo, motivo), lista in sorted(por_clave.items()):
        if len(lista) >= FALLOS_REPETIDOS:
            avisos.append(
                {
                    "codigo": "fallo_repetido",
                    "severidad": "error",
                    "mensaje": (
                        f"{len(lista)} trabajos de tipo «{tipo}» han fallado con el motivo "
                        f"«{motivo}» en las últimas {VENTANA_HORAS} h."
                    ),
                    "trabajos": [j.id for j in lista][:20],
                }
            )

    return avisos


def estado_operativo(db: Session) -> dict:
    """Métricas y alertas en una sola llamada (lo que consume la página /ops)."""
    return {"metricas": metricas(db), "alertas": alertas(db)}
