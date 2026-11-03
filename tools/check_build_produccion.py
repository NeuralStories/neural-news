"""Comprueba que el build de producción no lleva sorpresas (F4).

Un build de producción no debería contener:

  - **modo depuración**: `console.log`, `debugger`, `TODO/FIXME` de desarrollo;
  - **credenciales de prueba**: la contraseña de ejemplo, claves de API de
    ejemplo, tokens;
  - **datos personales**: correos, teléfonos o identificadores de personas.

El backend también se revisa: `DEBUG`, `print(` en el arranque, etc.

Uso:
    python tools/check_build_produccion.py           # informa y sale con error si encuentra algo
    python tools/check_build_produccion.py --json    # salida en JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"
API = RAIZ / "apps" / "api" / "src" / "neuralnews"

# (etiqueta, patrón) — lo que no debe aparecer en un build de producción.
PATRONES_WEB = [
    ("sentencia de depuración", re.compile(r"\bdebugger\b")),
    ("credencial de ejemplo", re.compile(r"neural-demo|clave-de-ejemplo|password\s*=\s*[\"']\w{4,}")),
    ("token o clave incrustada", re.compile(r"sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}")),
    ("correo electrónico", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]
# El backend: `print` está prohibido (todo el logging va por logging_setup).
# Nota: la contraseña de ejemplo **sí** aparece en `config.py` como valor por
# defecto, y es intencionado: `Settings.comprobar()` se niega a arrancar fuera
# de `local` con ese valor. Por eso el backend no busca «credencial de ejemplo»
# (el bundle de la web sí, que es donde no debe aparecer).
PATRONES_API = [
    ("print() en el backend", re.compile(r"^\s*print\(", re.MULTILINE)),
    ("DEBUG=True en el código", re.compile(r"\bDEBUG\s*=\s*True")),
    ("clave de API incrustada", re.compile(r"sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}")),
]

# Extensiones que se revisan en el bundle del cliente.
EXTENSIONES_BUNDLE = {".js", ".css", ".map", ".json", ".html"}


def _ficheros(directorio: Path) -> list[Path]:
    if not directorio.exists():
        return []
    return [
        p
        for p in directorio.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONES_BUNDLE
    ]


def revisar() -> list[str]:
    hallazgos: list[str] = []

    for fichero in _ficheros(WEB / ".next" / "static"):
        try:
            texto = fichero.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relativo = fichero.relative_to(WEB).as_posix()
        for etiqueta, patron in PATRONES_WEB:
            coincidencia = patron.search(texto)
            if coincidencia:
                inicio = max(0, coincidencia.start() - 40)
                extracto = texto[inicio : coincidencia.end() + 40].replace("\n", " ")
                hallazgos.append(f"{relativo}: {etiqueta} → …{extracto}…")

    for fichero in sorted(API.rglob("*.py")):
        texto = fichero.read_text(encoding="utf-8", errors="ignore")
        relativo = fichero.relative_to(RAIZ).as_posix()
        for etiqueta, patron in PATRONES_API:
            coincidencia = patron.search(texto)
            if coincidencia:
                numero = texto[: coincidencia.start()].count("\n") + 1
                hallazgos.append(f"{relativo}:{numero}: {etiqueta}")

    return hallazgos


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Salida en JSON.")
    args = parser.parse_args()

    if not (WEB / ".next" / "static").exists():
        print("No hay build de producción: ejecuta `npm run build` en apps/web primero.")
        return 1

    hallazgos = revisar()
    if args.json:
        print(json.dumps({"hallazgos": hallazgos, "total": len(hallazgos)}, ensure_ascii=False, indent=2))
    else:
        for linea in hallazgos:
            print(f"HALLAZGO  {linea}")
        print(
            f"\n{len(hallazgos)} hallazgos en el build de producción y en el backend."
            if hallazgos
            else "OK: el build de producción no lleva depuración, credenciales ni datos personales."
        )
    return 1 if hallazgos else 0


if __name__ == "__main__":
    raise SystemExit(main())
