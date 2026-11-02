"""NN-111.11 — Escaneo de secretos en el árbol y en el historial.

Uso:
    python tools/scan_secrets.py [ruta-del-repo]

Sale con código 1 si encuentra algo. Comprueba:

  - variables con forma de clave real (`sk-…`, `AIza…`, `ghp_…`, `AKIA…`);
  - cadenas largas asignadas a nombres tipo key/token/secret/password;
  - ficheros de entorno con valores no vacíos (fuera de `.env.example`);
  - las claves de ejemplo conocidas del proyecto.

Un secreto en el historial **sigue en el historial**: si aparece, la clave se
rota, no se limpia el fichero.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATRONES: list[tuple[str, re.Pattern[str]]] = [
    ("openai", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("google", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    (
        "asignacion-larga",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*"
            r"['\"]?([A-Za-z0-9+/_\-]{24,})['\"]?"
        ),
    ),
]

# Valores de ejemplo conocidos: no son secretos, pero sí conviene detectarlos
# para que nadie los deje puestos por despiste.
EJEMPLOS: list[tuple[str, re.Pattern[str]]] = [
    ("clave-de-ejemplo", re.compile(r"\bneural-demo\b")),
    ("clave-de-ejemplo", re.compile(r"\bneural-local\b")),
]

# Ficheros que nunca se escanean (binarios o generados).
EXCLUIDOS = {".git", "node_modules", ".next", "__pycache__", ".pytest_cache", "storage", "test-results"}
EXCLUIDOS_SUFIJO = {".pyc", ".zip", ".rar", ".exe", ".dll", ".png", ".jpg", ".mp4", ".woff2", ".db"}

# Valores que son marcadores de posición conocidos y no son secretos.
MARCADORES = {
    "",
    "none",
    "null",
    "changeme",
    "example",
    "your-key-here",
    "tu-clave-aqui",
    "pendiente",
    "x",
    "***",
}


def _texto_de_interes(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


def _relativo(ruta: Path, raiz: Path) -> str:
    try:
        return str(ruta.relative_to(raiz))
    except ValueError:
        return str(ruta)


def escanear_arbol(raiz: Path) -> tuple[list[str], list[str]]:
    """Devuelve (fallos, avisos). Un fallo es un secreto posible; un aviso, algo
    que conviene revisar pero que no bloquea la entrega."""
    fallos: list[str] = []
    avisos: list[str] = []
    for ruta in raiz.rglob("*"):
        if not ruta.is_file():
            continue
        if any(parte in EXCLUIDOS for parte in ruta.parts):
            continue
        if ruta.suffix.lower() in EXCLUIDOS_SUFIJO:
            continue
        nombre = ruta.name
        texto = _texto_de_interes(ruta)
        if not texto:
            continue
        for etiqueta, patron in PATRONES:
            for coincidencia in patron.finditer(texto):
                valor = coincidencia.group(0)
                if valor.strip().strip("'\"").lower() in MARCADORES:
                    continue
                if "test" in _relativo(ruta, raiz).lower() and etiqueta == "asignacion-larga":
                    # Las pruebas usan valores falsos a propósito.
                    continue
                fallos.append(
                    f"{_relativo(ruta, raiz)}: posible {etiqueta} → {valor[:12]}…"
                )
        if nombre == ".env" or (nombre.startswith(".env.") and nombre != ".env.example"):
            for linea in texto.splitlines():
                limpia = linea.strip()
                if not limpia or limpia.startswith("#") or "=" not in limpia:
                    continue
                clave, _, valor = limpia.partition("=")
                valor = valor.strip().strip("'\"").lower()
                if valor and valor not in MARCADORES:
                    fallos.append(
                        f"{_relativo(ruta, raiz)}: {clave.strip()} tiene un valor real"
                    )
        # La contraseña de ejemplo es un marcador conocido: avisa, no falla.
        if nombre != ".env.example" and not any(
            parte == "tests" for parte in ruta.parts
        ):
            for etiqueta, patron in EJEMPLOS:
                if patron.search(texto):
                    avisos.append(
                        f"{_relativo(ruta, raiz)}: contiene {etiqueta} "
                        "(no es un secreto, pero conviene confirmar que es solo un ejemplo)"
                    )
    return fallos, avisos


def escanear_historial(raiz: Path, profundidad: int = 200) -> tuple[list[str], list[str]]:
    """Busca el patrón en el historial de git (parche y mensajes)."""
    fallos: list[str] = []
    avisos: list[str] = []
    try:
        salida = subprocess.run(
            ["git", "-C", str(raiz), "log", "-p", f"-{profundidad}", "--all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return [], ["no se pudo leer el historial de git"]
    for etiqueta, patron in PATRONES:
        for coincidencia in patron.finditer(salida.stdout):
            valor = coincidencia.group(0)
            if valor.strip().strip("'\"").lower() in MARCADORES:
                continue
            fallos.append(f"historial: posible {etiqueta} → {valor[:12]}…")
    return fallos, avisos


def main() -> int:
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    raiz = raiz.resolve()
    print(f"Escaneando secretos en {raiz}…")
    fallos_arbol, avisos_arbol = escanear_arbol(raiz)
    fallos_hist, avisos_hist = escanear_historial(raiz)
    fallos = sorted(set(fallos_arbol + fallos_hist))
    avisos = sorted(set(avisos_arbol + avisos_hist))

    if avisos:
        print(f"\n{len(avisos)} aviso(s):")
        for a in avisos:
            print(f"  · {a}")
    if not fallos:
        print("\nOK: 0 hallazgos de secretos.")
        return 0
    print(f"\n{len(fallos)} hallazgo(s) de secretos:")
    for f in fallos:
        print(f"  ✗ {f}")
    print(
        "\nSi algo es un secreto real, **rótalo**: limpiar el fichero no lo saca "
        "del historial."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
