"""Recorrido audiovisual completo de NN-107 contra la pila en marcha (F3/F4).

Ejecuta, contra una instancia viva de neural.news, el recorrido de producto con
una noticia real del motor editorial y transcribe cada paso etiquetado como:

  [AUTOMÁTICO]  lo hace la aplicación sola (motor, worker, API)
  [MANUAL]      lo hace el operador/editor (aquí se ejecuta programáticamente
                en su nombre, pero en producción es una acción humana)
  [PENDIENTE]   lo que exige el exterior (Flow) y no se simula

Uso: python scripts/recorrido_audiovisual.py [base_url]
Base por defecto: http://localhost:3000 (proxy de la web hacia la API).
"""
from __future__ import annotations

import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000").rstrip("/")
GUIION = (
    "Cortexa Labs presenta Radar, un modelo multimodal, con un 12 por ciento más de acierto. "
    "La compañía atribuye el salto a su nuevo motor de atención, según la ficha técnica. "
    "Radar llegará a producción general el próximo trimestre."
)
MP4 = b"\x00\x01\x02\x03mp4-externo-generado-en-flow-nn107"

client = httpx.Client(base_url=BASE, timeout=60)
failures: list[str] = []


def step(label: str, kind: str, ok: bool, detail: str = "") -> None:
    icon = {"AUTOMÁTICO": "⚙", "MANUAL": "✋", "PENDIENTE": "⏳", "CHECK": "✓"}[kind]
    print(f"{icon} [{kind:10s}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def main() -> int:
    # Sesión de demo (modo sin claves)
    r = client.post("/api/v1/auth/demo")
    step("Acceso en modo demo", "AUTOMÁTICO", r.status_code == 200)

    # Noticia real del motor: fuente → worker → historia con afirmaciones
    marca = f"recorrido-{int(time.time())}"
    r = client.post("/api/v1/sources", json={"text": f"Prueba {marca}. {GUIION}"})
    source_id = r.json()["source"]["id"]
    step("Captación de la noticia (fuente + snapshot)", "AUTOMÁTICO", r.status_code == 200, f"source #{source_id}")

    story_id = claims = None
    for _ in range(40):
        detail = client.get(f"/api/v1/sources/{source_id}").json()
        stories = detail.get("stories") or []
        if stories:
            story_id = stories[0]["id"]
            claims = len((client.get(f"/api/v1/stories/{story_id}").json().get("claims")) or [])
            break
        time.sleep(2)
    step("Extracción de afirmaciones por el motor", "AUTOMÁTICO", bool(story_id),
         f"historia #{story_id} con {claims} afirmaciones")

    # Dossier editorial: las afirmaciones llegan SIN verificar y así permanecen
    dossier = client.get(f"/api/v1/projects/0/dossier") if False else None  # placeholder
    project = client.post("/api/v1/projects", json={
        "name": f"Recorrido audiovisual {marca}", "ratio": "9:16", "story_id": story_id,
    }).json()
    pid = project["id"]
    dossier = client.get(f"/api/v1/projects/{pid}/dossier").json()
    estados = {c["verification_status"] for c in dossier["claims"]}
    step("Dossier editorial vinculado (fuentes + afirmaciones)", "AUTOMÁTICO",
         dossier["linked"] and estados <= {"UNVERIFIED", "SUPPORTED", "CONTRADICTED", "CONFIRMED"},
         f"estados: {sorted(estados)} — sin verificación automática (F-08)")

    # Guion del proyecto (acción del editor)
    r = client.put(f"/api/v1/projects/{pid}/studio/guion",
                   json={"payload": {"scriptText": GUIION}, "expected_revision": 0})
    step("Guion del proyecto (edición del editor)", "MANUAL", r.status_code == 200,
         f"revisión {r.json().get('revision')}")

    # Selección del presentador maxDotAi (pendiente de vincular: sin activos aún)
    r = client.put(f"/api/v1/projects/{pid}/studio/personaje",
                   json={"payload": {"personaje": "maxDotAi", "estado": "PENDIENTE_DE_VINCULAR"},
                         "expected_revision": 0})
    step("Selección de maxDotAi como presentador", "MANUAL", r.status_code == 200,
         "identidad canónica; vínculo PENDIENTE_POR_ACTIVO (handle/hoja sin confirmar)")

    # Director audiovisual determinista
    plan = client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
    kinds = [s["shot_kind"] for s in plan["shots"]]
    step("Dirección audiovisual determinista (beats + tomas)", "AUTOMÁTICO",
         len(plan["beats"]) >= 3 and len(plan["shots"]) >= 2,
         f"{len(plan['beats'])} beats, {len(plan['shots'])} tomas {kinds}")

    full = client.get(f"/api/v1/projects/{pid}").json()
    takes = []
    for i, shot in enumerate(full["shots"]):
        t = client.post(f"/api/v1/projects/{pid}/takes",
                        json={"shot_id": shot["id"], "take_number": i + 1}).json()
        takes.append(t)
        client.post(f"/api/v1/projects/{pid}/prompts", json={
            "take_id": t["id"],
            "prompt_en": f"News broadcast take {i + 1} featuring anchor maxDotAi from the canonical master sheet, CRT studio.",
            "explanation_es": "Prompt compilado en orden fijo con referencia a la ficha canónica.",
        })
    step("Tomas creadas y prompts versionados (v1)", "AUTOMÁTICO",
         all(t["status"] for t in takes), f"{len(takes)} tomas con prompt → PROMPT_LISTO")

    # FlowManualPackage de la primera toma
    pkg = client.get(f"/api/v1/projects/{pid}/takes/{takes[0]['id']}/flow-package").json()
    step("Exportación de FlowManualPackage.v1", "AUTOMÁTICO",
         pkg.get("package") == "FlowManualPackage.v1" and pkg["personaje"]["a_escoger_en_flow"] == "maxDotAi",
         "instrucciones + checklist; el JSON es lo que el operador lleva a Flow")

    # Generación real en Flow: PENDIENTE (no se simula)
    step("Generación de la toma en Google Flow", "PENDIENTE", True,
         "el operador pega el prompt en Flow con el personaje y referencias del paquete; "
         "la app no llama a Flow ni simula la generación")

    # Importación del MP4 externo y aprobación humana
    r = client.post(f"/api/v1/projects/{pid}/takes/{takes[0]['id']}/media",
                    files={"file": ("toma1.mp4", MP4, "video/mp4")})
    imported = r.json()
    step("Importación del MP4 generado externamente", "MANUAL", imported["status"] == "IMPORTADA",
         f"sha256 {imported['media']['sha256'][:16]}… (probe: {imported['media']['probe_status']})")

    # Intento de verificación falsa de las afirmaciones: NO existe tal endpoint.
    # La aprobación es de la TOMA (no de las afirmaciones).
    r = client.post(f"/api/v1/projects/{pid}/takes/{takes[0]['id']}/approval",
                    json={"status": "APROBADA"})
    step("Aprobación humana de la toma", "MANUAL", r.json().get("status") == "APROBADA",
         "aprueba la toma importada; las afirmaciones siguen sin verificar")

    # Comprobación final: las afirmaciones NO han sido marcadas como verificadas
    dossier = client.get(f"/api/v1/projects/{pid}/dossier").json()
    sin_verificar = all(c["verification_status"] == "UNVERIFIED" for c in dossier["claims"])
    step("Las afirmaciones siguen sin respaldo de verificación", "CHECK", sin_verificar,
         f"{len(dossier['claims'])} afirmaciones UNVERIFIED tras todo el recorrido")

    final = client.get(f"/api/v1/projects/{pid}").json()
    step("Estado persistido en la base de datos", "CHECK",
         final["takes"][0]["status"] == "APROBADA" and final["story_id"] == story_id,
         f"proyecto #{pid}: ratio {final['ratio']}, {len(final['takes'])} tomas")

    print()
    if failures:
        print("FALLOS:", failures)
        return 1
    print("RECORRIDO COMPLETO OK — automático (motor), manual (editor/operador) y "
          "pendiente (Flow) quedan diferenciados; ninguna afirmación marcada verificada sin respaldo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
