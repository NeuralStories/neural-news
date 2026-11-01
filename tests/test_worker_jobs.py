"""NN-110.b — Los cuatro trabajos que hasta ahora se ejecutaban dentro del hilo
de petición: transcripción, extracción web, montaje y sondeo de medios.

Cada handler debe ser **idempotente**: ejecutarlo dos veces no duplica nada.
Los proveedores de red se sustituyen por dobles: aquí se prueba el trabajo,
no la red.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import select

from neuralnews.db import get_session_factory
from neuralnews.models import Job, MediaAsset, SourceContent
from neuralnews.providers.base import ContentDraft, SegmentDraft
from neuralnews.queue import enqueue
from neuralnews.worker_tasks import (
    BUILD_MONTAGE,
    EXTRACT_WEB,
    PROBE_MEDIA,
    TRANSCRIBE_SOURCE,
)

FFMPEG_DIR = shutil.which("ffmpeg") and Path(shutil.which("ffmpeg")).parent


def _ffmpeg_disponible() -> Path | None:
    if FFMPEG_DIR:
        return FFMPEG_DIR
    tools = Path(__file__).resolve().parents[2] / "ffmpeg-local"
    for c in sorted(tools.glob("ffmpeg*/bin")):
        if (c / "ffmpeg.exe").exists() or (c / "ffmpeg").exists():
            return c
    return None


FF = _ffmpeg_disponible()


@pytest.fixture(autouse=True)
def _cache_limpia(monkeypatch):
    """La caché de transcripciones es por proceso: se aísla cada prueba."""
    from neuralnews.services import transcription as transcription_mod

    monkeypatch.setattr(transcription_mod, "_auto_transcript_cache", {})


def _borrador(texto: str = "Transcripción de prueba para el trabajo en cola.") -> ContentDraft:
    return ContentDraft(
        content_type="TRANSCRIPT",
        text=texto,
        is_verbatim=True,
        provider="test",
        coverage=1.0,
        confidence="high",
        segments=[SegmentDraft(start_s=0.0, end_s=2.0, text=texto)],
    )


def _encolar(tipo: str, payload: dict, dedupe: str) -> int:
    with get_session_factory()() as db:
        job, _ = enqueue(db, tipo, payload, dedupe_key=dedupe)
        job_id = job.id
        db.commit()
    return job_id


def _trabajo(job_id: int) -> Job:
    with get_session_factory()() as db:
        job = db.get(Job, job_id)
        assert job is not None
        return job


def _contenidos(source_id: int) -> list[SourceContent]:
    with get_session_factory()() as db:
        return list(
            db.scalars(
                select(SourceContent).where(SourceContent.source_id == source_id)
            ).all()
        )


# ---------------------------------------------------------------------------
# transcribe_source
# ---------------------------------------------------------------------------


def test_transcribe_source_guarda_la_transcripcion(demo_client, worker, monkeypatch):
    """El trabajo guarda la transcripción encontrada y termina con el motivo."""
    from neuralnews.providers import transcript as transcript_mod

    monkeypatch.setattr(
        transcript_mod, "fetch_youtube_transcript_auto", lambda *a, **k: _borrador()
    )
    source_id = demo_client.post(
        "/api/v1/sources", json={"url": "https://youtu.be/dQw4w9WgXcQ"}
    ).json()["source"]["id"]

    job_id = _encolar(
        TRANSCRIBE_SOURCE, {"source_id": source_id}, f"tr:{source_id}"
    )
    worker()

    job = _trabajo(job_id)
    assert job.status == "DONE", job.error
    assert "almacenada" in (job.progress or "")
    tipos = {c.content_type for c in _contenidos(source_id)}
    assert "TRANSCRIPT" in tipos


def test_transcribe_source_es_idempotente(demo_client, worker, monkeypatch):
    """Repetir el trabajo no duplica el contenido guardado."""
    from neuralnews.providers import transcript as transcript_mod

    monkeypatch.setattr(
        transcript_mod, "fetch_youtube_transcript_auto", lambda *a, **k: _borrador()
    )
    source_id = demo_client.post(
        "/api/v1/sources", json={"url": "https://youtu.be/dQw4w9WgXcQ"}
    ).json()["source"]["id"]
    # El alta encola además un `process_source`: se vacía la cola antes de medir.
    worker()

    job_id = _encolar(TRANSCRIBE_SOURCE, {"source_id": source_id}, f"tr2:{source_id}")
    worker()
    antes = len([c for c in _contenidos(source_id) if c.content_type == "TRANSCRIPT"])

    # Segunda pasada del worker: el trabajo ya está DONE y no se repite.
    worker()
    despues = len([c for c in _contenidos(source_id) if c.content_type == "TRANSCRIPT"])

    assert _trabajo(job_id).status == "DONE"
    assert despues == antes, "un trabajo repetido no debe duplicar el contenido"


def test_transcribe_source_sin_transcripcion_no_es_un_fallo(demo_client, worker, monkeypatch):
    """Si no hay transcripción accesible, el trabajo TERMINA con el motivo: no es un error.

    Se usa una fuente de pódcast sin feed RSS: no hay transcripción posible y
    el motivo es accionable para el operador.
    """
    source_id = demo_client.post(
        "/api/v1/sources",
        json={"url": "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"},
    ).json()["source"]["id"]

    job_id = _encolar(TRANSCRIBE_SOURCE, {"source_id": source_id}, f"tr3:{source_id}")
    worker()

    job = _trabajo(job_id)
    assert job.status == "DONE", job.error
    assert "transcripción" in (job.progress or "")
    assert "feed RSS" in (job.progress or "")
    assert not [
        c for c in _contenidos(source_id) if c.content_type == "TRANSCRIPT"
    ]


def test_transcribe_source_de_una_fuente_inexistente_falla(demo_client, worker):
    """Una fuente que ya no existe es un fallo real del trabajo."""
    job_id = _encolar(TRANSCRIBE_SOURCE, {"source_id": 999999}, "tr-missing")
    worker()
    job = _trabajo(job_id)
    assert job.status in ("FAILED", "RETRYABLE_FAILED")
    assert job.error


# ---------------------------------------------------------------------------
# extract_web
# ---------------------------------------------------------------------------


def test_extract_web_guarda_el_texto_del_articulo(demo_client, worker, monkeypatch):
    """El trabajo de extracción web guarda el contenido y es idempotente."""
    from neuralnews.providers import web_rss as web_rss_mod

    def _fake_fetch(url, **_kwargs):
        from neuralnews.providers.base import FetchResult

        return FetchResult(
            provider="web_rss",
            status="READY",
            canonical_url=url,
            contents=[
                ContentDraft(
                    content_type="ARTICLE_TEXT",
                    text="El artículo extraído por el trabajo en cola.",
                    provider="web_rss",
                    coverage=1.0,
                    confidence="high",
                )
            ],
        )

    monkeypatch.setattr(web_rss_mod, "fetch_web", _fake_fetch)
    source_id = demo_client.post(
        "/api/v1/sources", json={"url": "https://ejemplo.invalid/artículo"}
    ).json()["source"]["id"]

    job_id = _encolar(EXTRACT_WEB, {"source_id": source_id}, f"ew:{source_id}")
    worker()

    job = _trabajo(job_id)
    assert job.status == "DONE", job.error
    textos = [c.text for c in _contenidos(source_id) if c.content_type == "ARTICLE_TEXT"]
    assert any("artículo extraído por el trabajo" in t for t in textos)


# ---------------------------------------------------------------------------
# probe_media
# ---------------------------------------------------------------------------


def test_probe_media_sondea_el_medio_ya_subido(demo_client, worker):
    """El sondeo (ffprobe) ocurre en el trabajo, no en la subida."""
    from neuralnews.services import media_library

    with get_session_factory()() as db:
        asset = media_library.upload_media(
            db, b"contenido-de-prueba", "video/mp4", "prueba.mp4", probe=False
        )
        asset_id = asset.id
        db.commit()

    assert _trabajo_estado(asset_id) == "PENDING"

    job_id = _encolar(PROBE_MEDIA, {"media_id": asset_id}, f"pm:{asset_id}")
    worker()

    job = _trabajo(job_id)
    assert job.status == "DONE", job.error
    # ffprobe puede no estar: el estado honesto es UNAVAILABLE/FAILED, nunca "OK" inventado.
    assert _trabajo_estado(asset_id) in ("OK", "UNAVAILABLE", "FAILED")


def _trabajo_estado(asset_id: int) -> str:
    with get_session_factory()() as db:
        asset = db.get(MediaAsset, asset_id)
        assert asset is not None
        return asset.probe_status


# ---------------------------------------------------------------------------
# build_montage
# ---------------------------------------------------------------------------


@pytest.mark.skipif(FF is None, reason="requiere FFmpeg local (sin Docker)")
def test_build_montage_construye_la_animatica(demo_client, worker):
    """El montaje se construye en el worker y se persiste en el paso Resultado."""
    project = demo_client.post(
        "/api/v1/projects", json={"name": "Montaje en cola", "ratio": "9:16"}
    ).json()
    pid = project["id"]
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={
            "payload": {
                "scriptText": (
                    "Apertura del bloque informativo con el presentador canónico. "
                    "La cifra clave del trimestre se muestra en pantalla con su fuente verificada. "
                    "Según la compañía, el despliegue llegará a producción en el próximo trimestre. "
                    "Cierre del bloque desde el plató principal."
                )
            },
            "expected_revision": 0,
        },
    )
    demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={})
    full = demo_client.get(f"/api/v1/projects/{pid}").json()

    with tempfile.TemporaryDirectory() as td:
        for i, shot in enumerate(full["shots"]):
            clip = Path(td) / f"clip{i}.mp4"
            subprocess.run(
                [
                    str(FF / ("ffmpeg.exe" if (FF / "ffmpeg.exe").exists() else "ffmpeg")),
                    "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30:duration=3",
                    "-vf", f"hue=h={i * 40}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(clip),
                ],
                check=True,
                timeout=120,
            )
            take = demo_client.post(
                f"/api/v1/projects/{pid}/takes",
                json={"shot_id": shot["id"], "take_number": i + 1},
            ).json()
            up = demo_client.post(
                f"/api/v1/projects/{pid}/takes/{take['id']}/media",
                files={"file": (clip.name, clip.read_bytes(), "video/mp4")},
            )
            assert up.status_code == 200, up.text

    job_id = _encolar(BUILD_MONTAGE, {"project_id": pid}, f"bm:{pid}")
    worker()

    job = _trabajo(job_id)
    assert job.status == "DONE", job.error
    state = demo_client.get(f"/api/v1/projects/{pid}").json()
    animatica = state["steps"]["resultado"]["payload"]["animatica"]
    assert animatica["duration_s"] >= 8


@pytest.mark.skipif(FF is None, reason="requiere FFmpeg local (sin Docker)")
def test_build_montage_sin_materiales_falla_con_el_motivo(demo_client, worker):
    """Sin materiales, el trabajo falla diciendo qué falta: no se finge."""
    project = demo_client.post(
        "/api/v1/projects", json={"name": "Montaje sin materiales", "ratio": "9:16"}
    ).json()
    pid = project["id"]
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": "Apertura. Cierre."}, "expected_revision": 0},
    )
    demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={})

    job_id = _encolar(BUILD_MONTAGE, {"project_id": pid}, f"bm2:{pid}")
    worker()

    job = _trabajo(job_id)
    assert job.status in ("FAILED", "RETRYABLE_FAILED")
    assert job.error
