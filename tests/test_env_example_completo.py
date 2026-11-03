"""NN-114 / F4 — La plantilla de entorno tiene que estar completa.

`.env.example` es la documentación ejecutable de la configuración. Si el
backend añade una variable y la plantilla no la recoge, quien instala el
proyecto no tiene forma de saber que existe.

Este test recorre los campos de `Settings` y comprueba que cada uno aparece en
`.env.example` (como variable si es útil, o comentado si es opcional). Además
comprueba que la plantilla **no** trae valores reales.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
EJEMPLO = RAIZ / ".env.example"


def _campos_de_settings() -> list[str]:
    from neuralnews.config import Settings

    return sorted(Settings.model_fields.keys())


def _lineas_de_la_plantilla() -> list[str]:
    return EJEMPLO.read_text(encoding="utf-8").splitlines()


def test_la_plantilla_de_entorno_existe() -> None:
    assert EJEMPLO.exists(), "falta .env.example"


@pytest.mark.parametrize("campo", _campos_de_settings())
def test_toda_variable_del_backend_aparece_en_la_plantilla(campo: str) -> None:
    """Cada `Settings.<campo>` se lee de `NEURAL_<CAMPO>`."""
    nombre = f"NEURAL_{campo.upper()}"
    plantilla = "\n".join(_lineas_de_la_plantilla())
    # Tiene que aparecer como variable activa o comentada.
    if not re.search(rf"^#?\s*{re.escape(nombre)}\s*=", plantilla, re.MULTILINE):
        pytest.fail(f"la variable {nombre} (campo «{campo}») no está en .env.example")


def test_la_plantilla_no_trae_valores_reales() -> None:
    """Ninguna clave de proveedor ni contraseña debe venir con valor."""
    for linea in _lineas_de_la_plantilla():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or "=" not in limpia:
            continue
        clave, _, valor = limpia.partition("=")
        clave = clave.strip().upper()
        valor = valor.strip().strip('"').strip("'")
        if clave.endswith("_API_KEY") or clave.endswith("_ACCESS_TOKEN") or clave == "NEURAL_MASTER_KEY":
            assert valor == "", f"{clave} trae un valor en .env.example: no debe"
        if clave == "NEURAL_ADMIN_PASSWORD":
            assert valor in {"", "neural-demo"}, (
                "NEURAL_ADMIN_PASSWORD solo puede venir vacío o con la contraseña de ejemplo"
            )


def test_el_env_real_esta_ignorado_por_git() -> None:
    """Un `.env` con secretos no puede acabar versionado."""
    ignorado = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    entradas = {linea.strip() for linea in ignorado}
    assert ".env" in entradas, ".env no está en .gitignore"
    assert ".env.example" not in entradas, ".env.example SÍ debe estar versionado"
