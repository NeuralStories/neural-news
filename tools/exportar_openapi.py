"""Exporta el contrato OpenAPI y lo verifica contra el servido (NN-114.4).

El contrato de la API es lo que consume la web y lo que se documenta. Si el
fichero exportado se queda viejo, el contrato "oficial" y el que se sirve
difieren sin que nadie se entere. Este script:

  - sin argumentos: escribe `docs/openapi.json` a partir de la aplicación real;
  - con `--check`: **falla** si el fichero exportado no coincide con el que
    sirve la aplicación (se usa en CI).

Uso:
    python tools/exportar_openapi.py
    python tools/exportar_openapi.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API_SRC = RAIZ / "apps" / "api" / "src"
DESTINO = RAIZ / "docs" / "openapi.json"

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

# La configuración exige un entorno explícito: sin él la aplicación no arranca.
os.environ.setdefault("NEURAL_ENV", "local")

# **Base de datos aislada.** Importar la aplicación aplica las migraciones
# pendientes: si se hiciese contra la base viva, la DDL de SQLite tomaría el
# bloqueo y dejaría **caída la API que esté en marcha** (pasó: el E2E se quedó
# sin servicio). El contrato OpenAPI no depende de los datos, así que se
# exporta contra una base temporal. Para usar la base real a propósito:
# NEURAL_EXPORT_USE_LIVE_DB=1.
if not os.environ.get("NEURAL_EXPORT_USE_LIVE_DB"):
    _temporal = tempfile.mkdtemp(prefix="neuralnews-openapi-")
    os.environ["NEURAL_DATABASE_URL"] = "sqlite:///" + (
        Path(_temporal) / "openapi.db"
    ).as_posix()


def contrato() -> str:
    from neuralnews.main import app

    esquema = app.openapi()
    # Se ordena para que el fichero sea estable entre ejecuciones.
    return json.dumps(esquema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: sale con error si el contrato exportado está desfasado.",
    )
    args = parser.parse_args()

    contenido = contrato()
    if args.check:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != contenido:
            print(
                f"DESFASADO: {DESTINO.relative_to(RAIZ)} no coincide con el contrato servido.\n"
                "Ejecuta: python tools/exportar_openapi.py"
            )
            return 1
        print("OK: el contrato exportado coincide con el servido.")
        return 0

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": en Windows, `write_text()` escribe CRLF y el contrato
    # dejaría de coincidir con los bytes que se versionan (LF) (hallazgo de la
    # auditoría A1).
    DESTINO.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"Escrito: {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
