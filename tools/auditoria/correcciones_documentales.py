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
        "`../.remotes/neural-news.git`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/archive/neuralnews-20261101/`",
        "`../archive/neuralnews-20261101/`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/MANIFIESTO_SELLADO_2026-11-01.txt`",
        "`../backups/MANIFIESTO_SELLADO_2026-11-01.txt`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt`",
        "`../backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/bundles/`",
        "`../backups/bundles/`",
        1,
    ),
    (
        "ESTADO_REAL.md",
        "`NeuralStories/backups/db/neuralnews-2026-11-01.sql`",
        "`../backups/db/neuralnews-2026-11-01.sql`",
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
]

# Rutas del **workspace** (carpetas hermanas del repositorio) y la carpeta de
# runtime del propio repositorio.
#
# El prefijo correcto depende de la **profundidad** del documento: desde la
# raíz del repositorio, el workspace está a un nivel (`../`); desde
# `docs/agente/`, a tres (`../../../`). Por eso no se sustituye de forma
# literal, sino que se normaliza el número de niveles.
CARPETAS_WORKSPACE = ("newsV2", "archive", ".remotes", "backups")
RE_TOKEN_BACKTICK = re.compile(r"`([^`\n]+)`")
RE_RUTA_WORKSPACE = re.compile(
    r"^(?P<prefijo>(?:\.\./)*)(?P<carpeta>" + "|".join(re.escape(c) for c in CARPETAS_WORKSPACE) + r")(?P<resto>/.*)?$"
)
RE_RUTA_STORAGE = re.compile(r"^(?P<prefijo>(?:\.\./)*)neural-news/storage(?P<resto>/.*)?$")

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

    Cada ruta recibe exactamente el número de niveles `../` que necesita para
    llegar al workspace desde el documento donde se cita. Es idempotente: se
    puede volver a ejecutar sin acumular prefijos.
    """
    informe: list[str] = []
    for relativo in DOCUMENTOS_A_REVISAR:
        ruta = RAIZ / relativo
        if not ruta.exists():
            continue
        profundidad = len(Path(relativo).parts) - 1  # 0 = raíz del repositorio
        niveles_workspace = "../" * (profundidad + 1)
        niveles_repo = "../" * profundidad
        texto = ruta.read_text(encoding="utf-8")

        def _normaliza(match: re.Match[str]) -> str:
            token = match.group(1)
            workspace = RE_RUTA_WORKSPACE.match(token)
            if workspace:
                resto = workspace.group("resto") or ""
                return f"`{niveles_workspace}{workspace.group('carpeta')}{resto}`"
            storage = RE_RUTA_STORAGE.match(token)
            if storage:
                resto = storage.group("resto") or ""
                return f"`{niveles_repo}storage{resto}`"
            return match.group(0)

        nuevo = RE_TOKEN_BACKTICK.sub(_normaliza, texto)
        if nuevo != texto:
            if not dry_run:
                ruta.write_text(nuevo, encoding="utf-8", newline="\n")
            informe.append(relativo)
    return informe


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
