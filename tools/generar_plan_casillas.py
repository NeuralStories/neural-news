"""Genera `docs/agente/PLAN.md` (con casillas) desde `PLAN_MAESTRO.md`.

El supervisor externo (`supervisor.sh`) valida el proyecto con
`grep -q "\\[ \\]" docs/agente/PLAN.md`: si encuentra una casilla pendiente,
no da el proyecto por terminado y sigue relanzando. Por eso este fichero:

  - se **genera** desde el plan maestro (una sola fuente de verdad: no hay dos
    listas que puedan divergir);
  - usa `[x]` para lo completado y `[ ]` para lo pendiente;
  - **no** incluye las decisiones del propietario: no son tareas ejecutables y
    dejarlas como `[ ]` haría que el supervisor nunca cerrara el proyecto.

Uso:
    python tools/generar_plan_casillas.py           # escribe el fichero
    python tools/generar_plan_casillas.py --check   # sólo comprueba (CI)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MAESTRO = RAIZ / "docs" / "agente" / "PLAN_MAESTRO.md"
DESTINO = RAIZ / "docs" / "agente" / "PLAN.md"

RE_FILA = re.compile(r"^\|\s*(NN-[\w.\-]+)\s*\|(.+)$")
RE_ESTADO = re.compile(r"\*\*(COMPLETADA|COMPLETADA \(desviación\)|PENDIENTE|EN CURSO|BLOQUEADA)\*\*")
# Las celdas pueden contener pipes escapados (`\|`, p. ej. `local\|beta\|prod`):
# partir por cualquier pipe desplazaría las columnas y haría que una fila
# completada pareciera pendiente.
RE_PIPE = re.compile(r"(?<!\\)\|")


def _celdas(linea: str) -> list[str]:
    partes = RE_PIPE.split(linea)
    # Una fila de tabla empieza y acaba con «|»: las partes 1..n-1 son celdas.
    return [p.strip() for p in partes[1:-1]]


def _titulo_actual(lineas: list[str]) -> str:
    for linea in reversed(lineas):
        if linea.startswith("## "):
            return linea[3:].strip()
    return "Plan"


def generar() -> str:
    lineas = MAESTRO.read_text(encoding="utf-8").splitlines()
    partes: list[str] = [
        "# PLAN — neural.news (lista operativa con casillas)",
        "",
        "**Generado por `tools/generar_plan_casillas.py` desde `docs/agente/PLAN_MAESTRO.md`.**",
        "No editar a mano: el plan maestro es la fuente de verdad y este fichero se regenera",
        "con `python tools/generar_plan_casillas.py`.",
        "",
        "El supervisor externo (`supervisor.sh`) comprueba este fichero: si encuentra una casilla",
        "`[ ]` sin marcar, da el proyecto por **no** terminado. Las decisiones del propietario no",
        "figuran aquí como casillas porque no son tareas ejecutables: están en `TAREAS.md` y en",
        "`ESTADO.md`.",
        "",
    ]
    titulo = ""
    total = 0
    completadas = 0
    for indice, linea in enumerate(lineas):
        if linea.startswith("## "):
            titulo = _titulo_actual(lineas[: indice + 1])
            continue
        coincidencia = RE_FILA.match(linea)
        if not coincidencia:
            continue
        celdas = _celdas(linea)
        if len(celdas) < 4:
            continue
        identificador = celdas[0]
        descripcion = celdas[1]
        criterio = celdas[3]
        estado = celdas[4] if len(celdas) > 4 else ""
        evidencia = celdas[5] if len(celdas) > 5 else ""
        esta_completada = "COMPLETADA" in estado
        marca = "x" if esta_completada else " "
        total += 1
        completadas += 1 if esta_completada else 0
        partes.append(
            f"- [{marca}] **{identificador}** — {descripcion} — *criterio:* {criterio} — "
            f"*evidencia:* {evidencia or '—'}"
        )
    partes.insert(6, f"**Tareas:** {total} · **completadas:** {completadas} · "
                     f"**pendientes:** {total - completadas}")
    partes.append("")
    return "\n".join(partes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Sólo comprobar.")
    args = parser.parse_args()

    contenido = generar()
    if args.check:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != contenido:
            print(
                f"DESFASADO: {DESTINO.relative_to(RAIZ)} no coincide con el plan maestro.\n"
                "Ejecuta: python tools/generar_plan_casillas.py"
            )
            return 1
        print("OK: PLAN.md está al día.")
        return 0

    DESTINO.write_text(contenido, encoding="utf-8")
    print(f"Escrito: {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
