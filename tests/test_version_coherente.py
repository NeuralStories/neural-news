"""F4 — La versión de la beta tiene que ser la misma en todas partes.

La versión aparece en cuatro sitios (paquete de la web, `pyproject.toml`,
`__version__` del backend y la constante de la web) y además viaja al contrato
OpenAPI y al endpoint de salud. Si uno se queda atrás, la beta dice dos
versiones distintas: este test lo impide.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VERSION_ESPERADA = "1.0.0-beta.1"


def _version_del_backend() -> str:
    texto = (RAIZ / "apps" / "api" / "src" / "neuralnews" / "__init__.py").read_text(
        encoding="utf-8"
    )
    coincidencia = re.search(r'__version__\s*=\s*"([^"]+)"', texto)
    assert coincidencia, "no se encuentra __version__ en el backend"
    return coincidencia.group(1)


def _version_del_pyproject() -> str:
    texto = (RAIZ / "apps" / "api" / "pyproject.toml").read_text(encoding="utf-8")
    coincidencia = re.search(r'^version\s*=\s*"([^"]+)"', texto, re.MULTILINE)
    assert coincidencia, "no se encuentra version en pyproject.toml"
    return coincidencia.group(1)


def _version_de_la_web() -> str:
    datos = json.loads((RAIZ / "apps" / "web" / "package.json").read_text(encoding="utf-8"))
    return datos["version"]


def _version_de_la_web_visible() -> str:
    texto = (RAIZ / "apps" / "web" / "lib" / "version.ts").read_text(encoding="utf-8")
    coincidencia = re.search(r'VERSION\s*=\s*"([^"]+)"', texto)
    assert coincidencia, "no se encuentra VERSION en apps/web/lib/version.ts"
    return coincidencia.group(1)


def test_la_version_esperada_es_la_de_la_beta() -> None:
    assert VERSION_ESPERADA == "1.0.0-beta.1"


def test_todos_los_sitios_declaran_la_misma_version() -> None:
    versiones = {
        "apps/api/src/neuralnews/__init__.py": _version_del_backend(),
        "apps/api/pyproject.toml": _version_del_pyproject(),
        "apps/web/package.json": _version_de_la_web(),
        "apps/web/lib/version.ts": _version_de_la_web_visible(),
    }
    distintas = {k: v for k, v in versiones.items() if v != VERSION_ESPERADA}
    assert not distintas, f"la versión no coincide en: {distintas}"


def test_el_contrato_openapi_publica_la_version() -> None:
    """`docs/openapi.json` se genera desde la aplicación: si no coincide, está viejo."""
    esquema = json.loads((RAIZ / "docs" / "openapi.json").read_text(encoding="utf-8"))
    assert esquema["info"]["version"] == VERSION_ESPERADA, (
        "docs/openapi.json no refleja la versión de la beta: "
        "regenéralo con python tools/exportar_openapi.py"
    )


def test_el_health_publica_la_version() -> None:
    """El endpoint de salud dice la versión: la UI y las pruebas la leen."""
    from neuralnews.main import app

    cliente = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(app)
    respuesta = cliente.get("/api/v1/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["version"] == VERSION_ESPERADA


def test_el_changelog_tiene_la_entrada_de_la_beta() -> None:
    changelog = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{VERSION_ESPERADA}]" in changelog, "el CHANGELOG no tiene la entrada de la beta"
