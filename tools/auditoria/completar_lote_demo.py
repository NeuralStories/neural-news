"""Auditoría A5 (utilidad) — completa el paso 2.9 (lote de 10 noticias).

El contrato de lote exige exactamente 5 o 10 noticias. Los datos de demo
traen 3, así que se crean las que faltan con el proveedor «manual» (texto
propio, sin red) y se espera a que el worker las convierta en noticias.

Uso:
    python tools/auditoria/completar_lote_demo.py [--cuantas 6]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RAIZ = Path(r"C:/Users/haxth3/Documents/NeuralStories/proyecto final")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cuantas", type=int, default=6)
    args = parser.parse_args()

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def pedir(metodo: str, ruta: str, cuerpo: dict | None = None):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        peticion = urllib.request.Request(
            f"http://127.0.0.1:8000{ruta}", data=datos, method=metodo
        )
        if datos:
            peticion.add_header("Content-Type", "application/json")
        try:
            with opener.open(peticion, timeout=30) as respuesta:
                crudo = respuesta.read().decode("utf-8", "replace")
                try:
                    return respuesta.status, json.loads(crudo)
                except json.JSONDecodeError:
                    return respuesta.status, crudo
        except urllib.error.HTTPError as exc:
            crudo = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(crudo)
            except json.JSONDecodeError:
                return exc.code, crudo

    pedir("POST", "/api/v1/auth/demo", {})

    def historias() -> list[dict]:
        estado, cuerpo = pedir("GET", "/api/v1/stories")
        if isinstance(cuerpo, list):
            return cuerpo
        return cuerpo.get("items", []) if isinstance(cuerpo, dict) else []

    actuales = historias()
    faltan = 10 - len(actuales)
    print(f"historias actuales: {len(actuales)} → faltan {max(0, faltan)}")
    if faltan > 0:
        for indice in range(min(args.cuantas, faltan)):
            # Textos **distintos**: la extracción deduplica por topic_key, así
            # que dos textos idénticos producen una sola noticia.
            estado, cuerpo = pedir(
                "POST",
                "/api/v1/sources",
                {
                    "title": f"Auditoría A5, noticia {indice + 1}",
                    "text": (
                        f"Informe {indice + 1} de la auditoría A5: el ayuntamiento de prueba "
                        f"aprobó la licitacion {indice + 1} por un importe de "
                        f"{indice + 1}00.000 euros segun el boletin oficial."
                    ),
                    "author": "Auditoría A5",
                },
            )
            print(f"  fuente creada: HTTP {estado}")
            time.sleep(1)

    for _ in range(90):
        actuales = historias()
        if len(actuales) >= 10:
            break
        time.sleep(2)
    print(f"historias tras procesar: {len(actuales)}")

    if len(actuales) < 10:
        # Una fuente «manual» no se convierte en noticia sola: el worker solo
        # extrae candidatos si la fuente tiene **contenido** (transcripción o
        # análisis). El flujo es: POST /sources/{id}/transcript y después
        # POST /sources/{id}/process.
        estado, fuentes = pedir("GET", "/api/v1/sources")
        items = fuentes if isinstance(fuentes, list) else (fuentes or {}).get("items", [])
        pendientes = [f for f in items if isinstance(f, dict) and f.get("provider") == "manual"]
        print(f"fuentes manual: {len(pendientes)} → transcripción + procesado")
        for fuente in pendientes:
            id_fuente = fuente.get("id")
            estado, cuerpo = pedir(
                "POST",
                f"/api/v1/sources/{id_fuente}/transcript",
                {
                    "text": (
                        "Texto de prueba para la auditoría A5. La fuente afirma que "
                        "el ayuntamiento de prueba ha aprobado la licitacion de prueba, "
                        "segun el informe trimestral de la aplicacion."
                    )
                },
            )
            if estado not in (200, 201):
                print(f"  transcripción de {id_fuente}: HTTP {estado} {str(cuerpo)[:120]}")
                continue
            pedir("POST", f"/api/v1/sources/{id_fuente}/process", {})
            time.sleep(0.5)
        for _ in range(120):
            actuales = historias()
            if len(actuales) >= 10:
                break
            time.sleep(2)
        print(f"historias tras transcripción y procesado: {len(actuales)}")

    ids = [h.get("id") for h in actuales][:10]
    estado, lote = pedir(
        "POST", "/api/v1/batches", {"story_ids": ids, "target_size": 10, "name": "Auditoria A5"}
    )
    print(f"crear lote: HTTP {estado} → {str(lote)[:200]}")
    id_lote = lote.get("id") if isinstance(lote, dict) else None
    if id_lote:
        estado, exportado = pedir("POST", f"/api/v1/batches/{id_lote}/export", {})
        print(f"exportar: HTTP {estado} → {str(exportado)[:200]}")
        estado, paquete = pedir("GET", f"/api/v1/batches/{id_lote}/package")
        tamano = len(str(paquete))
        print(f"descargar paquete: HTTP {estado} ({tamano} bytes de respuesta)")
        return 0 if estado == 200 else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
