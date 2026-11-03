"""Fase 7 — piloto completo simulado (T700-T710).

Recorre el ciclo completo con una noticia de prueba real registrada en el motor
editorial: fuente → noticia → investigación → guion → aprobación → contrato
production_handoff.v1 → plan de producción → composición FFmpeg → descarga
verificada. Sin servicios de pago (activos simulados).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "contracts" / "consumer"))

from neuralnews.db import session_scope  # noqa: E402
from neuralnews.models import Job, RenderOutput  # noqa: E402


def _probe(path) -> dict:
    import subprocess

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), {})
    return {"duration": float(data["format"]["duration"]), "w": video.get("width"), "h": video.get("height"),
            "has_audio": bool(audio)}


def test_piloto_completo_noticia_aprobada_a_video(demo_client, worker, app_env):
    # T700: noticia de prueba con fuente válida registrada (manual, con texto real).
    # Texto del caso de ejemplo DEMO: sus afirmaciones quedan SUPPORTED con evidencia
    # (fixture local), que es lo que exige el traspaso a producción.
    text = (
        "Piloto NeuralStories: Cortexa Labs ha anunciado Radar, su modelo multimodal con un 12% "
        "más de acierto en razonamiento visual según la ficha técnica; lista de espera para demo web "
        "y disponibilidad en el mercado europeo el próximo trimestre."
    )
    payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
    assert detail["stories"], "la fuente debe producir un candidato de noticia"
    story_id = detail["stories"][0]["id"]

    # T701: investigación, guion y aprobación editorial en origen.
    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detail["summary"], "la investigación debe dejar resumen"
    version = detail["script_versions"][-1]
    approval = demo_client.post(
        f"/api/v1/stories/{story_id}/approve", json={"script_version_id": version["id"]}
    )
    assert approval.status_code == 200, approval.text

    # T702: contrato production_handoff.v1 emitido y válido.
    handoff_response = demo_client.get(f"/api/v1/stories/{story_id}/handoff")
    assert handoff_response.status_code == 200, handoff_response.text
    handoff = handoff_response.json()
    assert handoff["stories"][0]["story_id"] == str(story_id)
    assert handoff["stories"][0]["editorial_approval"]["status"] == "approved"
    assert handoff["stories"][0]["sources"], "el contrato conserva las fuentes"

    # T703-T704: Studio recibe la noticia y crea el plan (equivalente al panel).
    from neural_handoff_consumer import HandoffRegistry, import_handoff  # type: ignore

    imported = import_handoff(handoff, HandoffRegistry())
    article = imported[0]
    from neuralnews.services.av_render import plan_fingerprint, validate_render_plan

    plan = {
        "projectId": f"proj-piloto-{story_id}-9x16",
        "storyRef": {"storyId": article["story_id"], "title": article["title"], "revision": article["revision"]},
        "profileId": "neuralnews-canon-v1",
        "profileVersion": "1.0.0",
        "outputFormat": "9:16",
        "glitch": True,
        "scenes": [
            {
                "sceneIndex": 1,
                "sceneType": "apertura",
                "scriptSnippet": article["script"].split("\n\n")[0],
                "imagePrompt": "simulado",
                "framing": "pecho",
                "movement": "lateral_slide_in",
                "transition": "whip_pan",
                "estDurationSeconds": 3.0,
                "referenceIds": [],
            },
            {
                "sceneIndex": 2,
                "sceneType": "cierre",
                "scriptSnippet": article["script"].split("\n\n")[-1],
                "imagePrompt": "simulado",
                "framing": "pecho",
                "movement": "chest_punch_zoom",
                "transition": "rgb_glitch_flash",
                "estDurationSeconds": 2.5,
                "referenceIds": [],
            },
        ],
        "warnings": [],
    }
    assert validate_render_plan(plan) == []

    # T705-T706: producción autorizada (simulada) y composición por el worker.
    render_response = demo_client.post("/api/v1/av/render", json=plan)
    assert render_response.status_code == 200, render_response.text
    job_id = render_response.json()["job_id"]
    worker()
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "DONE", job.error
        row = db.query(RenderOutput).order_by(RenderOutput.id.desc()).first()
        assert row.project_id == plan["projectId"]
        file_path = row.storage_path
        sha256 = row.sha256

    # T707 (automatizada): reproducción, duración, sincronización e integridad.
    media = _probe(file_path)
    assert (media["w"], media["h"]) == (1080, 1920)
    assert media["has_audio"]
    assert abs(media["duration"] - 5.5) <= 0.6
    assert hashlib.sha256(open(file_path, "rb").read()).hexdigest() == sha256

    # T709: exportación descargable con hash en cabeceras.
    renders = demo_client.get("/api/v1/av/renders", params={"project_id": plan["projectId"]}).json()
    download = demo_client.get(f"/api/v1/av/renders/{renders['items'][0]['render_id']}")
    assert download.status_code == 200 and download.headers["content-type"] == "video/mp4"
    # T710: coste registrado = 0 € (proveedor simulado).
    with session_scope() as db:
        usage = db.query(__import__("neuralnews.models", fromlist=["UsageEvent"]).UsageEvent).filter_by(job_id=job_id).all()
        assert usage and all(u.cost_estimate == 0.0 for u in usage)
