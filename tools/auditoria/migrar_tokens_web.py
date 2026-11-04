"""Migración mecánica del Studio y los componentes al sistema visual.

Sustituye las classes del diseño viejo por las del sistema:

    rounded-lg            -> rounded-md      (radios cortos)
    text-white            -> text-ink       (visible en tema claro)
    shadow-lg             -> shadow-sm
    gradiente de acento   -> sólido con tinte de token
    rounded-xl            -> rounded-md

Y elimina los **spinners**: el icono de «actualizar» no gira; el estado se ve
en la etiqueta del botón («actualizar» → «leyendo…»).

El script es idempotente: se puede volver a ejecutar sin efectos.
"""
from __future__ import annotations

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2] / "apps" / "web"

SUSTITUCIONES = [
    ("rounded-lg", "rounded-md"),
    ("rounded-xl", "rounded-md"),
    ("text-white", "text-ink"),
    ("shadow-lg", "shadow-sm"),
    (
        "bg-gradient-to-r from-sky-500 to-sky-600 hover:from-sky-400 hover:to-sky-500",
        "bg-info/20 text-info hover:bg-info/30",
    ),
]

# El icono de recarga no gira: un spinner es un indicador de carga genérico y
# el sistema lo prohíbe. La etiqueta del botón ya dice «leyendo…».
SPINNERS = [
    ' className={cargando ? "animate-spin" : undefined}',
    ' className={actualizando ? "animate-spin" : undefined}',
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    totales: dict[str, int] = {}
    tocados = 0
    for fichero in sorted(RAIZ.rglob("*.tsx")):
        texto = fichero.read_text(encoding="utf-8")
        original = texto
        for viejo, nuevo in SUSTITUCIONES:
            cantidad = texto.count(viejo)
            if cantidad:
                totales[viejo] = totales.get(viejo, 0) + cantidad
            texto = texto.replace(viejo, nuevo)
        for spinner in SPINNERS:
            cantidad = texto.count(spinner)
            if cantidad:
                totales["animate-spin"] = totales.get("animate-spin", 0) + cantidad
            texto = texto.replace(spinner, "")
        if texto != original:
            fichero.write_text(texto, encoding="utf-8", newline="\n")
            tocados += 1
    for clave, valor in sorted(totales.items()):
        print(f"{valor:5d}  {clave}")
    print(f"\n{tocados} fichero(s) actualizado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
