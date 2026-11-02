"""Detector de contradicciones de cifras (NN-117.7).

Port del módulo `app/domain/contradictions.py` del hermano congelado
(`archive/neuralnews-20261101`).

Regla conservadora: dos afirmaciones de la misma historia que citan la **misma**
magnitud (misma unidad y palabras comunes) con valores **distintos** se
proponen como contradictorias.

**Nunca cambia estados por su cuenta**: devuelve la propuesta (`action:
"PROPOSED"`) y es una persona quien decide. Una cifra coincidente no
«verifica» nada, y una contradicción detectada no invalida la afirmación sin
revisión humana: el estado que se propone es una sugerencia, no un hecho.

Adaptación al vocabulario de este producto: el estado propuesto es
`CONTRADICTED` (el que usa `Claim.verification_status` aquí), no `DISPUTED`.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Claim

_NUMERO = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(ms|s|%|€|\$|USD|EUR|GB|MB|KB|tokens|ppm|wpm|k|millones)?",
    re.IGNORECASE,
)


def _cifras(texto: str) -> list[tuple[float, str]]:
    salida: list[tuple[float, str]] = []
    for coincidencia in _NUMERO.finditer(texto):
        crudo = coincidencia.group(1).replace(",", ".")
        unidad = (coincidencia.group(2) or "").lower()
        salida.append((float(crudo), unidad))
    return salida


def _palabras(texto: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúüñ]{4,}", texto.lower()))


def detectar_conflictos(afirmaciones: list[Claim]) -> list[dict]:
    """Propone contradicciones entre cifras de la misma historia. No cambia nada."""
    conflictos: list[dict] = []
    for i in range(len(afirmaciones)):
        for j in range(i + 1, len(afirmaciones)):
            a, b = afirmaciones[i], afirmaciones[j]
            cifras_a, cifras_b = _cifras(a.statement), _cifras(b.statement)
            comunes = _palabras(a.statement) & _palabras(b.statement)
            if not comunes or not cifras_a or not cifras_b:
                continue
            unidades_a = {u for _, u in cifras_a}
            unidades_b = {u for _, u in cifras_b}
            if unidades_a != unidades_b or not unidades_a:
                continue
            valores_a = sorted({v for v, _ in cifras_a})
            valores_b = sorted({v for v, _ in cifras_b})
            if valores_a == valores_b:
                continue
            conflictos.append(
                {
                    "claim_a": str(a.id),
                    "claim_b": str(b.id),
                    "text_a": a.statement,
                    "text_b": b.statement,
                    "figures_a": valores_a,
                    "figures_b": valores_b,
                    "suggested_status": "CONTRADICTED",
                    "action": "PROPOSED",  # requiere revisión humana
                }
            )
    return conflictos


def conflictos_de_historia(db: Session, story_id: int) -> list[dict]:
    """Conflictos propuestos de las afirmaciones de una historia."""
    afirmaciones = db.scalars(select(Claim).where(Claim.story_id == story_id)).all()
    return detectar_conflictos(list(afirmaciones))
