"""Crea el proyecto piloto NEURAL NEWS — PILOTO 001 contra la pila en marcha.

Noticia real (Reuters: OPA de Anthropic, valoración 965.000 M$, nov 2026).
Todo se persiste en PostgreSQL. Los bloqueos de activos se dejan honestos.
"""
from __future__ import annotations

import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000").rstrip("/")
client = httpx.Client(base_url=BASE, timeout=60)

FUENTE_URL = "https://www.reuters.com/technology/"
TEXTO_FUENTE = (
    "Reuters — Anthropic prepara su salida a bolsa (noviembre 2026). La compañía confidencialmente "
    "presentó su documentación de OPA en junio de 2026 y después hizo público el fichaje, camino de "
    "convertirse en el primer laboratorio de IA frontera en debutar en bolsa (Reuters Legal). Su "
    "valoración pasó de 61,5 mil millones de dólares (marzo de 2025) a 380 mil millones (febrero de "
    "2026) y a 965 mil millones tras una ronda de 65 mil millones en mayo de 2026. Su ingreso "
    "anualizado superó los 65 mil millones de dólares a finales de julio, desde unos 9 mil millones "
    "a finales de 2025. Referencia: reuters.com/technology/ — URL exacta del artículo pendiente de "
    "captura; contraste humano de las afirmaciones pendiente (estados UNVERIFIED)."
)

GUION = (
    "La mayor valoración de la historia de la inteligencia artificial está a un paso de la bolsa. "
    "Anthropic, la empresa rival de OpenAI, prepara su salida a bolsa con una valoración de 965 mil "
    "millones de dólares. La escalada es meteórica: 61 mil millones en marzo de 2025, 380 mil "
    "millones en febrero de este año, y 965 mil millones tras una ronda de 65 mil millones en mayo. "
    "Según Reuters Legal, la compañía presentó de forma confidencial su documentación en junio y "
    "después la hizo pública, camino de convertirse en el primer laboratorio de inteligencia "
    "artificial frontera en debutar en bolsa. Su ingreso anualizado supera hoy los 65 mil millones "
    "de dólares, frente a los 9 mil millones de finales de 2025. ¿Puede una empresa de tres años de "
    "vida sostener ese precio? Eso lo decidirá el mercado, y lo contaremos aquí, con las cifras a la vista."
)


