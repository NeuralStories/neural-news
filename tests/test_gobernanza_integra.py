"""DEC-01 — La gobernanza que entra en Git llega **intacta**.

`docs/gobernanza/` es evidencia histórica (el plan rector, el registro de
decisiones y la evidencia del port de Flow). Trae su propio manifiesto de
SHA-256 (`MANIFEST_SHA256.json`): si el movimiento al repositorio o una
edición posterior alterase un solo byte, ese manifiesto dejaría de cuadrar y
la evidencia ya no sería creíble.

Este test comprueba los hashes del manifiesto contra los ficheros reales.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
GOBERNANZA = RAIZ / "docs" / "gobernanza"
MANIFIESTO = GOBERNANZA / "MANIFEST_SHA256.json"


def _entradas() -> list[dict]:
    datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    return datos["files"]


def test_el_manifiesto_de_la_gobernanza_existe() -> None:
    assert MANIFIESTO.exists(), "docs/gobernanza/MANIFEST_SHA256.json no está"
    assert GOBERNANZA.is_dir(), "docs/gobernanza no está"


def test_los_hashes_de_la_gobernanza_cuadran() -> None:
    """Cada fichero del manifiesto conserva su SHA-256.

    **Excepciones documentadas.** El manifiesto se selló el 2026-10-30; después
    se actualizaron legítimamente tres ficheros (verificable por su fecha de
    modificación, anterior al traslado de la gobernanza al repositorio):

      - `06_TASKS/BACKLOG.csv` y `06_TASKS/BACKLOG.json`: reconstruidos en la
        Fase 0 (NN-119) el 2026-11-01 a las 22:34.
      - `01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md`: se le añadió
        el riesgo R-26 el 2026-11-01 a las 23:24.

    El manifiesto se conserva **tal cual** (es evidencia histórica): no se
    re-sella para que cuadre, porque eso escondería el cambio.
    """
    excepciones = {
        "06_TASKS/BACKLOG.csv": "reconstruido en la Fase 0 (NN-119) el 2026-11-01",
        "06_TASKS/BACKLOG.json": "reconstruido en la Fase 0 (NN-119) el 2026-11-01",
        "01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md": "riesgo R-26 añadido el 2026-11-01",
    }
    desajustes = []
    for entrada in _entradas():
        ruta = GOBERNANZA / entrada["path"]
        if not ruta.exists():
            desajustes.append(f"{entrada['path']}: no existe")
            continue
        if entrada["path"] in excepciones:
            continue
        datos = ruta.read_bytes()
        if hashlib.sha256(datos).hexdigest() != entrada["sha256"]:
            desajustes.append(f"{entrada['path']}: el hash ya no coincide")
    assert not desajustes, (
        "la evidencia de la gobernanza está alterada:\n  " + "\n  ".join(desajustes)
    )


def test_las_excepciones_del_manifiesto_son_las_documentadas() -> None:
    """Las excepciones son exactamente las tres documentadas, ni una más."""
    excepciones = {
        "06_TASKS/BACKLOG.csv",
        "06_TASKS/BACKLOG.json",
        "01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md",
    }
    import hashlib as _h

    desajustes = set()
    for entrada in _entradas():
        ruta = GOBERNANZA / entrada["path"]
        if not ruta.exists():
            continue
        if _h.sha256(ruta.read_bytes()).hexdigest() != entrada["sha256"]:
            desajustes.add(entrada["path"])
    assert desajustes == excepciones, (
        f"los ficheros que no cuadran han cambiado: {sorted(desajustes ^ excepciones)}"
    )


def test_la_gobernanza_no_trae_artefactos_generados() -> None:
    """Condición de DEC-01: sin node_modules, builds, cachés, .env ni bases."""
    prohibidos = []
    for ruta in GOBERNANZA.rglob("*"):
        if any(parte in {"node_modules", ".next", "dist", "build", "__pycache__", ".pytest_cache"} for parte in ruta.parts):
            prohibidos.append(str(ruta.relative_to(RAIZ)))
        elif ruta.is_file():
            if ruta.name == ".env":
                prohibidos.append(str(ruta.relative_to(RAIZ)))
            elif ruta.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                prohibidos.append(str(ruta.relative_to(RAIZ)))
    assert not prohibidos, "artefactos generados dentro de la gobernanza:\n  " + "\n  ".join(prohibidos)


def test_ningun_fichero_de_la_gobernanza_pasa_de_50_mb() -> None:
    """Condición de DEC-01: ningún fichero de más de 50 MB."""
    limite = 50 * 1024 * 1024
    grandes = [
        f"{ruta.relative_to(RAIZ)} ({ruta.stat().st_size / 1024 / 1024:.1f} MB)"
        for ruta in GOBERNANZA.rglob("*")
        if ruta.is_file() and ruta.stat().st_size > limite
    ]
    assert not grandes, "ficheros de más de 50 MB:\n  " + "\n  ".join(grandes)
