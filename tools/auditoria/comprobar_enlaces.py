"""Auditoría A2.2 — comprueba que TODOS los enlaces y rutas de los documentos existen.

No es una comprobación de estilo: recorre los documentos de la entrega (y el
README y el CHANGELOG), extrae los destinos y verifica que cada uno existe en
el disco. Un enlace roto es una afirmación falsa en la documentación.

Uso:
    python tools/auditoria/comprobar_enlaces.py            # informe
    python tools/auditoria/comprobar_enlaces.py --json     # salida JSON
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Documentos que se revisan (la gobernanza heredada se excluye: es evidencia
# verbatim y sus enlaces apuntan a rutas de la copia histórica).
DOCUMENTOS = [
    "README.md",
    "CHANGELOG.md",
    "ESTADO_REAL.md",
    "IMPLEMENTACION_REALIZADA.md",
    "docs/agente/PLAN_MAESTRO.md",
    "docs/agente/PLAN.md",
    "docs/agente/TAREAS.md",
    "docs/agente/REGISTRO.md",
    "docs/agente/ESTADO.md",
    "docs/adr/ADR-022-descartes-del-port.md",
    "docs/entrega/RESUMEN_COMPLETO.md",
    "docs/entrega/NOTAS_BETA.md",
    "docs/entrega/GUIA_PRUEBAS_BETA.md",
    "docs/entrega/INFORME_FINAL.md",
    "docs/entrega/RESUMEN_VERIFICACIONES.md",
    "docs/entrega/evidencias/F1_linea_base.md",
    "docs/entrega/evidencias/F6_lanzamiento.md",
]

RE_ENLACE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
RE_RUTA = re.compile(r"`([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)`")
RE_PLACEHOLDER = re.compile(r"[<>{}\[\]*]")


def _indice_de_ficheros() -> list[str]:
    """Rutas de todos los ficheros del repositorio (sin node_modules ni .next)."""
    indice: list[str] = []
    for base in ("apps", "tests", "tools", "docs", "scripts", "infra", "packages", "fixtures"):
        raiz = RAIZ / base
        if not raiz.exists():
            continue
        for candidato in raiz.rglob("*"):
            if not candidato.is_file():
                continue
            if "node_modules" in candidato.parts or ".next" in candidato.parts:
                continue
            indice.append(candidato.relative_to(RAIZ).as_posix())
    return indice


INDICE_FICHEROS = _indice_de_ficheros()

# Extensiones con las que un nombre suelto entre acentos graves puede ser un
# fichero real. Fuera de esta lista, un token como `1.0.0-beta.1`, `sys.path`
# o `neural.news` **no** es una afirmación sobre un fichero.
EXTENSIONES_FICHERO = {
    ".md", ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".ps1", ".json", ".yml",
    ".yaml", ".toml", ".css", ".txt", ".sh", ".ico", ".svg", ".csv", ".sql", ".ini",
}


def _existe(destino: Path) -> bool:
    return destino.exists()


def _coincide_por_sufijo(limpia: str) -> bool:
    """¿Existe en el repositorio algún fichero cuya ruta acabe en esa ruta?

    Los documentos citan rutas relativas a un subdirectorio (por ejemplo
    `features/studio/App.tsx`, que vive en `apps/web/`). Se aceptan si el
    sufijo coincide con algún fichero versionado.
    """
    normalizada = limpia.replace("\\", "/").strip("/")
    if not normalizada:
        return False
    for indice in INDICE_FICHEROS:
        if indice.endswith(normalizada):
            return True
    return False


def _buscar_por_nombre(nombre: str) -> bool:
    """¿Existe en el repositorio un fichero con ese nombre (en cualquier carpeta)?"""
    for base in ("apps", "tests", "tools", "docs", "scripts", "infra", "packages", "fixtures"):
        raiz = RAIZ / base
        if not raiz.exists():
            continue
        for candidato in raiz.rglob(nombre):
            if "node_modules" in candidato.parts or ".next" in candidato.parts:
                continue
            return True
    return (RAIZ / nombre).exists()


def revisar() -> list[str]:
    rotos: list[str] = []
    for relativo in DOCUMENTOS:
        fichero = RAIZ / relativo
        if not fichero.exists():
            rotos.append(f"{relativo}: el documento mismo no existe")
            continue
        texto = fichero.read_text(encoding="utf-8")
        base = fichero.parent
        destinos: list[str] = []
        for coincidencia in RE_ENLACE.finditer(texto):
            destinos.append(coincidencia.group(1).strip())
        for coincidencia in RE_RUTA.finditer(texto):
            destinos.append(coincidencia.group(1).strip())
        for destino in destinos:
            if not destino or destino.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if RE_PLACEHOLDER.search(destino):
                continue
            limpio = destino.split("#", 1)[0].split("?", 1)[0].strip()
            if not limpio:
                continue
            # Una ruta que empieza por «/» es un camino de URL, no un fichero.
            if limpio.startswith("/"):
                continue
            # Los registros y bases son ficheros de runtime: no viven en el repo.
            if limpio.lower().endswith((".log", ".db", ".sqlite")):
                continue
            # `storage/…` es el directorio de runtime (ignorado por git).
            if limpio.replace("\\", "/").startswith("storage/"):
                continue
            # `node_modules/…` describe el entorno instalado, no el repositorio.
            if limpio.replace("\\", "/").startswith("node_modules/"):
                continue
            if "/" in limpio or "\\" in limpio:
                # Es una ruta: se resuelve contra el documento, contra la raíz y
                # por sufijo (las rutas relativas a un subdirectorio son válidas).
                if (
                    _existe(base / limpio)
                    or _existe(RAIZ / limpio)
                    or _coincide_por_sufijo(limpio)
                ):
                    continue
                # Una rama o un tag no son ficheros: `release/1.0.0-beta.1`.
                if not Path(limpio).suffix.lower() in EXTENSIONES_FICHERO:
                    continue
                rotos.append(f"{relativo}: «{destino}» no existe")
                continue
            # Nombre suelto: solo se comprueba si su extensión es de fichero.
            extension = Path(limpio).suffix.lower()
            if extension not in EXTENSIONES_FICHERO:
                continue
            if not _buscar_por_nombre(limpio):
                rotos.append(f"{relativo}: «{limpio}» no existe en el repositorio")
    return rotos


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Salida en JSON.")
    args = parser.parse_args()

    rotos = revisar()
    if args.json:
        print(json.dumps({"rotos": rotos, "total": len(rotos)}, ensure_ascii=False, indent=2))
    else:
        for linea in rotos:
            print(f"ROTO  {linea}")
        print(f"\n{len(rotos)} destinos rotos en {len(DOCUMENTOS)} documentos.")
    return 1 if rotos else 0


if __name__ == "__main__":
    raise SystemExit(main())