def main() -> int:
    client.post("/api/v1/auth/demo")
    print("— Sesión demo iniciada")

    src = client.post("/api/v1/sources", json={"text": TEXTO_FUENTE}).json()
    source_id = src["source"]["id"]
    print(f"— Fuente registrada #{source_id} (snapshot manual del reporte de Reuters; ref: {FUENTE_URL})")

    story_id = None
    for _ in range(40):
        detail = client.get(f"/api/v1/sources/{source_id}").json()
        stories = detail.get("stories") or []
        if stories:
            story_id = stories[0]["id"]
            break
        time.sleep(2)
    if not story_id:
        print("FALLO: el worker no generó historia"); return 1
    story = client.get(f"/api/v1/stories/{story_id}").json()
    print(f"— Historia #{story_id} «{story['title'][:60]}…» | afirmaciones: {len(story.get('claims') or [])} (UNVERIFIED)")

    project = client.post("/api/v1/projects", json={
        "name": "NEURAL NEWS — PILOTO 001",
        "ratio": "9:16",
        "story_id": story_id,
        "target_duration_s": 60,
        "format_profile": {"ratio": "9:16", "plataforma": "Short/Reel", "duracion_objetivo": "45–60 s"},
    }).json()
    pid = project["id"]
    print(f"— Proyecto PILOTO 001 creado #{pid} (9:16, duración objetivo 60 s; R-BUG-2: ratio fijado)")

    client.put(f"/api/v1/projects/{pid}/studio/noticias",
               json={"payload": {"story_id": story_id, "seleccion": "noticia vinculada"},
                     "expected_revision": 0})
    client.put(f"/api/v1/projects/{pid}/studio/guion",
               json={"payload": {"scriptText": GUION}, "expected_revision": 0})
    client.put(f"/api/v1/projects/{pid}/studio/personaje",
               json={"payload": {"personaje": "maxDotAi", "estado": "PENDIENTE_DE_VINCULAR",
                                 "nota": "Sin activos aprobados: no se inventa rostro ni voz"},
                     "expected_revision": 0})
    client.put(f"/api/v1/projects/{pid}/studio/fondo",
               json={"payload": {"fondo": "CRT NeuralStories News", "estado": "PENDIENTE_DE_APROBACION",
                                 "nota": "Referencia real no aportada aún"}, "expected_revision": 0})
    client.put(f"/api/v1/projects/{pid}/studio/voz",
               json={"payload": {"voz": "pendiente", "nota": "Sin TTS autorizado; locución pendiente de material"},
                     "expected_revision": 0})
    print("— Pasos Noticias/Guion/Personaje/Fondo/Voz guardados (personaje: maxDotAi PENDIENTE_DE_VINCULAR)")

    plan = client.post(f"/api/v1/projects/{pid}/director/plan", json={"provider_max_clip_s": 8}).json()
    print(f"— Director: {len(plan['beats'])} beats, {len(plan['shots'])} tomas")
    for s in plan["shots"]:
        print(f"    · Toma ventana {s['sequence'] + 1}: {s['shot_kind']} "
              f"({s['start_s']}s→{s['end_s']}s) — {s['rationale'][:70]}…")

    full = client.get(f"/api/v1/projects/{pid}").json()
    for i, shot in enumerate(full["shots"]):
        t = client.post(f"/api/v1/projects/{pid}/takes",
                        json={"shot_id": shot["id"], "take_number": i + 1}).json()
        client.post(f"/api/v1/projects/{pid}/prompts", json={
            "take_id": t["id"],
            "prompt_en": (
                f"Take {i + 1} ({shot['shot_kind']}): news broadcast segment for NeuralStories News "
                f"featuring anchor maxDotAi from the canonical master sheet. Window {shot['start_s']}s–"
                f"{shot['end_s']}s. Literal narration: \"{' '.join(shot['data'].get('beat_texts', []))}\". "
                "Identity continuity; purely optical effects; on-screen numbers come from programmatic graphics only."
            ),
            "explanation_es": f"Ventana {shot['start_s']}s→{shot['end_s']}s; locución continua (el audio no se corta aquí).",
        })
    print(f"— {len(full['shots'])} tomas creadas con prompt v1 (PROMPT_LISTO)")

    graphic = client.post(f"/api/v1/projects/{pid}/graphics", json={
        "title": "Valoración de Anthropic (miles de millones USD)",
        "series": [
            {"label": "mar 2025", "value": 61.5, "unit": "G$"},
            {"label": "feb 2026", "value": 380, "unit": "G$"},
            {"label": "may 2026", "value": 965, "unit": "G$"},
        ],
        "source_note": "Fuente: Reuters — ronda de mayo 2026 (65 G$); verificación humana pendiente",
    }).json()
    svg = client.get(f"/api/v1/projects/{pid}/graphics/{graphic['id']}/svg")
    print(f"— Gráfico programático #{graphic['id']} (SVG {svg.status_code}, valores exactos 61,5/380/965)")

    pkg = client.get(f"/api/v1/projects/{pid}/takes/{full['takes'][0]['id']}/flow-package") if False else None
    maxdot_take = None
    for shot in full["shots"]:
        if shot["shot_kind"] == "FLOW_MAXDOTAI":
            for t in full["takes"]:
                if t["shot_id"] == shot["id"]:
                    maxdot_take = t
    if maxdot_take:
        pkg = client.get(f"/api/v1/projects/{pid}/takes/{maxdot_take['id']}/flow-package").json()
        print(f"— FlowManualPackage de la toma #{maxdot_take['id']}: personaje {pkg['personaje']['a_escoger_en_flow']}, "
              f"referencias adjuntables {len(pkg['referencias']['adjuntables_con_mediaid'])} (mediaId real: ninguna aún)")

    validation = {
        "locucion": "PENDIENTE_POR_ACTIVO — sin TTS autorizado ni pista de voz aportada",
        "tomas_FLOW_MAXDOTAI": "PENDIENTE_POR_ACTIVO — generar en Flow con el paquete e importar el MP4",
        "tomas_GENERATIVE_BROLL": "PENDIENTE_POR_ACTIVO — B-roll generativo pendiente de generación",
        "tomas_DOCUMENTARY": "PENDIENTE_POR_ACTIVO — captura/material auténtico con derechos pendientes",
        "plató_CRT": "PENDIENTE_POR_APROBACION — referencia real no aportada",
        "graficos_y_rótulos": "DISPONIBLES — programáticos (SVG/PNG), valores exactos",
    }
    print("— Validación de materiales del PILOTO (bloqueos honestos):")
    for k, v in validation.items():
        print(f"    · {k}: {v}")

    print(f"\nPILOTO 001 OPERATIVO: proyecto #{pid} — http://localhost:3000/estudio?project={pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
