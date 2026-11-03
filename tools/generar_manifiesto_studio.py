"""Genera el manifiesto de integridad de las fuentes del Studio (NN-113.15).

El «Centro de mantenimiento» (antes `BackupModal`) promete **auditar** las
fuentes del Studio con SHA-256. Para que la promesa sea verdad, el manifiesto
tiene que salir de los **ficheros reales** del repositorio, no de una lista
escrita a mano.

Este generador recorre `apps/web/features/studio/**`, calcula el SHA-256 real
de cada fichero y escribe `features/studio/data/manifiestoStudio.generado.json`.

Uso:
    python tools/generar_manifiesto_studio.py           # escribe el fichero
    python tools/generar_manifiesto_studio.py --check   # sólo comprueba (CI)

`tests/test_manifiesto_studio.py` falla si el manifiesto se queda desfasado:
si alguien toca el código del Studio y no regenera, la interfaz está
declarando hashes que ya no son ciertos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STUDIO = RAIZ / "apps" / "web" / "features" / "studio"
DESTINO = STUDIO / "data" / "manifiestoStudio.generado.json"

# Extensiones que forman parte del código del Studio.
EXTENSIONES = {".ts", ".tsx"}
# Directorios que no son código del producto.
EXCLUIDOS = {"node_modules", ".next", "dist", "coverage", "__pycache__"}


def _sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def collecting() -> list[Path]:
    ficheros = []
    for ruta in STUDIO.rglob("*"):
        if not ruta.is_file() or ruta.suffix not in EXTENSIONES:
            continue
        if any(parte in EXCLUIDOS for parte in ruta.parts):
            continue
        if ruta == DESTINO:
            continue
        ficheros.append(ruta)
    return sorted(ficheros)


def generar() -> str:
    entradas = []
    for ruta in collecting():
        datos = ruta.read_bytes()
        texto = datos.decode("utf-8", errors="replace")
        entradas.append(
            {
                "path": ruta.relative_to(STUDIO).as_posix(),
                "lines": texto.count("\n") + (1 if texto and not texto.endswith("\n") else 0),
                "chars": len(texto),
                "sha256": _sha256(datos),
            }
        )

    manifiesto = {
        "manifestVersion": "1.0",
        "generatedBy": "tools/generar_manifiesto_studio.py",
        "scope": "apps/web/features/studio",
        "totalFiles": len(entradas),
        "totalLines": sum(e["lines"] for e in entradas),
        "totalChars": sum(e["chars"] for e in entradas),
        "files": entradas,
    }
    return json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: sale con error si el manifiesto está desfasado.",
    )
    args = parser.parse_args()

    contenido = generar()
    if args.check:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != contenido:
            print(
                f"DESFASADO: {DESTINO.relative_to(RAIZ)} no coincide con el código del Studio.\n"
                "Ejecuta: python tools/generar_manifiesto_studio.py"
            )
            return 1
        print("OK: el manifiesto del Studio está al día.")
        return 0

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": en Windows, `write_text()` escribe CRLF y el artefacto
    # dejaría de coincidir con los bytes que se versionan (LF), con lo que el
    # test de «artefacto al día» falla en un clon limpio (hallazgo de la
    # auditoría A1).
    DESTINO.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"Escrito: {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
