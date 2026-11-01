"""NN-107 FASE 3 — Motor de montaje real con FFmpeg (sin Docker).

Genera MP4 válidos con el propio FFmpeg local, los importa como tomas y
construye una animática 9:16 real. Requiere FFmpeg (local sin Docker):
tests/test_tipos_toma_continuidad.py no lo necesita; este sí.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

FFMPEG_DIR = shutil.which("ffmpeg") and Path(shutil.which("ffmpeg")).parent


def _ffmpeg_available() -> Path | None:
    if FFMPEG_DIR:
        return FFMPEG_DIR
    tools = Path(__file__).resolve().parents[2] / "ffmpeg-local"
    for c in sorted(tools.glob("ffmpeg*/bin")):
        if (c / "ffmpeg.exe").exists() or (c / "ffmpeg").exists():
            return c
    return None


FF = _ffmpeg_available()
pytestmark = pytest.mark.skipif(FF is None, reason="requiere FFmpeg local (sin Docker)")


def _valid_mp4(path: Path, seconds: int, color: str) -> None:
    subprocess.run([
        str(FF / ("ffmpeg.exe" if (FF / "ffmpeg.exe").exists() else "ffmpeg")),
        "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"testsrc=size=1080x1920:rate=30:duration={seconds}",
        "-vf", f"hue=h={color}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(path),
    ], check=True, timeout=120)


def test_montage_builds_real_916_mp4_from_imported_clips(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "Montaje", "ratio": "9:16"}).json()
    pid = project["id"]
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": "Apertura del bloque informativo con el presentador canónico. La cifra clave del trimestre se muestra en pantalla con su fuente verificada. Según la compañía, el despliegue llegará a producción en el próximo trimestre. Cierre del bloque desde el plató principal."}, "expected_revision": 0},
    )
    plan = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
    full = demo_client.get(f"/api/v1/projects/{pid}").json()

    with tempfile.TemporaryDirectory() as td:
        for i, shot in enumerate(full["shots"]):
            clip = Path(td) / f"clip{i}.mp4"
            _valid_mp4(clip, 3, i * 40)
            take = demo_client.post(f"/api/v1/projects/{pid}/takes",
                                    json={"shot_id": shot["id"], "take_number": i + 1}).json()
            up = demo_client.post(
                f"/api/v1/projects/{pid}/takes/{take['id']}/media",
                files={"file": (clip.name, clip.read_bytes(), "video/mp4")},
            )
            assert up.status_code == 200, up.text

    built = demo_client.post(f"/api/v1/projects/{pid}/montage")
    assert built.status_code == 200, built.text
    result = built.json()
    assert result["ok"] is True
    assert result["missing"] == []
    assert result["duration_s"] >= 8  # dos ventanas como mínimo

    served = demo_client.get(f"/api/v1/projects/{pid}/montage.mp4")
    assert served.status_code == 200
    assert served.headers["content-type"] == "video/mp4"
    assert len(served.content) > 50_000  # un MP4 real, no un error

    # Persistencia: la animática sobrevive en el paso Resultado
    state = demo_client.get(f"/api/v1/projects/{pid}").json()
    animatica = state["steps"]["resultado"]["payload"]["animatica"]
    assert animatica["duration_s"] == result["duration_s"]


def test_montage_lists_exactly_what_is_missing(demo_client):
    """Sin MP4 importados, el montaje no se construye y lista el material
    que falta con su tipo (cap. 7) — sin fingir producción."""
    project = demo_client.post("/api/v1/projects", json={"name": "Sin materiales"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": "Apertura. Cierre."}, "expected_revision": 0},
    )
    demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={}).json()

    built = demo_client.post(f"/api/v1/projects/{project['id']}/montage")
    assert built.status_code == 409
    detail = built.json()["detail"]
    assert detail["missing"], "debe listar exactamente qué falta"
    for item in detail["missing"]:
        assert item["shot_kind"] in ("FLOW_MAXDOTAI", "GENERATIVE_BROLL", "DOCUMENTARY",
                                     "USER_VIDEO", "PENDING")
        assert item["reason"]
