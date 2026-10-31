"""NN-107 F4 — Dossier editorial, gráficos programáticos e invalidación dirigida."""
from __future__ import annotations

import pytest

GUION = (
    "Cortexa Labs presenta Radar con un 12 por ciento más de acierto. "
    "La compañía atribuye el salto a su motor de atención. "
    "Radar llegará a producción el próximo trimestre."
)


@pytest.fixture()
def proyecto_con_historia(demo_client, worker):
    src = demo_client.post(
        "/api/v1/sources",
        json={"text": f"Prueba automatizada {__import__('time').time()}. {GUION}"},
    ).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{src['source']['id']}").json()
    story_id = detail["stories"][0]["id"]
    project = demo_client.post(
        "/api/v1/projects", json={"name": "F4", "ratio": "9:16", "story_id": story_id}
    ).json()
    demo_client.put(
        f"/api/v1/projects/{project['id']}/studio/guion",
        json={"payload": {"scriptText": GUION}, "expected_revision": 0},
    )
    return demo_client, project["id"], story_id


def test_dossier_shares_the_editorial_newsroom(proyecto_con_historia):
    """D7: el Studio lee fuentes y afirmaciones del dominio editorial, con los
    mismos estados; importar o vincular nunca verifica (F-08)."""
    client, pid, story_id = proyecto_con_historia
    dossier = client.get(f"/api/v1/projects/{pid}/dossier").json()
    assert dossier["linked"] is True
    assert dossier["story"]["id"] == story_id
    assert isinstance(dossier["sources"], list)
    assert isinstance(dossier["claims"], list)
    for claim in dossier["claims"]:
        assert claim["verification_status"] in {
            "UNVERIFIED", "SUPPORTED", "CONTRADICTED", "CONFIRMED", "DESACTUALIZADA",
        }


def test_project_without_story_has_no_dossier(demo_client):
    project = demo_client.post("/api/v1/projects", json={"name": "sin historia"}).json()
    dossier = demo_client.get(f"/api/v1/projects/{project['id']}/dossier").json()
    assert dossier["linked"] is False


def test_graphic_svg_renders_exact_values_with_source(proyecto_con_historia):
    client, pid, story_id = proyecto_con_historia
    dossier = client.get(f"/api/v1/projects/{pid}/dossier").json()
    claim_id = dossier["claims"][0]["claim_id"] if dossier["claims"] else None
    created = client.post(
        f"/api/v1/projects/{pid}/graphics",
        json={
            "title": "Mejora de acierto de Radar",
            "claim_id": claim_id,
            "series": [{"label": "Radar", "value": 12, "unit": "%"}],
        },
    )
    assert created.status_code == 200, created.text

    svg = client.get(f"/api/v1/projects/{pid}/graphics/{created.json()['id']}/svg")
    assert svg.status_code == 200
    body = svg.text
    assert "<svg" in body and 'viewBox="0 0 480 320"' in body
    assert "12 %" in body or "12%" in body  # valor exacto, no inventado
    assert "Claim #" in body  # pie de fuente trazable


def test_graphic_rejects_empty_series_and_foreign_claim(proyecto_con_historia):
    client, pid, story_id = proyecto_con_historia
    empty = client.post(
        f"/api/v1/projects/{pid}/graphics", json={"title": "x", "series": []}
    )
    assert empty.status_code == 422

    # Claim de otra historia no se puede vincular (trazabilidad)
    other = client.post(
        "/api/v1/sources", json={"text": "Fuente ajena sin relación para la prueba de traza."}
    ).json()
    worker = None
    foreign_story = None
    detail = client.get(f"/api/v1/sources/{other['source']['id']}").json()
    if detail.get("stories"):
        foreign_story = detail["stories"][0]["id"]
        foreign_claim = client.get(f"/api/v1/stories/{foreign_story}").json()
        claims = foreign_claim.get("claims") or []
        if claims:
            bad = client.post(
                f"/api/v1/projects/{pid}/graphics",
                json={"title": "x", "claim_id": claims[0]["id"], "series": [{"label": "a", "value": 1}]},
            )
            assert bad.status_code == 422


def test_script_change_invalidates_derived_graphics(proyecto_con_historia):
    """Invalidación dirigida (cap. 13): cambio factual → gráficos derivados
    quedan INVALIDADO para revisión; el fondo y los clips neutros no se tocan."""
    client, pid, story_id = proyecto_con_historia
    graphic = client.post(
        f"/api/v1/projects/{pid}/graphics",
        json={"title": "Cifra del guion", "series": [{"label": "Radar", "value": 12, "unit": "%"}]},
    ).json()

    # Guardar el MISMO guion no invalida nada
    same = client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": GUION}, "expected_revision": 1},
    )
    assert same.status_code == 200
    assert same.json()["invalidated_graphics"] == []

    # Cambiar el guion invalida el gráfico derivado
    changed = client.put(
        f"/api/v1/projects/{pid}/studio/guion",
        json={"payload": {"scriptText": GUION + " Dato adicional de cierre."}, "expected_revision": 2},
    )
    assert changed.status_code == 200
    assert graphic["id"] in changed.json()["invalidated_graphics"]

    listing = client.get(f"/api/v1/projects/{pid}/graphics").json()
    status = {g["id"]: g["status"] for g in listing["items"]}
    assert status[graphic["id"]] == "INVALIDADO"

    # El SVG de un gráfico invalidado no se sirve (exige revisión)
    blocked = client.get(f"/api/v1/projects/{pid}/graphics/{graphic['id']}/svg")
    assert blocked.status_code == 409
