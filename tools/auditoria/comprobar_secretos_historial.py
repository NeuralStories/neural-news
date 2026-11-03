"""Auditoría A4.4 — secretos en el historial de git.

`tools/scan_secrets.py` ya escanea el árbol versionado y el historial. Esta
comprobación es la segunda mitad de A4.4: **los commits de esta entrega**
(contenido añadido o modificado) filtrados por patrones de clave, con dos
patrones que el escáner del repo no tiene: clave privada PEM y credenciales
dentro de una URL de conexión.

Uso:
    python tools/auditoria/comprobar_secretos_historial.py
    python tools/auditoria/comprobar_secretos_historial.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

PATRONES: dict[str, re.Pattern[str]] = {
    "openai": re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    "google": re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    "github": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "aws": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack": re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),
    "asignacion-larga": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*"
        r"['\"]?([A-Za-z0-9+/_\-]{24,})['\"]?"
    ),
    "clave-privada": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "credenciales-en-url": re.compile(
        r"(?i)\b(?:postgres|postgresql|mysql|redis|mongodb)://[^\s:@/]+:[^\s:@/]+@"
    ),
}

# Valores que el proyecto usa a propósito como ejemplos (no son secretos).
VALORES_DE_EJEMPLO = ("neural-demo", "neural-local", "changeme", "your-key-here")


def _diff() -> str:
    """Todo el historial con su parche."""
    return subprocess.run(
        ["git", "-C", str(RAIZ), "log", "-p", "--all"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    ).stdout


def revisar() -> list[str]:
    salida = _diff()
    hallazgos: list[str] = []
    for etiqueta, patron in PATRONES.items():
        for coincidencia in patron.finditer(salida):
            valor = coincidencia.group(0)
            if any(ejemplo in valor for ejemplo in VALORES_DE_EJEMPLO):
                continue
            linea = salida[: coincidencia.start()].count("\n") + 1
            contexto = salida[max(0, coincidencia.start() - 50) : coincidencia.start() + 40]
            hallazgos.append(
                f"{etiqueta} (línea {linea} del diff): ...{contexto.strip()}..."
            )
    return hallazgos


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    hallazgos = revisar()
    if args.json:
        print(json.dumps({"hallazgos": hallazgos, "total": len(hallazgos)}, ensure_ascii=False, indent=2))
    else:
        for hallazgo in hallazgos:
            print(f"HALLAZGO  {hallazgo}")
        print(f"\n{len(hallazgos)} hallazgo(s) de secretos en el historial.")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    raise SystemExit(main())
