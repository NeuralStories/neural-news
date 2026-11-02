"""NN-113.14 (auditoría) — La evidencia que cita el plan tiene que existir.

Un plan marcado COMPLETADA puede quedarse desfasado: una fila puede citar un
fichero que se borró después, o un test que ya no existe. Este test ejecuta
`tools/auditar_evidencias.py` y falla si alguna referencia de la columna de
evidencia no se resuelve.

Lo que **no** comprueba (y no se debe presumir): que el comportamiento siga
siendo el de siempre. Eso lo cubren las pruebas y el E2E.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "tools") not in sys.path:
    sys.path.insert(0, str(RAIZ / "tools"))

import auditar_evidencias  # noqa: E402


def test_la_auditoria_no_encuentra_referencias_desfasadas() -> None:
    ok, fuera, inexistentes, _no_rutas = auditar_evidencias.auditar()
    assert ok, "la auditoría no ha comprobado ninguna referencia: el plan no tiene evidencia"
    assert not inexistentes, (
        "referencias desfasadas en el plan maestro:\n  " + "\n  ".join(inexistentes)
    )


def test_el_plan_tiene_evidencia_que_auditar() -> None:
    """Si el plan dejara de citar rutas, la auditoría dejaría de tener sentido."""
    referencias = auditar_evidencias._referencias()
    assert len(referencias) > 50, f"solo {len(referencias)} referencias por auditar"
