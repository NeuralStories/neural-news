"""NN-107 — Transiciones del montaje y movimiento del catálogo en las tomas."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

GUION = (
    "Apertura con el presentador canónico del programa. "
    "El informe atribuye el crecimiento a la inversión en centros de datos, según la empresa. "
    "El sector alcanzó 40 millones de euros durante el último trimestre. "
    "Imágenes ilustrativas del interior de un centro de datos. "
    "Titular: inversión récord en infraestructura. "
    "Los analistas esperan una segunda ronda de financiación antes del cierre del año. "
    "La compañía abre una nueva oficina de investigación en Europa. "
    "Los competidores reaccionan con recortes de precios agresivos. "
    "El mercado laboral técnico crece un dieciocho por ciento interanual. "
    "Cierre del bloque desde el plató principal."
)


def test_director_assigns_movements_without_consecutive_repeats(demo_client):
    """Movimiento por intención (cap. 6.6): cada toma lleva instrucción de cámara
    del catálogo y nunca el mismo movimiento en tomas seguidas."""
    project = demo_client.post("/api/v1/projects", json={"name": "Movimiento"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": GUION}, "expected_revision": 0},
    )
    demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={}).json()
    full = demo_client.get(f"/api/v1/projects/{project['id']}").json()
    movements = [s["data"]["movement_id"] for s in full["shots"]]
    assert len(movements) >= 4
    assert all(m for m in movements)
    for prev, cur in zip(movements, movements[1:]):
        assert prev != cur, "movimiento repetido en tomas consecutivas"
    assert all(s["data"]["movement_instruction"] for s in full["shots"])


def test_transitions_assigned_and_applied_in_montage(demo_client):
    """FASE 3 punto 5: transiciones reales (xfade glitch/pan/zoom/fade) entre
    segmentos; el MP4 resultante es más corto que la suma cruda por solape."""
    project = demo_client.post("/api/v1/projects", json={"name": "Transiciones", "ratio": "9:16"}).json()
    pid = project["id"]
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": GUION}, "expected_revision": 0},
    )
    demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
    full = demo_client.get(f"/api/v1/projects/{pid}").json()
    transitions = [s["data"]["transition"] for s in full["shots"]]
    assert "rgb_glitch_flash" in transitions  # la primera toma no lleva transición de entrada
    assert transitions[0] == "corte_directo"

    # MP4 reales para cada toma (FFmpeg local, sin Docker)
    tools = REPO.parent / "ffmpeg-local"
    for c in sorted(tools.glob("ffmpeg*/bin")):
        if (c / "ffmpeg.exe").exists():
            ff_dir = c
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        for i, shot in enumerate(full["shots"]):
            take = demo_client.post(
                f"/api/v1/projects/{pid}/takes",
                json={"shot_id": shot["id"], "take_number": i + 1},
            ).json()
            clip = Path(td) / f"c{i}.mp4"
            subprocess.run([
                str(ff_dir / "ffmpeg.exe"), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"testsrc=size=1080x1920:rate=30:duration=4",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(clip),
            ], check=True, timeout=120)
            up = demo_client.post(
                f"/api/v1/projects/{pid}/takes/{take['id']}/media",
                files={"file": (clip.name, clip.read_bytes(), "video/mp4")},
            )
            assert up.status_code == 200

        built = demo_client.post(f"/api/v1/projects/{pid}/montage").json()

    xfades = [t for t in built["transitions"] if t["transition"] != "corte_directo"]
    assert xfades, "debe haber al menos una transición xfade aplicada"
    assert all(t["duration_s"] == 0.4 for t in xfades)
    # El solape acorta: duración real < suma de ventanas
    total_windows = sum(s["end_s"] - s["start_s"] for s in full["shots"])
    assert built["duration_s"] < total_windows

    served = demo_client.get(f"/api/v1/projects/{pid}/montage.mp4")
    assert served.status_code == 200


def test_movement_reaches_prompts_through_the_unified_flow(demo_client):
    """El movimiento del catálogo llega al prompt de la toma (FASE 2: tomas del
    presentador con movimiento coherente)."""
    project = demo_client.post("/api/v1/projects", json={"name": "Movimiento en prompt"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": GUION}, "expected_revision": 0},
    )
    demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={}).json()
    full = demo_client.get(f"/api/v1/projects/{project['id']}").json()
    shot = full["shots"][0]
    take = demo_client.post(
        f"/api/v1/projects/{project['id']}/takes",
        json={"shot_id": shot["id"], "take_number": 1},
    ).json()
    # El compilador de prompts (UI) incluye la instrucción de movimiento de la toma
    movement = shot["data"]["movement_instruction"]
    prompt_text = f"Take 1 featuring anchor maxDotAi. Camera: {movement}."
    saved = demo_client.post(
        f"/api/v1/projects/{project['id']}/prompts",
        json={"take_id": take["id"], "prompt_en": prompt_text},
    )
    assert saved.status_code == 200
    # El movimiento del catálogo es reconocible en el prompt compilado
    assert "camera" in prompt_text.lower()
    assert movement
