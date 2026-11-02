"""El supervisor externo y el prompt deben hablar el mismo idioma.

`supervisor.sh` decide qué hacer **leyendo etiquetas en la salida del agente**:
si el prompt y el guion no coinciden en esas etiquetas, el supervisor no
detecta ni el final ni la espera por cuota, y el ciclo se queda dando vueltas.

Este test comprueba el contrato entre los dos ficheros, y que el guion sea
ejecutable en principle (finales de línea LF, sin BOM, bloques equilibrados).

Nota: en esta máquina **no** se puede ejecutar el guion (WSL no arranca porque
la virtualización está desactivada), así que la comprobación es estática.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROMPT = RAIZ / "PROMPT.md"
SUPERVISOR = RAIZ / "supervisor.sh"

# Las etiquetas que el guion busca con `grep -q`.
ETIQUETAS = ("CONTINUAR", "ESPERA_CUOTA", "INTERVENCION", "PROYECTO_COMPLETADO")


def _supervisor() -> str:
    return SUPERVISOR.read_text(encoding="utf-8")


def _prompt() -> str:
    return PROMPT.read_text(encoding="utf-8")


def test_el_prompt_declara_las_cuatro_etiquetas() -> None:
    prompt = _prompt()
    for etiqueta in ETIQUETAS:
        assert f"[ESTADO: {etiqueta}]" in prompt, f"el prompt no declara [ESTADO: {etiqueta}]"


def test_el_supervisor_busca_las_mismas_etiquetas() -> None:
    """Tres etiquetas se buscan explícitamente; `CONTINUAR` es la ruta por defecto.

    En el guion, `[ESTADO: CONTINUAR]` **no** se busca con `grep`: si no
    aparece ninguna de las otras tres, el ciclo cae en el último `echo`, que
    es justamente el estado CONTINUAR. Por eso aquí no se exige un `grep`.
    """
    supervisor = _supervisor()
    for etiqueta in ("ESPERA_CUOTA", "INTERVENCION", "PROYECTO_COMPLETADO"):
        assert f"\\[ESTADO: {etiqueta}\\]" in supervisor, (
            f"el supervisor no busca [ESTADO: {etiqueta}]"
        )
    assert "estado CONTINUAR" in supervisor, "el guion no contempla el estado CONTINUAR"


def test_el_supervisor_usa_los_ficheros_que_existen() -> None:
    supervisor = _supervisor()
    for ruta in ("docs/agente/PLAN.md", "docs/agente/espera.txt", "docs/agente/TERMINADO"):
        assert ruta in supervisor, f"el supervisor no usa {ruta}"
    assert (RAIZ / "docs" / "agente" / "PLAN.md").exists()


def test_el_supervisor_tiene_lf_y_sin_bom() -> None:
    """Bash se rompe con CRLF y con BOM."""
    datos = SUPERVISOR.read_bytes()
    assert not datos.startswith(b"\xef\xbb\xbf"), "el guion tiene BOM: bash lo leerá mal"
    assert b"\r\n" not in datos, "el guion tiene CRLF: bash lo leerá mal"


def test_los_bloques_del_guion_estan_equilibrados() -> None:
    supervisor = _supervisor()
    ifs = len(re.findall(r"^\s*if\s", supervisor, re.M))
    fis = len(re.findall(r"^\s*fi\s*$", supervisor, re.M))
    fors = len(re.findall(r"^\s*for\s", supervisor, re.M))
    dones = len(re.findall(r"^\s*done\s*$", supervisor, re.M))
    assert ifs == fis, f"if/fi descompensados: {ifs} if y {fis} fi"
    assert fors == dones, f"for/done descompensados: {fors} for y {dones} done"


def test_el_guion_tiene_el_marcador_de_configuracion_pendiente() -> None:
    """`AGENTE_CMD` es un marcador: hay que rellenarlo (SUP-01 en TAREAS.md)."""
    supervisor = _supervisor()
    assert "AGENTE_CMD=" in supervisor
    assert "tu_comando_de_agente_aqui" in supervisor, (
        "AGENTE_CMD sigue siendo el marcador de posición: el supervisor no lanzaría nada"
    )
