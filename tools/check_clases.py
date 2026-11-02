"""Comprueba que las clases propias de la web **existen** (NN-113.9).

La web usa clases de Tailwind (que no viven en este repositorio) y unas pocas
clases propias definidas en `apps/web/app/globals.css`. El problema: una clase
propia mal escrita no da error en ninguna parte — ni TypeScript, ni ESLint, ni
el navegador: simplemente no se aplica. Así se colaron dos:

  - `scrollbar-none`, usada en la navegación del Studio y **sin definir**
    (la barra de desplazamiento aparecía en Chromium);
  - `studio-root`, usada como contenedor del Studio y **sin definir**
    (el envoltorio no tenía altura y la raíz del Studio no crecía).

Este script vigila **sólo** las familias de clases propias del proyecto
(`badge-`, `btn-`, `studio-`, `scrollbar-` y las clases sueltas `card`, `input`,
`table-base`): si se usa una clase de esas familias y no está definida en
`globals.css`, el script falla.

Uso:
    python tools/check_clases.py           # informa y sale con error si falta algo
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"
CSS = WEB / "app" / "globals.css"

# Familias de clases propias del proyecto: el prefijo basta para suspectar.
FAMILIAS = ("badge-", "btn-", "studio-", "scrollbar-")
# Clases propias sueltas (sin familia).
SUELTAS = ("card", "input", "table-base", "badge", "btn")

# Sistema visual (NN-113.12): cada componente tiene una firma de utilidades.
# Si una composición en línea vuelve a aparecer, es una reimplementación del
# componente y hay que usar la clase del sistema.
SIGNATURAS = (
    ("card", ("rounded-lg", "border-neutral-800", "bg-neutral-900", "p-4"), ()),
    ("card-compact", ("rounded-lg", "border-neutral-800", "bg-neutral-900", "p-3"), ()),
    ("card-quiet", ("rounded-lg", "border-neutral-800", "bg-neutral-950", "p-3"), ()),
    ("input-compact", ("bg-neutral-950", "border-neutral-800", "rounded", "p-2"), ()),
    ("panel-header", ("justify-between", "pb-3", "border-b"), ()),
    ("modal-actions", ("justify-end", "gap-2", "border-t"), ()),
    ("inset", ("bg-neutral-950", "border-neutral-800/60"), ()),
    ("table-wrap", ("overflow-x-auto", "rounded-lg", "border-neutral-800"), ()),
    ("btn-sm", ("bg-neutral-800", "hover:bg-neutral-700", "border-neutral-700", "py-1.5"), ()),
)

# `className="..."` y `className={`... ${x} ...`}`.
RE_CLASSE = re.compile(r"className\s*=\s*(?:\"([^\"]*)\"|\{`([^`]*)`\})")
RE_INTERPOLACION = re.compile(r"\$\{[^}]*\}")


def clases_definidas() -> set[str]:
    """Clases declaradas en `globals.css`."""
    texto = CSS.read_text(encoding="utf-8")
    return set(re.findall(r"^\.([A-Za-z0-9_-]+)", texto, re.MULTILINE))


def clases_usadas() -> dict[str, list[str]]:
    """Clases propias usadas en la web → ficheros donde aparecen."""
    usadas: dict[str, list[str]] = {}
    for fichero in WEB.rglob("*"):
        if fichero.suffix not in {".tsx", ".ts"}:
            continue
        if "node_modules" in fichero.parts or ".next" in fichero.parts:
            continue
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        for literal, plantilla in RE_CLASSE.findall(texto):
            bruto = literal or plantilla
            if not bruto:
                continue
            estatico = RE_INTERPOLACION.sub(" ", bruto)
            for token in estatico.split():
                if token.startswith(FAMILIAS) or token in SUELTAS:
                    usadas.setdefault(token, []).append(
                        str(fichero.relative_to(RAIZ)).replace("\\", "/")
                    )
    return usadas


def comprobar() -> list[str]:
    """Devuelve la lista de clases propias usadas y **no** definidas."""
    definidas = clases_definidas()
    usadas = clases_usadas()
    return [
        f"{clase} (usada en {', '.join(sorted(set(ficheros)))})"
        for clase, ficheros in sorted(usadas.items())
        if clase not in definidas
    ]


# Utilidades de maquetación: si están, la composición es el componente **más**
# algo (un contenedor, una rejilla): no es una reimplementación del componente.
MAQUETACION = (
    "flex", "grid", "inline-flex", "w-full", "h-full", "items-", "justify-",
    "aspect-", "overflow-", "pl-", "pr-", "space-", "gap-", "absolute",
    "sticky", "fixed", "relative", "max-w-", "min-h-", "col-span", "row-span",
)


def reimplementaciones_en_linea() -> list[str]:
    """Composiciones que reimplementan en línea un componente del sistema."""
    problemas = []
    for fichero in WEB.rglob("*.tsx"):
        if "node_modules" in fichero.parts or ".next" in fichero.parts:
            continue
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        for literal, plantilla in RE_CLASSE.findall(texto):
            bruto = literal or plantilla
            if not bruto:
                continue
            tokens = set(RE_INTERPOLACION.sub(" ", bruto).split())
            if any(any(t.startswith(m) for m in MAQUETACION) for t in tokens):
                continue  # componente + maquetación: no es una reimplementación
            for clase, obligatorias, cualquiera in SIGNATURAS:
                if clase in tokens:
                    continue
                if all(t in tokens for t in obligatorias) and (
                    not cualquiera or any(t in tokens for t in cualquiera)
                ):
                    problemas.append(
                        f"{fichero.relative_to(RAIZ).as_posix()} — "
                        f"«{bruto.strip()[:70]}» reimplementa «{clase}»: usa la clase del sistema"
                    )
    return problemas


def main() -> int:
    # La consola de Windows puede ir en cp1252: se fuerza UTF-8 con sustitución
    # para que un acento no rompa la salida (hallazgo B19, mismo origen).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover - stdout sin reconfigure
        pass
    faltantes = comprobar()
    reimplementaciones = reimplementaciones_en_linea()
    for linea in reimplementaciones:
        print(f"REIMPLEMENTACIÓN  {linea}")
    if faltantes:
        print("Clases propias usadas pero NO definidas en app/globals.css:")
        for linea in faltantes:
            print(f"  - {linea}")
        print("\nCorrige el nombre o define la clase en apps/web/app/globals.css.")
    print(
        f"OK: todas las clases propias usadas están definidas "
        f"({len(clases_usadas())} revisadas); "
        f"{len(reimplementaciones)} reimplementaciones en línea."
    )
    return 1 if (faltantes or reimplementaciones) else 0


if __name__ == "__main__":
    raise SystemExit(main())
