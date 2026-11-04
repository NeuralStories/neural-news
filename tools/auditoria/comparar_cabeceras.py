"""Compara las cabeceras de tabla de las vistas migradas con las del tag.

El E2E del repositorio comprueba cabeceras concretas («Puntuación», «Fecha»,
«Verificación»…): si una migración las renombra, la prueba falla. Este script
lista la diferencia para poder alinearlas.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

VISTAS = [
    "apps/web/app/noticias/page.tsx",
    "apps/web/app/fuentes/page.tsx",
    "apps/web/app/lotes/page.tsx",
    "apps/web/app/noticias/[id]/page.tsx",
]


def cabeceras_viejas(ruta: str) -> list[str]:
    salida = subprocess.run(
        ["git", "-C", str(RAIZ), "show", f"HEAD:{ruta}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    found = re.findall(r"<th[^>]*>(.*?)</th>", salida, re.S)
    return [re.sub(r"<[^>]+>", "", c).strip() for c in found if c.strip()]


def cabeceras_nuevas(ruta: str) -> list[str]:
    texto = (RAIZ / ruta).read_text(encoding="utf-8")
    found = re.findall(r'cabecera:\s*"([^"]*)"', texto)
    return [c for c in found if c]


def cabeceras_jsx(ruta: str) -> list[str]:
    """Cabeceras escritas como JSX (`<th>Puntuación</th>`)."""
    texto = (RAIZ / ruta).read_text(encoding="utf-8")
    found = re.findall(r"<th[^>]*>([^<{]+)</th>", texto)
    return [c.strip() for c in found if c.strip()]


def main() -> int:
    print(f"{'vista':38} {'antes':38} ahora")
    for ruta in VISTAS:
        antes = cabeceras_viejas(ruta)
        ahora = cabeceras_nuevas(ruta) or cabeceras_jsx(ruta)
        print(f"\n{ruta}")
        print(f"  antes: {antes}")
        print(f"  ahora: {ahora}")
        perdidas = [c for c in antes if c and c not in ahora]
        if perdidas:
            print(f"  !! cabeceras que el E2E puede buscar y ya no existen: {perdidas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
