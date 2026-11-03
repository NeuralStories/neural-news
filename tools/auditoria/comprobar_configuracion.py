"""Auditoría A2.3 y A2.4 — configuración y versión coherentes.

**A2.3** `.env.example` debe contener **todas** las variables que el código lee
de verdad (y ninguna de más). Se busca en:

  - Python: `os.environ.get(...)`, `os.getenv(...)`, `os.environ[...]` y los
    campos de `Settings` (pydantic-settings con prefijo `NEURAL_`).
  - Web: `process.env.X` y `process.env["X"]`.

**A2.4** la versión de la beta debe ser idéntica en `package.json`, `pyproject.toml`,
`__version__`, `lib/version.ts`, `docs/openapi.json` y en la respuesta de `/health`.

Uso:
    python tools/auditoria/comprobar_configuracion.py [--sin-health]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
VERSION_ESPERADA = "1.0.0-beta.1"

RE_PY_GET = re.compile(r"os\.environ\.get\(\s*[\"']([A-Z0-9_]+)[\"']")
RE_PY_GETENV = re.compile(r"os\.getenv\(\s*[\"']([A-Z0-9_]+)[\"']")
RE_PY_ITEM = re.compile(r"os\.environ\[\s*[\"']([A-Z0-9_]+)[\"']\s*\]")
RE_JS_DOT = re.compile(r"process\.env\.([A-Z0-9_]+)")
RE_JS_CORCHETE = re.compile(r"process\.env\[\s*[\"']([A-Z0-9_]+)[\"']\s*\]")
RE_CAMPO_SETTINGS = re.compile(r"^\s{4}([a-z_][a-z0-9_]*)\s*:\s*.*=\s*Field\(", re.MULTILINE)
RE_EJEMPLO = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)

# Variables de Node que no son configuración del producto.
IGNORAR_JS = {"NODE_ENV", "NEXT_PUBLIC_API_URL"}


def _ficheros(patron: str) -> list[Path]:
    return [
        p
        for p in RAIZ.glob(patron)
        if p.is_file() and "node_modules" not in p.parts and ".next" not in p.parts
    ]


def variables_del_codigo() -> dict[str, list[str]]:
    usadas: dict[str, list[str]] = {}

    def anota(nombre: str, donde: str) -> None:
        usadas.setdefault(nombre, [])
        if donde not in usadas[nombre]:
            usadas[nombre].append(donde)

    for fichero in _ficheros("apps/api/src/**/*.py"):
        texto = fichero.read_text(encoding="utf-8", errors="ignore")
        relativo = fichero.relative_to(RAIZ).as_posix()
        for patron in (RE_PY_GET, RE_PY_GETENV, RE_PY_ITEM):
            for nombre in patron.findall(texto):
                anota(nombre, relativo)

    for fichero in _ficheros("apps/api/src/neuralnews/config.py"):
        texto = fichero.read_text(encoding="utf-8", errors="ignore")
        relativo = fichero.relative_to(RAIZ).as_posix()
        for campo in RE_CAMPO_SETTINGS.findall(texto):
            anota(f"NEURAL_{campo.upper()}", relativo)

    for patron_base in ("apps/web/**/*.ts", "apps/web/**/*.tsx", "apps/web/**/*.mjs", "scripts/*.mjs"):
        for fichero in _ficheros(patron_base):
            texto = fichero.read_text(encoding="utf-8", errors="ignore")
            relativo = fichero.relative_to(RAIZ).as_posix()
            for patron in (RE_JS_DOT, RE_JS_CORCHETE):
                for nombre in patron.findall(texto):
                    if nombre in IGNORAR_JS:
                        continue
                    anota(nombre, relativo)

    return usadas


def variables_de_la_plantilla() -> set[str]:
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    return set(RE_EJEMPLO.findall(texto))


def versiones() -> dict[str, str]:
    pkg = json.loads((RAIZ / "apps" / "web" / "package.json").read_text(encoding="utf-8"))
    pyproject = (RAIZ / "apps" / "api" / "pyproject.toml").read_text(encoding="utf-8")
    init = (RAIZ / "apps" / "api" / "src" / "neuralnews" / "__init__.py").read_text(encoding="utf-8")
    web_version = (RAIZ / "apps" / "web" / "lib" / "version.ts").read_text(encoding="utf-8")
    openapi = json.loads((RAIZ / "docs" / "openapi.json").read_text(encoding="utf-8"))
    return {
        "apps/web/package.json": pkg["version"],
        "apps/api/pyproject.toml": (re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M) or [None, "?"])[1],
        "neuralnews/__init__.py": (re.search(r'__version__\s*=\s*"([^"]+)"', init) or [None, "?"])[1],
        "apps/web/lib/version.ts": (re.search(r'VERSION\s*=\s*"([^"]+)"', web_version) or [None, "?"])[1],
        "docs/openapi.json": openapi["info"]["version"],
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-health", action="store_true", help="No consultar /health.")
    args = parser.parse_args()

    problemas: list[str] = []

    # --- A2.3: variables de entorno -----------------------------------------
    usadas = variables_del_codigo()
    plantilla = variables_de_la_plantilla()
    faltan = sorted(nombre for nombre in usadas if nombre not in plantilla)
    sobran = sorted(nombre for nombre in plantilla if nombre not in usadas)
    for nombre in faltan:
        problemas.append(f"variable que el código lee y la plantilla NO tiene: {nombre} ({usadas[nombre][0]})")
    for nombre in sobran:
        problemas.append(f"variable en la plantilla que el código no lee: {nombre}")

    # --- A2.4: versión ------------------------------------------------------
    encontradas = versiones()
    for donde, valor in encontradas.items():
        if valor != VERSION_ESPERADA:
            problemas.append(f"versión distinta en {donde}: {valor} (esperada {VERSION_ESPERADA})")

    if not args.sin_health:
        import urllib.request

        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=5) as respuesta:
                salud = json.loads(respuesta.read().decode("utf-8"))
            if salud.get("version") != VERSION_ESPERADA:
                problemas.append(f"versión distinta en /health: {salud.get('version')}")
        except Exception as exc:  # noqa: BLE001 — si no está en marcha, no es un fallo de versión
            print(f"AVISO: /health no responde ({exc}); la versión en vivo queda sin comprobar.")

    for linea in problemas:
        print(f"FALLA  {linea}")
    print(
        f"\nA2.3: {len(usadas)} variables leídas por el código, {len(plantilla)} en la plantilla. "
        f"A2.4: {len(encontradas)} sitios de versión comprobados."
    )
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
