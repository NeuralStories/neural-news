"""NN-110.f — Ninguna operación pesada bloquea el hilo de la petición (gate G3).

Criterio: **ningún handler tarda más de 2 s**. Para que la prueba sea
significativa, el proveedor que antes se ejecutaba dentro de la petición se
vuelve **lento a propósito**: si el trabajo volviera a ejecutarse en el hilo,
el handler tardaría 3 s y la prueba fallaría.

Los tres endpoints que se medían:

  - `POST /sources/{id}/transcribe` — antes: yt-dlp/feed/extracción en el hilo.
  - `POST /projects/{id}/montage` — antes: FFmpeg (timeout 600) en el hilo.
  - `POST /projects/{id}/takes/{id}/media` — antes: ffprobe en la subida.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

LIMITE_S = 2.0
PROVEEDOR_LENTO_S = 3.0

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


def _cronometrar(accion) -> tuple[float, object]:
    inicio = time.monotonic()
    resultado = accion()
    return time.monotonic() - inicio, resultado


def test_transcribe_responde_mientras_el_proveedor_trabaja(demo_client, monkeypatch):
    """El handler encola y devuelve; el proveedor lento sigue trabajando aparte."""
    from neuralnews.providers import transcript as transcript_mod

    def _lento(*_args, **_kwargs):
        time.sleep(PROVEEDOR_LENTO_S)
        return None

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _lento)
    src = demo_client.post(
        "/api/v1/sources", json={"url": "https://youtu.be/ccccccccccc"}
    ).json()["source"]["id"]

    transcurrido, r = _cronometrar(
        lambda: demo_client.post(f"/api/v1/sources/{src}/transcribe")
    )

    assert r.status_code == 202, r.text
    assert transcurrido < LIMITE_S, (
        f"el handler tardó {transcurrido:.2f} s: la transcripción sigue en la petición"
    )
    assert r.json()["job_id"] > 0


def test_montage_responde_mientras_ffmpeg_trabaja(demo_client, monkeypatch):
    """El handler encola el montaje; el render lento no bloquea la petición."""
    from neuralnews.services import montage as montage_mod

    def _lento(*_args, **_kwargs):
        time.sleep(PROVEEDOR_LENTO_S)
        return {"ok": True, "path": "x", "duration_s": 8, "segments": 2, "label": "l", "transitions": []}

    monkeypatch.setattr(montage_mod, "build_animatica", _lento)
    proyecto = demo_client.post(
        "/api/v1/projects", json={"name": "Montaje lento", "ratio": "9:16"}
    ).json()

    transcurrido, r = _cronometrar(
        lambda: demo_client.post(f"/api/v1/projects/{proyecto['id']}/montage")
    )

    assert r.status_code == 202, r.text
    assert transcurrido < LIMITE_S, (
        f"el handler tardó {transcurrido:.2f} s: FFmpeg sigue en la petición"
    )


def test_la_subida_no_espera_a_ffprobe(demo_client, monkeypatch):
    """La subida no espera al sondeo: el sondeo es un trabajo aparte."""
    from neuralnews.services import media_library

    def _lento(*_args, **_kwargs):
        time.sleep(PROVEEDOR_LENTO_S)
        return {"probe_status": "OK", "width": 1080, "height": 1920}

    monkeypatch.setattr(media_library, "_ffprobe", _lento)
    proyecto = demo_client.post(
        "/api/v1/projects", json={"name": "Subida lenta", "ratio": "9:16"}
    ).json()
    demo_client.put(
        f"/api/v1/projects/{proyecto['id']}/studio/guion",
        json={"payload": {"scriptText": "Apertura. Cierre."}, "expected_revision": 0},
    )
    demo_client.post(f"/api/v1/projects/{proyecto['id']}/director/plan", json={})
    completo = demo_client.get(f"/api/v1/projects/{proyecto['id']}").json()
    toma = demo_client.post(
        f"/api/v1/projects/{proyecto['id']}/takes",
        json={"shot_id": completo["shots"][0]["id"], "take_number": 1},
    ).json()

    with tempfile.TemporaryDirectory() as td:
        clip = Path(td) / "clip.mp4"
        clip.write_bytes(b"contenido-de-prueba")
        transcurrido, r = _cronometrar(
            lambda: demo_client.post(
                f"/api/v1/projects/{proyecto['id']}/takes/{toma['id']}/media",
                files={"file": ("clip.mp4", clip.read_bytes(), "video/mp4")},
            )
        )

    assert r.status_code == 200, r.text
    assert transcurrido < LIMITE_S, (
        f"la subida tardó {transcurrido:.2f} s: ffprobe sigue dentro de la petición"
    )
    assert r.json()["probe_job_id"] > 0, "el sondeo debe quedar encolado"


def test_los_endpoints_de_lectura_siguen_siendo_rapidos(demo_client, worker):
    """La API de lectura no se ha ralentizado: sigue por debajo del límite."""
    demo_client.post("/api/v1/sources", json={"text": "Una fuente de lectura."})
    worker()
    for ruta in ("/api/v1/sources", "/api/v1/stories", "/api/v1/jobs", "/api/v1/usage"):
        transcurrido, r = _cronometrar(lambda r=ruta: demo_client.get(r))
        assert r.status_code == 200, f"{ruta} → {r.status_code}"
        assert transcurrido < LIMITE_S, f"{ruta} tardó {transcurrido:.2f} s"


@pytest.mark.skipif(FF is None, reason="requiere FFmpeg local (sin Docker)")
def test_el_montaje_real_tarda_mas_que_el_limite_pero_el_handler_no(demo_client, worker):
    """Con FFmpeg de verdad, el handler sigue siendo inmediato (el render, no)."""
    proyecto = demo_client.post(
        "/api/v1/projects", json={"name": "Montaje real", "ratio": "9:16"}
    ).json()
    pid = proyecto["id"]
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={
            "payload": {
                "scriptText": (
                    "Apertura del bloque informativo con el presentador canónico. "
                    "La cifra clave del trimestre se muestra con su fuente verificada. "
                    "Según la compañía, el despliegue llegará a producción pronto. "
                    "Cierre del bloque desde el plató principal."
                )
            },
            "expected_revision": 0,
        },
    )
    plan = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
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
            toma = demo_client.post(
                f"/api/v1/projects/{pid}/takes",
                json={"shot_id": shot["id"], "take_number": i + 1},
            ).json()
            demo_client.post(
                f"/api/v1/projects/{pid}/takes/{toma['id']}/media",
                files={"file": (clip.name, clip.read_bytes(), "video/mp4")},
            )

    transcurrido, r = _cronometrar(
        lambda: demo_client.post(f"/api/v1/projects/{pid}/montage")
    )
    assert r.status_code == 202
    assert transcurrido < LIMITE_S, (
        f"el handler tardó {transcurrido:.2f} s con FFmpeg real: el render sigue en la petición"
    )

    # Y el render ocurre de verdad, en el worker.
    job_id = r.json()["job_id"]
    worker()
    estado = demo_client.get(f"/api/v1/projects/{pid}/montage").json()
    assert estado["animatica"] is not None
    assert estado["animatica"]["duration_s"] >= 8
