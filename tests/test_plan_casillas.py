"""El plan con casillas (`PLAN.md`) no puede desfasarse del plan maestro.

`supervisor.sh` valida el proyecto con `grep -q "\\[ \\]" docs/agente/PLAN.md`: si el fichero no
refleja el estado real, el supervisor o bien da el proyecto por terminado antes de tiempo o bien
relanza sin parar. Este test lo evita.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "tools") not in sys.path:
    sys.path.insert(0, str(RAIZ / "tools"))

import generar_plan_casillas  # noqa: E402

PLAN = RAIZ / "docs" / "agente" / "PLAN.md"
MAESTRO = RAIZ / "docs" / "agente" / "PLAN_MAESTRO.md"


def test_plan_con_casillas_esta_al_dia() -> None:
    assert PLAN.exists(), "Falta docs/agente/PLAN.md (lo usa supervisor.sh)"
    assert PLAN.read_text(encoding="utf-8") == generar_plan_casillas.generar(), (
        "PLAN.md está desfasado. Regenera: python tools/generar_plan_casillas.py"
    )


def test_cada_tarea_del_plan_maestro_tiene_su_casilla() -> None:
    ids_maestro = set(re.findall(r"^\|\s*(NN-[\w.\-]+)\s*\|", MAESTRO.read_text(encoding="utf-8"), re.M))
    ids_casillas = set(re.findall(r"^- \[[ x]\] \*\*(NN-[\w.\-]+)\*\*", PLAN.read_text(encoding="utf-8"), re.M))
    assert ids_maestro == ids_casillas, (
        f"Faltan o sobran tareas: {sorted(ids_maestro ^ ids_casillas)}"
    )


def test_no_hay_casillas_pendientes_while_todo_este_completado() -> None:
    """El supervisor da el proyecto por terminado solo si no queda ninguna `[ ]`."""
    pendientes = [
        linea
        for linea in PLAN.read_text(encoding="utf-8").splitlines()
        if linea.startswith("- [ ]")
    ]
    assert not pendientes, pendientes
