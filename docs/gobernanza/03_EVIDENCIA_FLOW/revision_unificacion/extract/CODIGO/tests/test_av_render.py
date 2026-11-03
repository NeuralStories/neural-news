"""Fase 6 — composición y exportación local con FFmpeg (T602-T612, T514).

Verifican: validación del plan, huella determinista, pipeline completo
(segmentos simulados → concat → glitch → mp4), formatos 9:16 y 16:9,
duración real medida con ffprobe, descarga con hash, idempotencia,
fallo definitivo con planes inválidos y techo de presupuesto por trabajo.
"""
from __future__ import annotations

import hashlib
import json
import subprocess

import neuralnews.config as config_mod


def storage():
    return config_mod.STORAGE_DIR


def _plan(output_format: str = "9:16", glitch: bool = True, **overrides) -> dict:
    plan = {
        "projectId": "proj-news-001-9x16",
        "storyRef": {"storyId": "news-001", "title": "Noticia de prueba", "revision": None},
        "profileId": "neuralnews-canon-v1",
        "profileVersion": "1.0.0",
        "outputFormat": output_format,
        "studioPresetId": "crt_original_vertical",
        "voice": {"profile": "Algenib", "locale": "es-ES", "speedMultiplier": 1.18, "speedNote": ""},
        "createdAt": "2026-10-28T10:00:00+00:00",
        "planVersion": 1,
        "glitch": glitch,
        "scenes": [
            {
                "sceneIndex": 1,
                "sceneType": "apertura",
                "scriptSnippet": "Buenas tardes, hoy analizamos los avances de la semana.",
                "imagePrompt": "prompt simulado",
                "framing": "plano cercano",
                "movement": "lateral_slide_in",
                "transition": "whip_pan",
                "estDurationSeconds": 2.0,
                "referenceIds": [],
            },
            {
                "sceneIndex": 2,
                "sceneType": "cierre",
                "scriptSnippet": "Y esto ha sido NeuralStories News.",
                "imagePrompt": "prompt simulado",
                "framing": "plano cercano",
                "movement": "chest_punch_zoom",
                "transition": "rgb_glitch_flash",
                "estDurationSeconds": 1.5,
                "referenceIds": [],
            },
        ],
        "warnings": [],
    }
    plan.update(overrides)
    return plan


def probe(path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,codec_name",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), {})
    return {
        "duration": float(data["format"]["duration"]),
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "has_audio": bool(audio),
    }


def test_validacion_del_plan_rechaza_planes_incompletos():
    from neuralnews.services.av_render import validate_render_plan

    errors = validate_render_plan({"projectId": "", "outputFormat": "4:3", "scenes": []})
    assert any("projectId" in e for e in errors)
    assert any("9:16" in e for e in errors)
    assert any("escenas" in e for e in errors)
    broken_scene = _plan()
    broken_scene["scenes"][0]["scriptSnippet"] = "   "
    broken_scene["scenes"][1]["estDurationSeconds"] = 99
    errors = validate_render_plan(broken_scene)
    assert any("locución" in e for e in errors)
    assert any("entre  1 y 30" in e or "entre 1 y 30" in e for e in errors)
    assert validate_render_plan(_plan()) == []


def test_huella_del_plan_determinista():
    from neuralnews.services.av_render import plan_fingerprint

    assert plan_fingerprint(_plan()) == plan_fingerprint(_plan())
    assert plan_fingerprint(_plan()) != plan_fingerprint(_plan(output_format="16:9"))
    changed = _plan()
    changed["scenes"][1]["scriptSnippet"] = "Otro cierre."
    assert plan_fingerprint(_plan()) != plan_fingerprint(changed)


def test_pipeline_completo_9x16_con_glitch_y_descarga(demo_client, worker, app_env):
    from sqlalchemy import select

    from neuralnews.db import session_scope
    from neuralnews.models import RenderOutput

    response = demo_client.post("/api/v1/av/render", json=_plan())
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    assert response.json()["created"] is True
    assert "cola" in response.json()["message"]

    worker()
    detail = demo_client.get(f"/api/v1/jobs/{job_id}").json()
    assert detail["status"] == "DONE", detail.get("error")

    renders = demo_client.get("/api/v1/av/renders", params={"project_id": _plan()["projectId"]}).json()
    assert renders["total"] >= 1
    render = renders["items"][0]

    with session_scope() as db:
        row = db.get(RenderOutput, render["render_id"])
        file_path = row.storage_path
    assert file_path, "el render debe estar registrado con su ruta"

    media = probe(file_path)
    assert (media["width"], media["height"]) == (1080, 1920), "formato vertical 9:16"
    assert media["video_codec"] == "h264" and media["has_audio"] and media["audio_codec"] == "aac"
    expected = 2.0 + 1.5
    assert abs(media["duration"] - expected) <= 0.6, "la duración real coincide con las escenas"

    download = demo_client.get(f"/api/v1/av/renders/{render['render_id']}")
    assert download.status_code == 200
    assert download.headers["content-type"] == "video/mp4"
    assert download.headers["x-output-format"] == "9:16"
    assert download.headers["x-content-sha256"] == render["sha256"]
    assert hashlib.sha256(download.content).hexdigest() == render["sha256"]


def test_exportacion_16x9(demo_client, worker, app_env):
    response = demo_client.post("/api/v1/av/render", json=_plan(output_format="16:9", glitch=False))
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]
    worker()
    from neuralnews.db import session_scope
    from neuralnews.models import Job, RenderOutput
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "DONE", job.error
        row = db.scalars(
            __import__("sqlalchemy").select(RenderOutput).where(RenderOutput.job_id == job_id)
        ).first()
        assert row is not None
        media = probe(row.storage_path)
        assert (media["width"], media["height"]) == (1920, 1080), "formato horizontal 16:9"
        assert row.glitch_applied is False


def test_mismo_plan_reutiliza_el_fichero_sin_recomponer(demo_client, worker, app_env):
    first = demo_client.post("/api/v1/av/render", json=_plan(projectId="proj-dedupe")).json()
    second = demo_client.post("/api/v1/av/render", json=_plan(projectId="proj-dedupe")).json()
    assert first["created"] is True and second["created"] is False
    assert first["job_id"] == second["job_id"]


def test_plan_invalido_falla_de_forma_definitiva_sin_artefacto(demo_client, worker, app_env):
    from neuralnews.db import session_scope
    from neuralnews.models import Job
    from neuralnews.services.av_jobs import enqueue_av_render

    bad_plan = _plan(projectId="proj-roto")
    bad_plan["scenes"][0]["scriptSnippet"] = "   "
    with session_scope() as db:
        job, created = enqueue_av_render(db, bad_plan)
        job_id = job.id
    worker()
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "FAILED", "un plan inválido no se reintentará en vano"
        assert "locución" in (job.error or "")
    assert not list((storage() / "av" / "renders").glob("render-proj-roto-*"))


def test_techo_de_presupuesto_por_trabajo(demo_client, worker, app_env):
    from neuralnews.db import session_scope
    from neuralnews.models import Job
    from neuralnews.services.av_jobs import enqueue_av_render

    # El proveedor simulado declara coste 0; un techo negativo lo bloquea y
    # demuestra que el control por trabajo (T514) está activo.
    with session_scope() as db:
        job, _ = enqueue_av_render(db, _plan(projectId="proj-techo"), max_cost_eur=-1.0)
        job_id = job.id
    worker()
    with session_scope() as db:
        job = db.get(Job, job_id)
        assert job.status == "FAILED"
        assert "techo del trabajo" in (job.error or "")
    assert not list((storage() / "av" / "renders").glob("render-proj-techo-*"))
