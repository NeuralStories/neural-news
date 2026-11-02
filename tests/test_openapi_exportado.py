"""NN-114.4 — El contrato OpenAPI exportado debe coincidir con el servido.

`docs/openapi.json` es el contrato "oficial" de la API: lo consume la web y lo
revisan otros. Si el fichero se queda viejo, el contrato documentado y el que
se sirve difieren sin que nadie se entere.

Este test regenera el contrato desde la aplicación real y lo compara con el
fichero versionado.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "tools") not in sys.path:
    sys.path.insert(0, str(RAIZ / "tools"))

import exportar_openapi  # noqa: E402


def test_el_contrato_exportado_coincide_con_el_servido() -> None:
    exportado = exportar_openapi.DESTINO
    assert exportado.exists(), (
        "Falta docs/openapi.json. Genera el contrato: python tools/exportar_openapi.py"
    )
    assert exportado.read_text(encoding="utf-8") == exportar_openapi.contrato(), (
        "docs/openapi.json está desfasado respecto al contrato servido. "
        "Regenera: python tools/exportar_openapi.py"
    )


def test_el_contrato_expone_las_rutas_principales() -> None:
    import json

    esquema = json.loads(exportar_openapi.DESTINO.read_text(encoding="utf-8"))
    rutas = set(esquema["paths"])
    for ruta in (
        "/api/v1/auth/demo",
        "/api/v1/sources",
        "/api/v1/stories",
        "/api/v1/jobs",
        "/api/v1/provider-status",
        "/api/v1/usage",
    ):
        assert ruta in rutas, f"El contrato no expone {ruta}"
