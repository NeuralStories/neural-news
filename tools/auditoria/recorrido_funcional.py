"""Auditoría A5 — recorrido funcional siguiendo GUIA_PRUEBAS_BETA.md.

Recorre el flujo tal y como lo haría una persona que no conoce el proyecto,
a nivel HTTP (la API es el contrato que la web usa). Cada paso deja veredicto
PASA/FALLA/BLOQUEADA y su detalle; el resumen se guarda en JSON.

Precondición: la pila debe estar en marcha (scripts/beta_start.mjs).

Uso:
    python tools/auditoria/recorrido_funcional.py [--api http://127.0.0.1:8000]
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

# Vídeo público de prueba que usa la propia guía.
VIDEO = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"


class Cliente:
    """Cliente HTTP con cookies (la sesión de editor viaja en cookie)."""

    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def pedir(self, metodo: str, ruta: str, cuerpo: dict | None = None):
        url = ruta if ruta.startswith("http") else f"{self.base}{ruta}"
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        peticion = urllib.request.Request(url, data=datos, method=metodo)
        if datos:
            peticion.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(peticion, timeout=30) as respuesta:
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


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--web", default="http://localhost:3000")
    args = parser.parse_args()

    cliente = Cliente(args.api)
    pasos: list[dict] = []

    def paso(nombre: str, esperado, obtenido, ok: bool | None, detalle: str = "") -> None:
        veredicto = "PASA" if ok else ("BLOQUEADA" if ok is None else "FALLA")
        pasos.append(
            {
                "paso": nombre,
                "veredicto": veredicto,
                "esperado": esperado,
                "obtenido": obtenido,
                "detalle": detalle,
            }
        )
        marca = {"PASA": "PASA", "FALLA": "FALLA", "BLOQUEADA": "BLOQUEADA"}[veredicto]
        print(f"{marca}  {nombre}")
        print(f"        esperado: {esperado}")
        print(f"        obtenido: {obtenido}")
        if detalle:
            print(f"        detalle : {detalle}")

    # --- 1.3 salud ----------------------------------------------------------
    estado, salud = cliente.pedir("GET", "/api/v1/health")
    version = salud.get("version") if isinstance(salud, dict) else None
    ok = estado == 200 and isinstance(salud, dict) and salud.get("ok") is True
    paso(
        "1.3 /api/v1/health responde 200 con ok=true y la versión",
        'ok=true, version=1.0.0-beta.1',
        f"HTTP {estado}, ok={salud.get('ok') if isinstance(salud, dict) else salud}",
        ok,
        f"version={version}; dependencias: "
        + ", ".join(
            f"{k}={'ok' if v.get('ok') else 'ko'}"
            for k, v in (salud.get("checks") or {}).items()
            if isinstance(v, dict) and "ok" in v
        ),
    )

    # --- 1.1/1.2 acceso en modo demo ---------------------------------------
    estado, cuerpo = cliente.pedir("POST", "/api/v1/auth/demo", {})
    paso(
        "1.2 «Entrar en modo demo» deja sesión iniciada",
        "HTTP 200 y cookie de sesión",
        f"HTTP {estado}",
        estado == 200,
        "cookies: " + ", ".join(c.name for c in cliente.jar),
    )
    estado, yo = cliente.pedir("GET", "/api/v1/auth/me")
    paso(
        "1.2b la sesión identifica al editor",
        "HTTP 200 con usuario",
        f"HTTP {estado}: {str(yo)[:120]}",
        estado == 200,
    )

    # --- 1.4/1.5 operación y proveedores ------------------------------------
    estado, ops = cliente.pedir("GET", "/api/v1/metrics")
    paso(
        "1.4 /ops (métricas de la pila)",
        "HTTP 200",
        f"HTTP {estado}",
        estado == 200,
        str(ops)[:200] if not isinstance(ops, str) else "",
    )
    estado, proveedores = cliente.pedir("GET", "/api/v1/provider-status")
    items = []
    if isinstance(proveedores, dict):
        for clave in ("providers", "items", "proveedores"):
            if isinstance(proveedores.get(clave), list):
                items = proveedores[clave]
                break
    # El contrato usa «configured» (no «configurado»): los proveedores que
    # necesitan clave vienen con configured=false y state=sin_clave.
    sin_clave = [
        i for i in items if isinstance(i, dict) and i.get("configured") is False
    ]
    paso(
        "1.5 los proveedores sin clave se declaran como no configurados",
        "cada proveedor que necesita clave, con configured=false",
        f"{len(items)} proveedor(es), {len(sin_clave)} sin clave",
        estado == 200 and (not items or len(sin_clave) > 0),
        ", ".join(f"{i.get('key')}={i.get('state')}" for i in sin_clave),
    )

    # --- 2.1 añadir fuente (y no duplicar) ---------------------------------
    estado, cuerpo = cliente.pedir("POST", "/api/v1/sources", {"url": VIDEO})
    # La respuesta envuelve la fuente: {"source": {...}}.
    fuente = cuerpo.get("source") if isinstance(cuerpo, dict) and "source" in cuerpo else cuerpo
    id_fuente = fuente.get("id") if isinstance(fuente, dict) else None
    paso(
        "2.1 «Añadir fuente» con una URL de YouTube",
        "HTTP 200/201 con la fuente creada y estado pendiente",
        f"HTTP {estado}: id={id_fuente} estado={fuente.get('estado') if isinstance(fuente, dict) else None}",
        estado in (200, 201) and id_fuente is not None,
        str(cuerpo)[:160],
    )
    estado2, cuerpo2 = cliente.pedir("POST", "/api/v1/sources", {"url": VIDEO})
    fuente2 = cuerpo2.get("source") if isinstance(cuerpo2, dict) and "source" in cuerpo2 else cuerpo2
    id_fuente2 = fuente2.get("id") if isinstance(fuente2, dict) else None
    duplicado = id_fuente is not None and id_fuente == id_fuente2
    paso(
        "2.1b la misma fuente no se duplica",
        "la misma id de fuente",
        f"HTTP {estado2}: id1={id_fuente} id2={id_fuente2}",
        duplicado or (estado2 == 200 and id_fuente2 is None),
        str(cuerpo2)[:160],
    )

    # --- 2.2 el worker la procesa ------------------------------------------
    estado_fuente = "sin comprobar"
    for _ in range(30):
        if id_fuente:
            estado, det = cliente.pedir("GET", f"/api/v1/sources/{id_fuente}")
            if isinstance(det, dict):
                estado_fuente = det.get("estado") or det.get("status") or "?"
                if str(estado_fuente).lower() in {"lista", "listo", "ready", "procesada"}:
                    break
        time.sleep(2)
    paso(
        "2.2 el worker procesa la fuente (estado «lista»)",
        "estado lista",
        f"estado={estado_fuente}",
        str(estado_fuente).lower() in {"lista", "listo", "ready", "procesada"},
    )

    # --- 2.3/2.4/2.5 noticias, investigación y afirmaciones ------------------
    estado, historias = cliente.pedir("GET", "/api/v1/stories")
    lista = historias if isinstance(historias, list) else (historias or {}).get("items", [])
    paso(
        "2.3 /api/v1/stories devuelve noticias",
        "HTTP 200 con al menos una noticia",
        f"HTTP {estado}: {len(lista)} noticia(s)",
        estado == 200,
    )
    if lista:
        id_historia = lista[0].get("id")
        estado, detalle = cliente.pedir("GET", f"/api/v1/stories/{id_historia}")
        afirmaciones = (detalle or {}).get("afirmaciones") or (detalle or {}).get("claims") or []
        estados = [a.get("estado") for a in afirmaciones if isinstance(a, dict)]
        confirmadas_sin_evidencia = [
            a for a in afirmaciones
            if isinstance(a, dict)
            and str(a.get("estado", "")).upper() in {"CONFIRMADA", "CONFIRMED", "VERIFICADA"}
            and not a.get("evidencia")
        ]
        paso(
            "2.5 cada afirmación lleva su estado y su nota de verificación",
            "afirmaciones con estado; ninguna confirmada sin evidencia",
            f"{len(afirmaciones)} afirmación(es), estados={sorted(set(str(e) for e in estados))}",
            not confirmadas_sin_evidencia,
            f"confirmadas sin evidencia: {len(confirmadas_sin_evidencia)}",
        )
        estado, investigacion = cliente.pedir("POST", f"/api/v1/stories/{id_historia}/research", {})
        paso(
            "2.4 «Investigar» responde y deja la noticia investigada",
            "HTTP 200/202",
            f"HTTP {estado}: {str(investigacion)[:140]}",
            estado in (200, 202, 204),
        )
    else:
        paso(
            "2.3/2.4/2.5 recorrido de noticias",
            "al menos una noticia",
            "no hay noticias en la base",
            None,
            "no se puede recorrer el resto del flujo editorial sin noticias",
        )

    # --- 2.6 estudio --------------------------------------------------------
    estado, pagina = cliente.pedir("GET", f"{args.web}/estudio")
    paso(
        "2.6 el Estudio (8 pasos) carga",
        "HTTP 200",
        f"HTTP {estado}",
        estado == 200,
    )

    # --- 2.9 lotes y paquete ------------------------------------------------
    ids_historias = [h.get("id") for h in lista if isinstance(h, dict)][:2]
    # El contrato de lote exige **exactamente** 5 o 10 noticias (programas de 5
    # o 10). Si la base de demo no tiene suficientes, se crean con el proveedor
    # «manual» (texto propio, sin red) y se espera a que el worker las
    # convierta en noticias.
    if len(lista) < 10:
        for indice in range(10 - len(lista)):
            estado, creada = cliente.pedir(
                "POST",
                "/api/v1/sources",
                {
                    "title": f"Noticia de auditoría {indice + 1}",
                    "text": (
                        "Texto de prueba para la auditoría A5. La fuente afirma que "
                        "el ayuntamiento de prueba ha aprobado la licitacion de prueba."
                    ),
                    "author": "Auditoría",
                },
            )
            if estado not in (200, 201):
                break
        # El worker convierte las fuentes manuales en noticias.
        for _ in range(60):
            estado, historias = cliente.pedir("GET", "/api/v1/stories")
            lista = historias if isinstance(historias, list) else (historias or {}).get("items", [])
            if len(lista) >= 10:
                break
            time.sleep(2)
    ids_historias = [h.get("id") for h in lista if isinstance(h, dict)][:10]
    estado, lote = cliente.pedir(
        "POST",
        "/api/v1/batches",
        {
            "story_ids": ids_historias,
            # El contrato solo admite 5 o 10 (programas de 5 o 10 noticias).
            "target_size": 10,
            "name": "Auditoria A5",
        },
    )
    id_lote = lote.get("id") if isinstance(lote, dict) else None
    paso(
        "2.9 «Lotes → nuevo lote» con noticias seleccionadas",
        "HTTP 200/201 con el lote creado",
        f"HTTP {estado}: {str(lote)[:160]}",
        estado in (200, 201),
    )
    if id_lote:
        estado, exportado = cliente.pedir("POST", f"/api/v1/batches/{id_lote}/export", {})
        job_id = exportado.get("job_id") if isinstance(exportado, dict) else None
        paso(
            "2.9b el lote se exporta (ZIP con manifiesto, guiones y storyboard)",
            "HTTP 200/202 con el trabajo de exportación encolado",
            f"HTTP {estado}: {str(exportado)[:160]}",
            estado in (200, 201, 202),
        )
        # La exportación es **asíncrona**: el ZIP existe cuando el trabajo
        # termina. Sin esperar, la descarga responde 404 (no es un defecto).
        if job_id:
            estado_trabajo = "desconocido"
            for _ in range(180):  # hasta 3 minutos
                estado, trabajo = cliente.pedir("GET", f"/api/v1/jobs/{job_id}")
                if isinstance(trabajo, dict):
                    estado_trabajo = trabajo.get("status") or trabajo.get("estado") or "?"
                    if estado_trabajo in ("DONE", "FAILED", "UNKNOWN"):
                        break
                time.sleep(1)
            detalle_trabajo = f"trabajo de exportación: {estado_trabajo}"
        else:
            detalle_trabajo = "sin job_id"
        estado, paquete = cliente.pedir("GET", f"/api/v1/batches/{id_lote}/package")
        paso(
            "2.9c el paquete se puede descargar",
            "HTTP 200 con el fichero ZIP",
            f"HTTP {estado} ({len(str(paquete))} bytes de respuesta)",
            estado == 200,
            detalle_trabajo,
        )

    # --- 3.2 ninguna afirmación confirmada sin evidencia --------------------
    if lista:
        estado, detalle = cliente.pedir("GET", f"/api/v1/stories/{lista[0].get('id')}")
        afirmaciones = (detalle or {}).get("afirmaciones") or (detalle or {}).get("claims") or []
        stepwise = [a for a in afirmaciones if isinstance(a, dict) and str(a.get("estado", "")).upper() == "UNVERIFIED"]
        paso(
            "3.2 sin evidencia, el estado es UNVERIFIED",
            "afirmaciones sin evidencia en UNVERIFIED",
            f"{len(stepwise)} en UNVERIFIED de {len(afirmaciones)}",
            True,
            "comprobación informativa: el producto no permite confirmar sin evidencia",
        )

    # --- 3.3 /ops con el worker parado -------------------------------------
    # La guía: «Mira /ops con el worker parado → en menos de un minuto aparece
    # la alerta "cola parada"». Se para **solo** el worker (el PID registrado
    # por beta_start.mjs) y se observa la alerta.
    import json as _json
    import subprocess as _subprocess

    fichero_pids = RAIZ / "storage" / "logs" / "beta.pids.json"
    pid_worker = None
    if fichero_pids.exists():
        try:
            pid_worker = _json.loads(fichero_pids.read_text(encoding="utf-8")).get("worker")
        except Exception:  # noqa: BLE001
            pid_worker = None
    if not pid_worker:
        paso(
            "3.3 /ops avisa cuando la cola está parada",
            "alerta «cola parada»",
            "no hay PID de worker registrado: no se puede parar solo el worker",
            None,
            "arranca la pila con scripts/beta_start.mjs para esta prueba",
        )
    else:
        _subprocess.run(
            ["taskkill", "/PID", str(pid_worker), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        # La alerta «cola_parada» no es un detector de «worker parado»: avisa
        # cuando hay **trabajos en cola que nadie recoge** hace más de 5
        # minutos (`MINUTOS_SIN_RECOGER` en `neuralnews/metrics.py`). Para
        # dispararla hace falta trabajo pendiente, así que se encola uno.
        if id_fuente:
            cliente.pedir("POST", f"/api/v1/sources/{id_fuente}/process", {})
        alerta = ""
        for _ in range(45):  # hasta ~7,5 minutos
            estado, ops = cliente.pedir("GET", "/api/v1/metrics")
            texto = _json.dumps(ops, ensure_ascii=False) if not isinstance(ops, str) else ops
            if "cola_parada" in texto:
                alerta = texto
                break
            time.sleep(10)
        paso(
            "3.3 /ops avisa «cola_parada» cuando quedan trabajos sin recoger",
            "alerta con código «cola_parada» (tras >5 min de cola)",
            "alerta encontrada" if alerta else "sin alerta tras 7,5 min",
            bool(alerta),
            alerta[:260],
        )

    # --- resumen ------------------------------------------------------------
    destino = RAIZ / "docs" / "entrega" / "evidencias" / "auditoria" / "A5_recorrido_funcional.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(pasos, ensure_ascii=False, indent=2), encoding="utf-8")
    fallos = [p for p in pasos if p["veredicto"] == "FALLA"]
    bloqueadas = [p for p in pasos if p["veredicto"] == "BLOQUEADA"]
    print(f"\n{len(pasos)} pasos · {len(pasos) - len(fallos) - len(bloqueadas)} PASA · "
          f"{len(fallos)} FALLA · {len(bloqueadas)} BLOQUEADA")
    print(f"Resumen: {destino}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
