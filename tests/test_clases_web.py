"""NN-113.9 — Lint de clases inexistentes.

Una clase propia mal escrita **no da error en ninguna parte**: ni TypeScript,
ni ESLint, ni el navegador. Simplemente no se aplica. Así se colaron
`scrollbar-none` y `studio-root`, que se usaban en la web pero no existían en
`apps/web/app/globals.css`.

Este test ejecuta el comprobador (`tools/check_clases.py`) y falla si alguna
clase propia se usa sin estar definida.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "tools") not in sys.path:
    sys.path.insert(0, str(RAIZ / "tools"))

import check_clases  # noqa: E402


def test_toda_clase_propia_usada_existe() -> None:
    faltantes = check_clases.comprobar()
    assert not faltantes, (
        "Clases propias usadas pero no definidas en apps/web/app/globals.css:\n  "
        + "\n  ".join(faltantes)
    )


def test_el_comprobador_detecta_una_clase_inventada() -> None:
    """El comprobador tiene que ser capaz de fallar (si no, no vigila nada)."""
    definidas = check_clases.clases_definidas()
    assert "scrollbar-none" in definidas, "scrollbar-none debe estar definida"
    assert "studio-root" in definidas, "studio-root debe estar definida"
    assert "clase-que-no-existe" not in definidas
