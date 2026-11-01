"""NN-107 — La producción distingue y gestiona los siete tipos de recurso,
mantiene la narración continua (sin cortes artificiales de 8 s) y los cambios
no regeneran activos independientes (invalidación dirigida, cap. 13)."""
from __future__ import annotations

ALL_KINDS = [
    "USER_VIDEO",          # vídeo propio del propietario
    "FLOW_MAXDOTAI",       # intervención del presentador canónico
    "DOCUMENTARY",         # captura/material auténtico con procedencia
    "DATA_GRAPHIC",        # gráfico programático con cifras exactas
    "GENERATIVE_BROLL",    # B-roll ilustrativo etiquetado
    "TITLE_CARD",          # rótulo programático
    "PENDING",             # recurso o autorización ausentes
]

GUION = (
    "Apertura con el presentador canónico del programa. "
    "El informe atribuye el crecimiento a la inversión en centros de datos, según la empresa. "
    "El sector alcanzó 40 millones de euros durante el último trimestre. "
    "Imágenes ilustrativas del interior de un centro de datos. "
    "Titular: inversión récord en infraestructura. "
    "Cierre del bloque desde el plató principal."
)


def test_the_app_manages_all_seven_shot_kinds(demo_client):
    """Distinción y gestión explícita de presentador, documental, apoyo, B-roll,
    gráficos de datos exactos y rótulos (cap. 7)."""
    project = demo_client.post("/api/v1/projects", json={"name": "Tipos", "ratio": "16:9"}).json()
    pid = project["id"]
    saved = demo_client.put(
        f"/api/v1/projects/{pid}/shots",
        json={"shots": [{"shot_kind": k, "rationale": f"prueba {k}"} for k in ALL_KINDS]},
    )
    assert saved.status_code == 200, saved.text
    full = demo_client.get(f"/api/v1/projects/{pid}").json()
    kinds = [s["shot_kind"] for s in full["shots"]]
    assert kinds == ALL_KINDS
    # Cada toma planificada sobre un tipo distinto queda gestionable
    for shot in full["shots"]:
        take = demo_client.post(f"/api/v1/projects/{pid}/takes",
                                json={"shot_id": shot["id"], "take_number": shot["sequence"] + 1})
        assert take.status_code == 200
    state = demo_client.get(f"/api/v1/projects/{pid}").json()
    assert len(state["takes"]) == len(ALL_KINDS)


def test_narration_is_continuous_and_not_cut_every_eight_seconds(demo_client):
    """La locución es continua: un beat = una frase (incluso >8 s) y las ventanas
    de vídeo agrupan frases por capacidad del proveedor, nunca a mitad de frase."""
    guion = (
        "Primera frase de apertura del bloque informativo. "
        "Segunda frase notablemente larga que describe con detalle técnico cómo el modelo procesa "
        "contextos extensos sin perder coherencia temporal durante toda la ventana de atención. "
        "Tercera frase de cierre."
    )
    project = demo_client.post("/api/v1/projects", json={"name": "Continuidad"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": guion}, "expected_revision": 0},
    )
    plan = demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={}).json()

    beats = plan["beats"]
    assert len(beats) == 3  # una frase = un beat; la frase larga no se parte
    assert max(b["est_seconds"] for b in beats) > 8  # y supera 8 s íntegra
    assert abs(sum(b["est_seconds"] for b in beats) - plan["total_seconds"]) < 0.02

    # Las ventanas de vídeo cubren la narración sin huecos ni solapes
    shots = plan["shots"]
    assert shots[0]["start_s"] == 0
    for prev, cur in zip(shots, shots[1:]):
        assert abs(cur["start_s"] - prev["end_s"]) < 0.02
    assert abs(shots[-1]["end_s"] - plan["total_seconds"]) < 0.02


def test_changes_do_not_regenerate_independent_assets(demo_client):
    """Invalidación dirigida (cap. 13): un cambio del guion marca los gráficos
    derivados para revisión pero NO toca tomas, prompts ni medios importados."""
    project = demo_client.post("/api/v1/projects", json={"name": "Invalidación"}).json()
    pid = project["id"]
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": "Guion original con una cifra de 30 por ciento."}, "expected_revision": 0},
    )
    graphic = demo_client.post(
        f"/api/v1/projects/{pid}/graphics",
        json={"title": "Cifra 30%", "series": [{"label": "x", "value": 30, "unit": "%"}]},
    ).json()
    take = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()
    demo_client.post(
        f"/api/v1/projects/{pid}/prompts",
        json={"take_id": take["id"], "prompt_en": "Prompt v1 estable."},
    )
    demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/media",
        files={"file": ("toma.mp4", b"mp4-estable", "video/mp4")},
    )
    before = demo_client.get(f"/api/v1/projects/{pid}").json()

    # Cambio del guion (cambio factual de arranque)
    changed = demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": "Guion corregido: la cifra real es 42 por ciento."}, "expected_revision": 1},
    ).json()
    assert graphic["id"] in changed["invalidated_graphics"]  # el derivado sí se marca

    after = demo_client.get(f"/api/v1/projects/{pid}").json()
    # …pero los activos independientes NO se regeneran ni se pierden: el MP4
    # importado sigue vinculado y el estado IMPORTADA se conserva; solo se pide
    # revisión del prompt dependiente (needs_review) sin borrar nada.
    media_before = before["takes"][0]["imported_media"]["sha256"]
    assert after["takes"][0]["imported_media"]["sha256"] == media_before
    assert after["takes"][0]["status"] == "IMPORTADA"
    assert after["takes"][0]["needs_review"] is True
    assert len(after["beats"]) == len(before["beats"])

    # Y un cambio en el paso Personaje no invalida los gráficos (regla dirigida:
    # solo afecta a tomas de presentador, que son revisiones, no borrados)
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/personaje",
        json={"payload": {"personaje": "maxDotAi", "nota": "cambio de vestuario"},
              "expected_revision": 0},
    )
    listing = demo_client.get(f"/api/v1/projects/{pid}/graphics").json()
    assert listing["items"][0]["status"] == "INVALIDADO"  # sigue invalidado solo por el guion
    assert len(listing["items"]) == 1  # no se regeneró ni duplicó nada
