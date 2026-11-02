"""Genera el mapa de estados compartido de la web (NN-113.6).

La **fuente de verdad** de los estados y de sus etiquetas en español es
`apps/api/src/neuralnews/states.py`. Antes de este generador la web repetía
el mismo mapa en tres ficheros (`app/noticias/page.tsx`, `app/noticias/[id]/page.tsx`
y `app/fuentes/page.tsx`) y tenía un cuarto mapa distinto en
`features/studio/components/DossierPanel.tsx` (con dos estados que no existen
en el backend: `CONFIRMED` y `DESACTUALIZADA`). Cuatro definiciones que pueden
divergir; dos ya lo habían hecho.

Uso:
    python tools/generate_estados.py           # escribe el fichero
    python tools/generate_estados.py --check   # sólo comprueba (para CI)

El fichero generado (`apps/web/lib/estados.generado.ts`) **no se edita a mano**:
`tests/test_estados_compartidos.py` falla si se queda desfasado.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API_SRC = RAIZ / "apps" / "api" / "src"
DESTINO = RAIZ / "apps" / "web" / "lib" / "estados.generado.ts"

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from neuralnews import states  # noqa: E402  (la ruta se ajusta arriba)

CABECERA = """// GENERADO POR tools/generate_estados.py — NO EDITAR A MANO.
//
// La fuente de verdad es `apps/api/src/neuralnews/states.py`.
// Regenerar: `python tools/generate_estados.py`
// Comprobar (CI): `python tools/generate_estados.py --check`
"""


def _constante(nombre: str, valores: tuple[str, ...] | list[str]) -> str:
    cuerpo = ", ".join(f'"{v}"' for v in valores)
    return f"export const {nombre} = [{cuerpo}] as const;\n"


def _mapa(nombre: str, etiquetas: dict[str, str]) -> str:
    lineas = ",\n".join(f'  {clave}: "{valor}"' for clave, valor in etiquetas.items())
    return f"export const {nombre}: Record<string, string> = {{\n{lineas}\n}};\n"


def generar() -> str:
    partes: list[str] = [CABECERA]

    partes.append(
        "\n// --- Estados ---------------------------------------------------------------\n\n"
    )
    partes.append(_constante("ESTADOS_FUENTE", states.SOURCE_STATES))
    partes.append(_constante("ESTADOS_NOTICIA", states.STORY_STATES))
    partes.append(_constante("ESTADOS_TRABAJO", states.JOB_STATES))
    partes.append(_constante("ESTADOS_PAQUETE", states.PACKAGE_STATES))

    partes.append(
        "\n// --- Etiquetas en español ---------------------------------------------------\n\n"
    )
    partes.append(_mapa("ETIQUETA_FUENTE", states.SOURCE_LABELS))
    partes.append(_mapa("ETIQUETA_NOTICIA", states.STORY_LABELS))
    partes.append(_mapa("ETIQUETA_TRABAJO", states.JOB_LABELS))
    partes.append(_mapa("ETIQUETA_PAQUETE", states.PACKAGE_LABELS))
    partes.append(_mapa("ETIQUETA_APROBACION", states.APPROVAL_LABELS))
    partes.append(_mapa("ETIQUETA_TIPO_CONTENIDO", states.CONTENT_TYPE_LABELS))
    partes.append(_mapa("ETIQUETA_VERIFICACION", states.CLAIM_VERIFICATION_LABELS))
    partes.append(_mapa("ETIQUETA_TIPO_AFIRMACION", states.CLAIM_KIND_LABELS))

    return "".join(partes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: sale con error si el fichero generado está desfasado.",
    )
    args = parser.parse_args()

    contenido = generar()
    if args.check:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != contenido:
            print(
                f"DESFASADO: {DESTINO} no coincide con el backend.\n"
                "Ejecuta: python tools/generate_estados.py"
            )
            return 1
        print(f"OK: {DESTINO.name} está al día.")
        return 0

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(contenido, encoding="utf-8")
    print(f"Escrito: {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
