"""NN-107 FASE 1 — Invalidación exclusiva de dependencias.

Modificar el guion debe invalidar EXCLUSIVAMENTE lo que depende del texto:
gráficos derivados y tomas cuyo prompt se compiló contra el guion anterior.
Las tomas sin prompt, los medios importados y lo ya recompilado no se tocan.
"""
from __future__ import annotations

GUION_V1 = "Cortexa Labs presenta Radar con un 12 por ciento más de acierto."
GUION_V2 = "Cortexa Labs presenta Radar con un 18 por ciento más de acierto."


def _proyecto(demo_client) -> dict:
    project = demo_client.post("/api/v1/projects", json={"name": "Invalidación exclusiva"}).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": GUION_V1}, "expected_revision": 0},
    )
    return project


def _prompt(demo_client, pid: int, take_id: int | None, text: str):
    return demo_client.post(
        f"/api/v1/projects/{pid}/prompts",
        json={"take_id": take_id, "prompt_en": text},
    )


def test_only_prompts_compiled_from_old_script_need_review(demo_client):
    project = _proyecto(demo_client)
    pid = project["id"]

    # Toma A: prompt compilado contra GUION_V1
    take_a = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()
    _prompt(demo_client, pid, take_a["id"], "Apertura con maxDotAi sobre el 12 por ciento.")

    # Toma B: sin prompt todavía
    take_b = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 2}).json()

    # Cambio de la cifra (cambio factual): 12 → 18
    r = demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": GUION_V2}, "expected_revision": 1},
    ).json()
    assert r["takes_needing_review"] == [take_a["id"]]  # exclusivamente la dependiente
    assert r["invalidated_graphics"] == []  # no había gráficos derivados

    state = demo_client.get(f"/api/v1/projects/{pid}").json()
    by_id = {t["id"]: t for t in state["takes"]}
    assert by_id[take_a["id"]]["needs_review"] is True
    assert by_id[take_b["id"]]["needs_review"] is False  # sin prompt: nada que revisar
    # El estado de la toma no se degrada: se pide revisión, no se borra el trabajo
    assert by_id[take_a["id"]]["status"] == "PROMPT_LISTO"

    # Recompilar la toma A contra el guion vigente despeja la revisión
    _prompt(demo_client, pid, take_a["id"], "Apertura corregida con el 18 por ciento.")
    state = demo_client.get(f"/api/v1/projects/{pid}").json()
    by_id = {t["id"]: t for t in state["takes"]}
    assert by_id[take_a["id"]]["needs_review"] is False


def test_recompiled_prompt_is_not_flagged_again(demo_client):
    project = _proyecto(demo_client)
    pid = project["id"]
    take = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()

    # Prompt compilado DESPUÉS de un primer cambio: queda alineado con GUION_V2
    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": GUION_V2}, "expected_revision": 1},
    )
    _prompt(demo_client, pid, take["id"], "Prompt contra el guion vigente (18%).")

    # Guardar DE NUEVO el mismo guion no invalida nada (mismo hash)
    r = demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": GUION_V2}, "expected_revision": 2},
    ).json()
    assert r["takes_needing_review"] == []
    assert r["invalidated_graphics"] == []


def test_imported_media_survives_script_invalidation(demo_client):
    project = _proyecto(demo_client)
    pid = project["id"]
    take = demo_client.post(f"/api/v1/projects/{pid}/takes", json={"take_number": 1}).json()
    _prompt(demo_client, pid, take["id"], "Prompt inicial.")
    demo_client.post(
        f"/api/v1/projects/{pid}/takes/{take['id']}/media",
        files={"file": ("toma.mp4", b"mp4-importado-estable", "video/mp4")},
    )
    before = demo_client.get(f"/api/v1/projects/{pid}").json()

    demo_client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": "Guion completamente nuevo de prueba."}, "expected_revision": 1},
    ).json()

    after = demo_client.get(f"/api/v1/projects/{pid}").json()
    assert after["takes"][0]["imported_media"] == before["takes"][0]["imported_media"]
    assert after["takes"][0]["needs_review"] is True  # pide revisión, no destruye el MP4
