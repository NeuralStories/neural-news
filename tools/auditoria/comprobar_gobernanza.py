"""Auditoría A4/A2 — integridad de `docs/gobernanza/` (evidencia verbatim).

La carpeta `docs/gobernanza/` es la evidencia heredada de la entrega: sus bytes
están fijados por un manifiesto SHA-256 (`MANIFIESTO_ARCHIVOS_SHA256.txt`).
Esta comprobación verifica tres cosas, en orden:

1. Que los bytes del **árbol de trabajo** coinciden con los **blobs de git**
   (HEAD). Si difieren, alguien ha renormalizado la evidencia: es un hallazgo.
2. Que las entradas del manifiesto SHA-256 cuadran con los blobs de git.
3. Que las entradas del manifiesto cuadran con los bytes del árbol de trabajo.

Uso:
    python tools/auditoria/comprobar_gobernanza.py
    python tools/auditoria/comprobar_gobernanza.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GOBERNANZA = "docs/gobernanza"
MANIFIESTO = (
    "docs/gobernanza/03_EVIDENCIA_FLOW/revision_unificacion/extract/"
    "REVISION_UNIFICACION/MANIFIESTO_ARCHIVOS_SHA256.txt"
)


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=RAIZ, capture_output=True, check=True
    ).stdout


def _sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _blob(ruta: str) -> bytes | None:
    try:
        return _git("cat-file", "blob", f"HEAD:{ruta}")
    except subprocess.CalledProcessError:
        return None


def _entradas_manifiesto() -> list[tuple[str, str, int | None]]:
    """Devuelve [(ruta_relativa_raiz, sha256, bytes)] del manifiesto.

    Formato real del manifiesto: ``SHA-256  bytes  ruta_en_zip``.
    """
    ruta = RAIZ / MANIFIESTO
    if not ruta.exists():
        return []
    entradas: list[tuple[str, str, int | None]] = []
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        partes = linea.split()
        if len(partes) < 2:
            continue
        digest = partes[0]
        if not re_full_hex(digest):
            continue
        tamano: int | None = None
        if len(partes) >= 3 and partes[1].isdigit():
            tamano = int(partes[1])
            nombre = partes[2]
        else:
            nombre = partes[1]
        entradas.append((nombre.strip(), digest.lower(), tamano))
    return entradas


def re_full_hex(texto: str) -> bool:
    return len(texto) == 64 and all(c in "0123456789abcdefABCDEF" for c in texto)


def revisar() -> dict:
    problemas: list[str] = []
    # Solo los ficheros **versionados**: la carpeta puede contener restos
    # locales ignorados por .gitignore que no forman parte de la entrega.
    try:
        salida = _git("ls-files", "--", GOBERNANZA).decode("utf-8", "replace")
    except subprocess.CalledProcessError:
        salida = ""
    ficheros = [linea.strip() for linea in salida.splitlines() if linea.strip()]

    for ruta in ficheros:
        bytes_wa = (RAIZ / ruta).read_bytes()
        blob = _blob(ruta)
        if blob is None:
            problemas.append(f"{ruta}: no está en HEAD")
            continue
        if bytes_wa != blob:
            problemas.append(
                f"{ruta}: el árbol de trabajo no coincide con el blob de git "
                f"(sha256 árbol={_sha256(bytes_wa)[:12]}… blob={_sha256(blob)[:12]}…)"
            )

    manifiesto = _entradas_manifiesto()
    coinciden_arbol = 0
    coinciden_blob = 0
    for nombre, digest, tamano in manifiesto:
        base_extract = "docs/gobernanza/03_EVIDENCIA_FLOW/revision_unificacion/extract"
        candidatos = [nombre, f"{base_extract}/{nombre}"]
        encontrado = None
        for candidato in candidatos:
            if (RAIZ / candidato).exists():
                encontrado = candidato
                break
        if encontrado is None:
            problemas.append(f"manifiesto: «{nombre}» no existe en el árbol de trabajo")
            continue
        bytes_wa = (RAIZ / encontrado).read_bytes()
        blob = _blob(encontrado)
        cuadra_arbol = _sha256(bytes_wa) == digest
        cuadra_blob = blob is not None and _sha256(blob) == digest
        if cuadra_arbol:
            coinciden_arbol += 1
        if cuadra_blob:
            coinciden_blob += 1
        if not cuadra_arbol and not cuadra_blob:
            problemas.append(
                f"manifiesto: sha256 de «{nombre}» no cuadra ni con el árbol de "
                f"trabajo ni con el blob de git"
            )
            continue
        if not cuadra_arbol:
            problemas.append(
                f"manifiesto: «{nombre}» cuadra con el blob de git pero NO con el "
                f"árbol de trabajo (el árbol se ha modificado)"
            )
        if tamano is not None and cuadra_blob and tamano != len(blob):
            problemas.append(
                f"manifiesto: «{nombre}» declara {tamano} bytes y el blob de git "
                f"tiene {len(blob)}"
            )

    return {
        "ficheros_gobernanza": len(ficheros),
        "entradas_manifiesto": len(manifiesto),
        "coinciden_con_arbol": coinciden_arbol,
        "coinciden_con_blob_head": coinciden_blob,
        "problemas": problemas,
        "ok": not problemas,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    resultado = revisar()
    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        for problema in resultado["problemas"]:
            print(f"PROBLEMA  {problema}")
        print(
            f"\n{resultado['ficheros_gobernanza']} ficheros de gobernanza versionados, "
            f"{resultado['entradas_manifiesto']} entradas de manifiesto.\n"
            f"Cuadran con el árbol de trabajo: {resultado['coinciden_con_arbol']} · "
            f"cuadran con el blob de HEAD: {resultado['coinciden_con_blob_head']}.\n"
            f"{len(resultado['problemas'])} problemas."
        )
    return 0 if resultado["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
