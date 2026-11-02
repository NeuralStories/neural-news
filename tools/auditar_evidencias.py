"""Audita la evidencia citada por el plan maestro (NN-113, §3.4 del contrato).

Un plan puede quedarse desfasado sin que nadie se entere: una tarea marcada
COMPLETADA puede citar un fichero que se borró después, o un test que ya no
existe. Este script **extrae las rutas que cita la columna de evidencia** de
`docs/agente/PLAN_MAESTRO.md` y comprueba, una a una, si el fichero existe.

Resultado por referencia:
  - `OK`          → la ruta existe dentro del repositorio;
  - `FUERA`       → la ruta está fuera del repositorio (artefactos sellados,
                     `storage/`, `backups/`): no se puede comprobar con git,
                     se dice con claridad en lugar de darla por buena;
  - `NO_EXISTE`   → la ruta **no** existe: la afirmación de la fila está
                     desfasada y hay que corregirla.

Uso:
    python tools/auditar_evidencias.py           # informa (exit 1 si hay NO_EXISTE)
    python tools/auditar_evidencias.py --check   # solo para CI
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MAESTRO = RAIZ / "docs" / "agente" / "PLAN_MAESTRO.md"

# Raíces donde se buscan las rutas citadas (todo lo versionado del producto).
RAICES = ("apps", "tests", "tools", "docs", "infra", "scripts", "packages")
# Rutas entre acentos graves que parecen rutas de fichero.
RE_RUTA = re.compile(r"`([^`]+)`")
# Directorios del repositorio que están fuera de git (artefactos sellados).
PREFIJOS_FUERA = ("storage/", "backups/", "archive/", ".remotes/", "apps/api/storage/")
# Sufijos de ruta que no son ficheros (comandos, firmas, claves…).
NO_ES_RUTA = re.compile(r"(^[A-Z_]{2,}$)|(^[a-z_]+$)|(^\d)|(^[<{\[])|(\s)")


def _es_ruta(texto: str) -> bool:
    if "/" not in texto and "\\" not in texto:
        return False
    if NO_ES_RUTA.search(texto):
        return False
    if texto.startswith(("http://", "https://")):
        return False
    return True


def _referencias() -> list[tuple[int, str, str]]:
    """(línea, id de tarea, ruta citada)."""
    encontradas = []
    for numero, linea in enumerate(MAESTRO.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.startswith("|") or "NN-" not in linea:
            continue
        celdas = [c.strip() for c in re.split(r"(?<!\\)\|", linea)[1:-1]]
        if len(celdas) < 6:
            continue
        identificador = celdas[0]
        evidencia = celdas[5]
        for referencia in RE_RUTA.findall(evidencia):
            if not _es_ruta(referencia):
                continue
            encontradas.append((numero, identificador, referencia))
    return encontradas


def _indices() -> list[Path]:
    """Todos los ficheros versionados (los que git sigue)."""
    try:
        import subprocess

        salida = subprocess.run(
            ["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, text=True, timeout=60
        )
        if salida.returncode == 0:
            return [RAIZ / p for p in salida.stdout.split("\0") if p]
    except (OSError, subprocess.SubprocessError):
        pass
    return [p for p in RAIZ.rglob("*") if p.is_file() and "node_modules" not in p.parts]


EXTENSIONES_CODIGO = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".sh",
    ".yml", ".yaml", ".ps1", ".csv", ".toml", ".ini", ".txt", ".html",
}


def _normalizar(referencia: str) -> str:
    """Quita el prefijo del repositorio y las referencias de línea."""
    limpia = referencia.rstrip(".,;:")
    if limpia.startswith("neural-news/"):
        limpia = limpia[len("neural-news/") :]
    # `fichero.py:43,156` → `fichero.py`
    limpia = re.sub(r":\d+(,\d+)*$", "", limpia)
    return limpia


def _ramas() -> set[str]:
    """Ramas de git: `beta/v1` es una referencia legítima, no un fichero."""
    try:
        import subprocess

        salida = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if salida.returncode == 0:
            return {r.strip() for r in salida.stdout.splitlines() if r.strip()}
    except (OSError, subprocess.SubprocessError):
        pass
    return set()


def _resolver(referencia: str) -> tuple[str, str]:
    """(estado, detalle). Estado: OK | FUERA | RUTA_OK | NO_EXISTE."""
    limpia = _normalizar(referencia)
    if limpia.startswith(PREFIJOS_FUERA):
        return "FUERA", "fuera del repositorio (artefacto sellado)"
    if limpia.startswith("node_modules/"):
        return "FUERA", "dentro de node_modules (no se versiona)"
    if limpia.startswith("next/") or limpia.startswith("packages/"):
        return "FUERA", "ruta de paquete, no de este repositorio"
    if limpia in _ramas():
        return "OK", "rama de git existente"
    if limpia.startswith("/"):
        # Ruta de API o de interfaz: se busca el literal en el código.
        for indice in _indices():
            try:
                if limpia in indice.read_text(encoding="utf-8", errors="ignore"):
                    return "RUTA_OK", "ruta presente en el código"
            except OSError:
                continue
        return "NO_EXISTE", "no aparece en ningún fichero versionado"

    # `fichero::nombre_de_test` → el fichero Y el test tienen que existir.
    nombre_test = None
    if "::" in limpia:
        limpia, nombre_test = limpia.split("::", 1)

    ultimo = limpia.rsplit("/", 1)[-1]
    es_directorio = limpia.endswith("/")
    extension = ultimo.rsplit(".", 1)[-1].lower() if "." in ultimo else ""
    es_fichero = bool(extension) and f".{extension}" in EXTENSIONES_CODIGO
    # Un fichero oculto (`.gitignore`) no tiene extensión.
    es_oculto = ultimo.startswith(".") and "." not in ultimo[1:]

    if es_fichero or es_directorio or es_oculto:
        candidatos = [RAIZ / limpia]
        for indice in _indices():
            try:
                relativo = indice.relative_to(RAIZ).as_posix()
            except ValueError:
                continue
            if relativo.endswith(limpia.rstrip("/")):
                candidatos.append(indice)
            elif es_directorio and relativo.startswith(limpia.rstrip("/") + "/"):
                # Un directorio no se indexa en git: se deduce de sus ficheros.
                candidatos.append(indice)
        if es_directorio:
            prefijo = "/" + limpia.rstrip("/") + "/"
            for indice in _indices():
                try:
                    relativo = "/" + indice.relative_to(RAIZ).as_posix()
                except ValueError:
                    continue
                if prefijo in relativo:
                    return "OK", "directorio con ficheros versionados"
        encontrado = next((c for c in candidatos if c.exists()), None)
        if encontrado is None:
            return "NO_EXISTE", "no existe ningún fichero con ese nombre"
        if nombre_test:
            try:
                if nombre_test not in encontrado.read_text(encoding="utf-8", errors="ignore"):
                    return "NO_EXISTE", f"el fichero existe pero no contiene «{nombre_test}»"
            except OSError:
                return "NO_EXISTE", "no se pudo leer el fichero"
        return "OK", "existe"

    # Rama, símbolo o identificador: se comprueba que aparezca en el **código**
    # (no en la documentación: si se buscara también en `docs/`, el propio plan
    # se citaría a sí mismo y la comprobación no probaría nada).
    candidatos_texto = [limpia]
    if "." in ultimo:
        # `modulo.atributo` → se busca también el atributo solo.
        candidatos_texto.append(ultimo.rsplit(".", 1)[-1])
    if "." not in ultimo and not es_directorio:
        # Una enumeración de valores (`ok/warn/error`) no es una ruta: no se
        # puede comprobar y no debe contarse como referencia válida.
        return "NO_ES_RUTA", "enumeración de valores, no una ruta"
    for indice in _indices():
        try:
            relativo = indice.relative_to(RAIZ).as_posix()
        except ValueError:
            continue
        if not relativo.startswith(("apps/", "tests/", "tools/", "scripts/", "infra/", "packages/")):
            continue
        try:
            contenido = indice.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(candidato in contenido for candidato in candidatos_texto):
            return "OK", "símbolo o rama presente en el código"
    return "NO_EXISTE", "no aparece en ningún fichero de código"


def auditar() -> tuple[list[str], list[str], list[str], list[str]]:
    ok: list[str] = []
    fuera: list[str] = []
    inexistentes: list[str] = []
    no_rutas: list[str] = []
    vistas: set[tuple[str, str]] = set()
    for numero, identificador, referencia in _referencias():
        clave = (identificador, referencia)
        if clave in vistas:
            continue
        vistas.add(clave)
        estado, detalle = _resolver(referencia)
        limpia = _normalizar(referencia)
        if estado == "OK":
            ok.append(f"{identificador}: {limpia}")
        elif estado == "RUTA_OK":
            ok.append(f"{identificador}: {limpia} (ruta)")
        elif estado == "FUERA":
            fuera.append(f"{identificador} (línea {numero}): {limpia} — {detalle}")
        elif estado == "NO_ES_RUTA":
            no_rutas.append(f"{identificador} (línea {numero}): {limpia} — {detalle}")
        else:
            inexistentes.append(f"{identificador} (línea {numero}): {limpia} — {detalle}")
    return ok, fuera, inexistentes, no_rutas


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass

    ok, fuera, inexistentes, no_rutas = auditar()
    for linea in inexistentes:
        print(f"NO_EXISTE  {linea}")
    print(
        f"\n{len(ok)} referencias comprobadas y existentes · "
        f"{len(fuera)} fuera del repositorio (artefactos sellados) · "
        f"{len(no_rutas)} que no son rutas · "
        f"{len(inexistentes)} desfasadas"
    )
    if not inexistentes:
        print("OK: ninguna fila cita un fichero que ya no exista.")
        return 0
    print("\nLas filas que citan esas rutas hay que corregirlas (o marcar la ruta como eliminada).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
