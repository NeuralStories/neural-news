"""Correcciones documentales de la auditoría A2 (enlaces y rutas).

Cada sustitución declara **cuántas veces** debe aplicarse. Si el recuento no
coincide, el script aborta: no se aplica un cambio a ciegas.

Uso:
    python tools/auditoria/correcciones_documentales.py            # aplica
    python tools/auditoria/correcciones_documentales.py --dry-run  # simula
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# (fichero, texto original, texto nuevo, apariciones esperadas)
CAMBIOS: list[tuple[str, str, str, int]] = [
    # --- README: el directorio real de gobernanza es el español --------------
    # El README decía «docs/gobernance» (anglicismo mal transcrito): un nombre
    # de carpeta que no existe, por lo que los dos enlaces quedaban rotos.
    (
        "README.md",
        "docs/gobernance",
        "docs/gobernanza",
        2,
    ),
    # --- ESTADO_REAL: rutas del workspace, relativas a la raíz del repo -----
    (
        "ESTADO_REAL.md",
        "| Repositorio activo | `NeuralStories/neural-news/` (rama `beta/v1`) |",
        "| Repositorio activo | esta misma carpeta (raíz del repositorio), rama "
        "`release/1.0.0-beta.1` |",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/.remotes/neural-news.git`",
        "`.remotes/neural-news.git`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/archive/neuralnews-20261101/`",
        "`archive/neuralnews-20261101/`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/MANIFIESTO_SELLADO_2026-11-01.txt`",
        "`backups/MANIFIESTO_SELLADO_2026-11-01.txt`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt`",
        "`backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/bundles/`",
        "`backups/bundles/`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/db/neuralnews-2026-11-01.sql`",
        "`backups/db/neuralnews-2026-11-01.sql`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/neural-news/storage/FLOW_RECOVERY_2026-11-01_DIR/`",
        "`storage/FLOW_RECOVERY_2026-11-01_DIR/`",
        1,
    ),
    # --- REGISTRO: el fichero de prueba era hipotético -----------------------
    (
        "docs/agente/REGISTRO.md",
        "inyectando `apps/web/lib/fichero-falso.ts` en una fila",
        "inyectando un fichero de prueba en `apps/web/lib/` en una fila",
        1,
    ),
    # --- PLAN: solo se entrega la variante de PowerShell ---------------------
    (
        "docs/agente/PLAN.md",
        "`bootstrap.ps1` / `bootstrap.sh`: un comando",
        "`bootstrap.ps1`: un comando (solo PowerShell; no se entrega variante para bash)",
        1,
    ),
    (
        "docs/agente/PLAN_MAESTRO.md",
        "`bootstrap.ps1` / `bootstrap.sh`: un comando",
        "`bootstrap.ps1`: un comando (solo PowerShell; no se entrega variante para bash)",
        1,
    ),
    # --- ESTADO_REAL: HelpModal.tsx se eliminó en B13 ------------------------
    (
        "ESTADO_REAL.md",
        "| **B13** | `HelpModal.tsx` sin usar | `features/studio/components/HelpModal.tsx` |",
        "| **B13** | `HelpModal.tsx` sin usar | (eliminado en B13; ruta histórica: "
        "`features/studio/components/HelpModal.tsx`) |",
        1,
    ),
    # --- bootstrap.ps1: construir la web (si no, un clon limpio no arranca) ---
    (
        "scripts/bootstrap.ps1",
        "  } finally { Pop-Location }\n}\n\n# --- 6. Pruebas",
        "  } finally { Pop-Location }\n"
        "\n"
        "  # La web se sirve en modo producción (`next start`), y eso **exige** un\n"
        "  # build. Sin este paso, un clon limpio se queda sin web: `npm run start`\n"
        "  # falla con «Could not find a production build in the '.next' directory»\n"
        "  # (hallazgo de la auditoría A1: siguiendo la guía de pruebas, la web\n"
        "  # nunca llegaba a levantarse).\n"
        "  #\n"
        "  # El build necesita saber el entorno: NEURAL_ENV=local es la instalación\n"
        "  # de escritorio (proxy same-origin contra la API local). Fuera de local hay\n"
        "  # que definir NEURAL_API_URL, y el build falla a propósito si no está\n"
        "  # (prueba negativa 3.5 de GUIA_PRUEBAS_BETA.md).\n"
        '  Paso "Construyendo la web (NEURAL_ENV=local)"\n'
        '  $env:NEURAL_ENV = "local"\n'
        '  Push-Location "apps\\web"\n'
        "  try {\n"
        "    & npm run build\n"
        '    if ($LASTEXITCODE -ne 0) { throw "Falló la construcción de la web." }\n'
        "  } finally { Pop-Location }\n"
        "}\n"
        "\n"
        "# --- 6. Pruebas",
        1,
    ),
    # --- start.ps1: avisar si la web no está construida -----------------------
    (
        "scripts/start.ps1",
        '  $web = Join-Path $raiz "apps\\web"\n',
        '  $web = Join-Path $raiz "apps\\web"\n'
        "  # La web se sirve en modo producción: sin build, `next start` no arranca.\n"
        '  if (-not (Test-Path (Join-Path $web ".next\\BUILD_ID"))) {\n'
        '    throw "La web no está construida. Ejecuta antes: scripts\\bootstrap.ps1"\n'
        "  }\n",
        1,
    ),
]

# Rutas del **workspace** (carpetas hermanas del repositorio).
#
# El proyecto tiene su propia convención (la misma que usa
# `tools/auditar_evidencias.py`): las rutas que viven fuera del repositorio se
# citan por su primer componente (`backups/`, `archive/`, `.remotes/`,
# `newsV2/`), sin prefijos ``. Un intento anterior de la auditoría de
# anteponer `` rompía esa convención y hacía fallar
# `tests/test_evidencias_plan.py`: por eso aquí **no** se toca nada.
RUTAS_WORKSPACE: dict[str, str] = {}

# Documentos en los que se revisan las rutas (los mismos que comprueba
# `comprobar_enlaces.py`).
DOCUMENTOS_A_REVISAR = [
    "README.md",
    "CHANGELOG.md",
    "ESTADO_REAL.md",
    "IMPLEMENTACION_REALIZADA.md",
    "docs/agente/PLAN_MAESTRO.md",
    "docs/agente/PLAN.md",
    "docs/agente/TAREAS.md",
    "docs/agente/REGISTRO.md",
    "docs/agente/ESTADO.md",
    "docs/entrega/RESUMEN_COMPLETO.md",
    "docs/entrega/NOTAS_BETA.md",
    "docs/entrega/GUIA_PRUEBAS_BETA.md",
    "docs/entrega/INFORME_FINAL.md",
    "docs/entrega/RESUMEN_VERIFICACIONES.md",
]


def _corregir_rutas_de_workspace(dry_run: bool = False) -> list[str]:
    """Normaliza las rutas del workspace citadas en los documentos.

    El proyecto cita las rutas externas por su primer componente (`backups/`,
    `archive/`, `.remotes/`, `newsV2/`), **sin** prefijos ``: es la
    convención de `tools/auditar_evidencias.py` y la que usa el propio test
    `tests/test_evidencias_plan.py`. Un intento anterior de la auditoría de
    anteponer `` rompía esa convención y hacía fallar ese test, así que
    aquí **no se altera nada**: la función se conserva como punto de extensión.
    """
    return []


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fallos: list[str] = []
    for relativo, viejo, nuevo, esperadas in CAMBIOS:
        ruta = RAIZ / relativo
        if not ruta.exists():
            fallos.append(f"{relativo}: no existe")
            continue
        texto = ruta.read_text(encoding="utf-8")
        encontradas = texto.count(viejo)
        if encontradas != esperadas:
            # Idempotencia: si el cambio ya está aplicado, no es un fallo.
            if encontradas == 0 and texto.count(nuevo) >= esperadas:
                print(f"OK (ya aplicado)  {relativo}")
                continue
            fallos.append(
                f"{relativo}: «{viejo[:60]}…» aparece {encontradas} veces, "
                f"se esperaban {esperadas}"
            )
            continue
        if args.dry_run:
            print(f"OK (simulado)  {relativo}: {esperadas}×")
            continue
        ruta.write_text(texto.replace(viejo, nuevo), encoding="utf-8", newline="\n")
        print(f"OK  {relativo}: {esperadas}× «{viejo[:50]}»")

    for fallo in fallos:
        print(f"FALLA  {fallo}")
    tocados = _corregir_rutas_de_workspace(args.dry_run)
    if tocados:
        print(f"Rutas de workspace corregidas en: {', '.join(tocados)}")
    print(f"\n{len(CAMBIOS) - len(fallos)}/{len(CAMBIOS)} cambios aplicados.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
