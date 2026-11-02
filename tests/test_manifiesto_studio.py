"""NN-113.15 — El manifiesto de integridad del Studio no puede mentir.

El «Centro de mantenimiento» muestra el SHA-256 de cada fuente del Studio. Esos
hashes los calcula `tools/generar_manifiesto_studio.py` sobre los ficheros
reales. Si alguien toca el código y no regenera el manifiesto, la interfaz
estaría declarando hashes que ya no son ciertos: este test lo impide.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ / "tools") not in sys.path:
    sys.path.insert(0, str(RAIZ / "tools"))

import generar_manifiesto_studio  # noqa: E402

DESTINO = generar_manifiesto_studio.DESTINO


def test_el_manifiesto_esta_al_dia() -> None:
    actual = DESTINO.read_text(encoding="utf-8")
    esperado = generar_manifiesto_studio.generar()
    assert actual == esperado, (
        "features/studio/data/manifiestoStudio.generado.json está desfasado. "
        "Ejecuta: python tools/generar_manifiesto_studio.py"
    )


def test_el_manifiesto_cubre_las_fuentes_del_studio() -> None:
    manifiesto = json.loads(DESTINO.read_text(encoding="utf-8"))
    rutas = {f["path"] for f in manifiesto["files"]}
    reales = {
        ruta.relative_to(generar_manifiesto_studio.STUDIO).as_posix()
        for ruta in generar_manifiesto_studio.collecting()
    }
    assert reales == rutas, (
        f"Faltan o sobran ficheros en el manifiesto: {sorted(reales ^ rutas)}"
    )
    assert manifiesto["totalFiles"] == len(rutas)
    assert manifiesto["totalFiles"] > 0


def test_los_hashes_del_manifiesto_son_reales() -> None:
    """Se recalcula un hash y se compara con el declarado."""
    import hashlib

    manifiesto = json.loads(DESTINO.read_text(encoding="utf-8"))
    for entrada in manifiesto["files"][:5]:
        ruta = generar_manifiesto_studio.STUDIO / entrada["path"]
        datos = ruta.read_bytes()
        assert hashlib.sha256(datos).hexdigest() == entrada["sha256"], (
            f"El SHA-256 declarado no coincide con el fichero real: {entrada['path']}"
        )
