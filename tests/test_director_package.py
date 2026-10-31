"""NN-107 F3 — Director audiovisual determinista y FlowManualPackage.

Comprueba el recorrido vertical del cap. 7: guion → beats (locución continua,
sin cortes impuestos de 8 s) → tomas por capacidad del proveedor → prompts
versionados → paquete manual exportable para Flow.
"""
from __future__ import annotations

GUION_CIFRAS = (
    "Cortexa Labs presenta Radar con un 12 por ciento más de acierto. "
    "La compañía atribuye el salto a su nuevo motor de atención. "
    "Los centros de datos europeos ya prueban el modelo. "
    "Radar llegará a producción el próximo trimestre."
)

GUION_CITA = (
    "Bienvenidos a NeuralStories News. Soy maxDotAi. "
    "Según la agencia, el satélite entró en órbita sin incidencias. "
    "Gracias por acompañarnos."
)


def _setup_proyecto_con_guion(demo_client) -> tuple[int, int]:
    project = demo_client.post(
        "/api/v1/projects", json={"name": "F3 — producción", "ratio": "16:9"}
    ).json()
    save = demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": GUION_CIFRAS}, "expected_revision": 0},
    )
    assert save.status_code == 200, save.text
    return project["id"], save.json()["revision"]


# ------------------------------------------------------------------ director


def test_director_is_deterministic_and_persists_beats_and_shots(demo_client):
    pid, _ = _setup_proyecto_con_guion(demo_client)
    first = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
    second = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()

    assert first["beats"] == second["beats"]
    assert first["shots"] == second["shots"]

    full = demo_client.get(f"/api/v1/projects/{pid}").json()
    assert len(full["beats"]) == len(first["beats"])
    assert len(full["shots"]) == len(first["shots"])


def test_director_never_forces_eight_second_cuts(demo_client):
    """F-05: una frase larga permanece entera; los cortes solo agrupan frases."""
    guion_largo = (
        "El consejo de administración aprobó por unanimidad una inversión de 40 millones de euros "
        "para modernizar la red de centros de datos durante los próximos tres ejercicios fiscales completos."
    )
    project = demo_client.post("/api/v1/projects", json={"name": "F5"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": guion_largo}, "expected_revision": 0},
    )
    plan = demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={}).json()

    assert len(plan["beats"]) == 1  # una sola frase → un solo beat, sin corte a 8 s
    assert plan["beats"][0]["est_seconds"] > 8  # y supera los 8 s sin partirse
    assert len(plan["shots"]) == 1  # la toma conserva la frase íntegra


def test_director_applies_chapter_seven_rules_and_covers_timeline(demo_client):
    pid, _ = _setup_proyecto_con_guion(demo_client)
    plan = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()

    shots = plan["shots"]
    kinds = [s["shot_kind"] for s in shots]
    # Reglas cap. 7: cifra exacta → DATA_GRAPHIC; apertura y cierre → presentador.
    assert "DATA_GRAPHIC" in kinds
    assert kinds[0] in ("FLOW_MAXDOTAI", "DATA_GRAPHIC")
    assert kinds[-1] == "FLOW_MAXDOTAI"
    for s in shots:
        assert s["rationale"], "cada toma registra por qué se ve eso"

    # Cobertura temporal sin huecos: primera toma en 0 y tomas contiguas.
    assert shots[0]["start_s"] == 0
    for prev, cur in zip(shots, shots[1:]):
        assert abs(cur["start_s"] - prev["end_s"]) < 0.02

    # La proporción del proyecto no cambia al planificar (R-BUG-2).
    project = demo_client.get(f"/api/v1/projects/{pid}").json()
    assert project["ratio"] == "16:9"


def test_director_requires_a_script(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "sin guion"}).json()
    response = demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={})
    assert response.status_code == 409


def test_director_maps_quotes_to_documentary(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "Cita"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": GUION_CITA}, "expected_revision": 0},
    )
    plan = demo_client.post(f"/api/v1/projects/{project['id']}/director/plan", json={}).json()
    kinds = [s["shot_kind"] for s in plan["shots"]]
    assert "DOCUMENTARY" in kinds  # «Según la agencia…» → material auténtico


# ------------------------------------------------------------------ paquete manual


def test_flow_manual_package_requires_prompt_and_carries_full_instructions(demo_client):
    pid, _ = _setup_proyecto_con_guion(demo_client)
    plan = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
    full = demo_client.get(f"/api/v1/projects/{pid}").json()
    take = demo_client.post(
        f"/api/v1/projects/{pid}/takes", json={"shot_id": full["shots"][0]["id"], "take_number": 1}
    ).json()

    # Sin prompt no hay paquete: prompt preparado ≠ vídeo generado
    empty = demo_client.get(f"/api/v1/projects/{pid}/takes/{take['id']}/flow-package")
    assert empty.status_code == 409

    created = demo_client.post(
        f"/api/v1/projects/{pid}/prompts",
        json={
            "take_id": take["id"],
            "prompt_en": "News broadcast segment featuring anchor maxDotAi in the CRT studio, 16:9.",
            "explanation_es": "Plano del presentador sobre el plató CRT canónico.",
            "constraints": ["Mantener la identidad de maxDotAi", "Sin rótulos que tapeen el rostro"],
        },
    )
    assert created.status_code == 200, created.text

    package = demo_client.get(f"/api/v1/projects/{pid}/takes/{take['id']}/flow-package").json()
    assert package["package"] == "FlowManualPackage.v1"
    assert package["personaje"]["a_escoger_en_flow"] == "maxDotAi"
    assert package["prompt"]["prompt_en"].startswith("News broadcast segment")
    assert package["prompt"]["content_hash"]
    assert package["ratio"] == "16:9"
    assert "importar_mp4_resultado" in str(package["checklist"])
    assert "no llama a Flow" in package["descargo"]
    assert any("MP4" in w or "impórtalo" in w for w in package["warnings"])


def test_prompt_versions_accumulate_and_take_becomes_prompt_ready(demo_client):
    pid, _ = _setup_proyecto_con_guion(demo_client)
    plan = demo_client.post(f"/api/v1/projects/{pid}/director/plan", json={}).json()
    take = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()

    v1 = demo_client.post(
        f"/api/v1/projects/{pid}/prompts",
        json={"take_id": take["id"], "prompt_en": "Primera versión del prompt."},
    ).json()
    v2 = demo_client.post(
        f"/api/v1/projects/{pid}/prompts",
        json={"take_id": take["id"], "prompt_en": "Segunda versión ajustada del prompt."},
    ).json()
    assert (v1["version"], v2["version"]) == (1, 2)
    assert v2["take_status"] == "PROMPT_LISTO"
