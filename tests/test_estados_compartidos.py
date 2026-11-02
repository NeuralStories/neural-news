"""NN-113.6 — Un solo mapa de estado, compartido y generado.

Antes de este trabajo la web repetía el mismo mapa estado→insignia en tres
ficheros (`app/noticias/page.tsx`, `app/noticias/[id]/page.tsx`,
`app/fuentes/page.tsx`) y tenía un cuarto mapa **distinto** en
`features/studio/components/DossierPanel.tsx`, con dos estados que no existen en
el backend (`CONFIRMED`, `DESACTUALIZADA`).

Estos tests fallan si:
  1. el fichero generado se queda desfasado respecto al backend;
  2. algún estado del backend se queda sin etiqueta en español;
  3. algún estado del backend se queda sin insignia en la web;
  4. vuelve a aparecer un mapa de estados **fuera** del módulo compartido.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API_SRC = RAIZ / "apps" / "api" / "src"
WEB = RAIZ / "apps" / "web"
COMPARTIDO = WEB / "lib" / "estados.ts"
GENERADO = WEB / "lib" / "estados.generado.ts"

if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))
if str(RAIZ / "tools") not in sys.path:
    sys.path.insert(0, str(RAIZ / "tools"))

from neuralnews import states  # noqa: E402

import generate_estados  # noqa: E402

# Códigos técnicos de estado: no pueden aparecer como **clave de un mapa**
# fuera del módulo compartido.
CODIGOS = (
    list(states.SOURCE_STATES)
    + list(states.STORY_STATES)
    + list(states.JOB_STATES)
    + list(states.PACKAGE_STATES)
    + list(states.CLAIM_VERIFICATION_LABELS)
    + list(states.CLAIM_KIND_LABELS)
    + list(states.APPROVAL_LABELS)
    # Los dos que el panel del dossier usaba y que **no existen** en el backend.
    + ["CONFIRMED", "DESACTUALIZADA"]
)


def _ficheros_web() -> list[Path]:
    return [
        p
        for p in WEB.rglob("*")
        if p.suffix in {".ts", ".tsx"}
        and "node_modules" not in p.parts
        and ".next" not in p.parts
        and p not in {COMPARTIDO, GENERADO}
    ]


def _mapa_ts(texto: str, nombre: str) -> dict[str, str]:
    """Extrae las claves de un `export const NOMBRE ... = { ... }` de TypeScript."""
    coincidencia = re.search(
        rf"export const {nombre}[^=]*=\s*\{{(.*?)\n\}};", texto, re.DOTALL
    )
    assert coincidencia, f"No se encuentra el mapa {nombre} en {COMPARTIDO.name}"
    return {
        clave: valor
        for clave, valor in re.findall(r"(\w+)\s*:\s*\"([^\"]*)\"", coincidencia.group(1))
    }


def test_el_fichero_generado_esta_al_dia() -> None:
    """Si cambia el backend y no se regenera, este test falla."""
    actual = GENERADO.read_text(encoding="utf-8")
    esperado = generate_estados.generar()
    assert actual == esperado, (
        "apps/web/lib/estados.generado.ts está desfasado respecto a "
        "apps/api/src/neuralnews/states.py. Ejecuta: python tools/generate_estados.py"
    )


def test_cada_estado_del_backend_tiene_etiqueta() -> None:
    for grupo, etiquetas in (
        (states.SOURCE_STATES, states.SOURCE_LABELS),
        (states.STORY_STATES, states.STORY_LABELS),
        (states.JOB_STATES, states.JOB_LABELS),
        (states.PACKAGE_STATES, states.PACKAGE_LABELS),
        (states.CLAIM_VERIFICATION_LABELS.keys(), states.CLAIM_VERIFICATION_LABELS),
        (states.CLAIM_KIND_LABELS.keys(), states.CLAIM_KIND_LABELS),
    ):
        for estado in grupo:
            assert estado in etiquetas, f"El estado {estado} no tiene etiqueta en español"


def test_cada_estado_del_backend_tiene_insignia_en_la_web() -> None:
    texto = COMPARTIDO.read_text(encoding="utf-8")
    mapa_noticia = _mapa_ts(texto, "BADGE_DE_NOTICIA")
    mapa_fuente = _mapa_ts(texto, "BADGE_DE_FUENTE")
    mapa_trabajo = _mapa_ts(texto, "BADGE_DE_TRABAJO")
    mapa_paquete = _mapa_ts(texto, "BADGE_DE_PAQUETE")
    mapa_verif = _mapa_ts(texto, "BADGE_DE_VERIFICACION")

    for estado in states.STORY_STATES:
        assert estado in mapa_noticia, f"El estado de noticia {estado} no tiene insignia"
    for estado in states.SOURCE_STATES:
        assert estado in mapa_fuente, f"El estado de fuente {estado} no tiene insignia"
    for estado in states.JOB_STATES:
        assert estado in mapa_trabajo, f"El estado de trabajo {estado} no tiene insignia"
    for estado in states.PACKAGE_STATES:
        assert estado in mapa_paquete, f"El estado de paquete {estado} no tiene insignia"
    for estado in states.CLAIM_VERIFICATION_LABELS:
        assert estado in mapa_verif, f"El estado de verificación {estado} no tiene insignia"

    # La insignia sólo puede ser una de las definidas en `app/globals.css`.
    permitidas = {"badge-ok", "badge-warn", "badge-err", "badge-info", "badge-neutral"}
    for nombre, mapa in (
        ("BADGE_DE_NOTICIA", mapa_noticia),
        ("BADGE_DE_FUENTE", mapa_fuente),
        ("BADGE_DE_TRABAJO", mapa_trabajo),
        ("BADGE_DE_PAQUETE", mapa_paquete),
        ("BADGE_DE_VERIFICACION", mapa_verif),
    ):
        for estado, clase in mapa.items():
            assert clase in permitidas, f"{nombre}.{estado} usa la clase inexistente {clase}"


def test_no_hay_mapas_de_estado_duplicados_en_la_web() -> None:
    """Ninguna página puede volver a declarar su propio mapa de estados."""
    patron = re.compile(
        r"^\s*(" + "|".join(sorted(set(CODIGOS), key=len, reverse=True)) + r")\s*:",
        re.MULTILINE,
    )
    ofensores: list[str] = []
    for fichero in _ficheros_web():
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        for linea in patron.findall(texto):
            ofensores.append(f"{fichero.relative_to(RAIZ)} declara el estado {linea}")
    assert not ofensores, (
        "Los mapas de estado deben vivir sólo en `apps/web/lib/estados.ts`. "
        "Duplicados:\n  " + "\n  ".join(ofensores)
    )


def test_la_web_no_declara_estados_que_el_backend_desconoce() -> None:
    """`CONFIRMED` y `DESACTUALIZADA` se usaban en el dossier y no existen."""
    conocidos = set(CODIGOS) - {"CONFIRMED", "DESACTUALIZADA"}
    texto = COMPARTIDO.read_text(encoding="utf-8") + GENERADO.read_text(encoding="utf-8")
    for nombre in (
        "BADGE_DE_NOTICIA",
        "BADGE_DE_FUENTE",
        "BADGE_DE_TRABAJO",
        "BADGE_DE_PAQUETE",
        "BADGE_DE_VERIFICACION",
    ):
        for clave in _mapa_ts(texto, nombre):
            assert clave in conocidos, f"{nombre} declara un estado desconocido: {clave}"
