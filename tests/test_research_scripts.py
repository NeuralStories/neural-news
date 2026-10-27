"""Etapa 3 — investigación, evidencia, puntuación, guiones y aprobación."""
from __future__ import annotations

from neuralnews.providers.llm import EditorialLLMError
from neuralnews.providers.video_analysis import extract_json_block
from neuralnews.worker_tasks import PROCESS_SOURCE

CORTEXA_VIDEO = (
    "Cortexa Labs ha anunciado Radar, su modelo multimodal. Según la ficha técnica mejora un 12% "
    "el razonamiento visual. Hay lista de espera para una demo web."
)
CORTEXA_ARTICLE = (
    "Cortexa Labs detalla Radar, su sistema multimodal. La ficha técnica indica un 12% más de acierto "
    "en razonamiento visual y el acceso queda limitado a lista de espera para demo web."
)
VIREO_TEXT = "Vireo AI levanta 40 millones de dólares liderados por Meridian Capital."
OLD_TEXT = (
    "Resumen de finales de 2024: LinguaNova anunciaba su primera versión de traducción en tiempo "
    "real para reuniones."
)


def _create_and_process(demo_client, worker, text: str) -> int:
    payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
    source_id = payload["source"]["id"]
    worker()
    return source_id


def test_two_sources_merge_into_one_story(demo_client, worker):
    _create_and_process(demo_client, worker, CORTEXA_VIDEO)
    _create_and_process(demo_client, worker, CORTEXA_ARTICLE)

    stories = demo_client.get("/api/v1/stories").json()["items"]
    radar = [s for s in stories if "radar" in s["topic_key"]][0]
    detail = demo_client.get(f"/api/v1/stories/{radar['id']}").json()
    assert len(detail["sources"]) == 2, "las dos fuentes deben quedar referenciadas"
    assert {src["provider"] for src in detail["sources"]} == {"manual"}


def test_old_source_not_marked_as_breaking(demo_client, worker):
    _create_and_process(demo_client, worker, OLD_TEXT)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    lingua = [s for s in stories if "linguanova" in s["topic_key"]][0]
    assert "2024" in lingua["summary"]
    detail = demo_client.get(f"/api/v1/stories/{lingua['id']}").json()
    assert detail["original_event_date"] is None, "no debe inventarse fecha del acontecimiento"


def test_research_attaches_only_real_or_marked_evidence(demo_client, worker):
    _create_and_process(demo_client, worker, CORTEXA_VIDEO + " " + VIREO_TEXT)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    radar = [s for s in stories if "radar" in s["topic_key"]][0]
    vireo = [s for s in stories if "vireo" in s["topic_key"]][0]

    demo_client.post(f"/api/v1/stories/{radar['id']}/research")
    demo_client.post(f"/api/v1/stories/{vireo['id']}/research")
    worker()

    radar_detail = demo_client.get(f"/api/v1/stories/{radar['id']}").json()
    assert radar_detail["status"] == "REVIEW_REQUIRED"
    supported = [c for c in radar_detail["claims"] if c["verification_status"] == "SUPPORTED"]
    assert supported, "la afirmación del 12% debe quedar soportada por la evidencia demo"
    for claim in radar_detail["claims"]:
        for ev in claim["evidence"]:
            assert ev["demo"] is True, "la evidencia demo debe ir marcada"
            assert ev["url"].startswith("https://demo.neuralnews.invalid/")

    vireo_detail = demo_client.get(f"/api/v1/stories/{vireo['id']}").json()
    unverified = [c for c in vireo_detail["claims"] if c["verification_status"] == "UNVERIFIED"]
    assert unverified, "sin evidencia, la afirmación queda sin verificar"
    for claim in unverified:
        assert claim["evidence"] == [], "no se inventan citas"


def test_scoring_breakdown_sums_and_records_criteria(demo_client, worker):
    source_id = _create_and_process(demo_client, worker, CORTEXA_VIDEO)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    radar = [s for s in stories if "radar" in s["topic_key"]][0]
    result = demo_client.post(f"/api/v1/stories/{radar['id']}/rescore").json()
    breakdown = result["breakdown"]
    total = sum(v for k, v in breakdown.items() if isinstance(v, (int, float)))
    assert total <= 100.0
    assert set(breakdown["criterios"]["pesos"]) == {"impacto", "verificacion", "novedad", "visual"}


def test_script_lifecycle_and_approval_invalidation(demo_client, worker):
    _create_and_process(demo_client, worker, CORTEXA_VIDEO)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    radar = [s for s in stories if "radar" in s["topic_key"]][0]
    story_id = radar["id"]

    demo_client.post(f"/api/v1/stories/{story_id}/research")
    worker()
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()

    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detail["status"] == "SCRIPT_DRAFT"
    versions = detail["script_versions"]
    assert len(versions) == 1 and versions[0]["author_type"] == "AI"

    # Edición del usuario → versión 2
    edited = versions[0]["content"] + "\n\nAñado un matiz propio y un cierre distinto."
    patch = demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": edited, "expected_version": 1},
    )
    assert patch.status_code == 200, patch.text
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detail["script_versions"][-1]["author_type"] == "HUMAN"

    # Aprobación de la versión 2
    approve = demo_client.post(
        f"/api/v1/stories/{story_id}/approve",
        json={"script_version_id": detail["script_versions"][-1]["id"]},
    )
    assert approve.status_code == 200, approve.text
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detail["status"] == "APPROVED"
    assert detail["active_approval"]["script_version_id"] == detail["script_versions"][-1]["id"]

    # Editar después del borrador aprobado anula la aprobación
    edited2 = edited + "\n\nCambio posterior a la aprobación."
    patch2 = demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": edited2, "expected_version": 2},
    )
    assert patch2.status_code == 200
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert detail["status"] == "SCRIPT_DRAFT", "editar obliga a volver a aprobar"
    assert detail["pending_approval_flag"] is True

    # Aprobar la versión antigua se rechaza
    old_version = detail["script_versions"][1]
    reject_old = demo_client.post(
        f"/api/v1/stories/{story_id}/approve", json={"script_version_id": old_version["id"]}
    )
    assert reject_old.status_code == 400
    assert "versión más reciente" in reject_old.json()["detail"]


def test_edit_conflict_keeps_both_versions(demo_client, worker):
    _create_and_process(demo_client, worker, CORTEXA_VIDEO)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    radar = [s for s in stories if "radar" in s["topic_key"]][0]
    story_id = radar["id"]
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    base = detail["script_versions"][0]["content"]

    # Primera edición entra; la segunda con expected_version desfasada choca.
    first = demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": base + "\n\nEdición A.", "expected_version": 1},
    )
    assert first.status_code == 200
    conflict = demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": base + "\n\nEdición B concurrente.", "expected_version": 1},
    )
    assert conflict.status_code == 409
    body = conflict.json()["detail"]
    assert body["current_version"] == 2

    # El texto de B no se pierde: se puede guardar como versión nueva.
    retry = demo_client.patch(
        f"/api/v1/stories/{story_id}/script",
        json={"content": base + "\n\nEdición B concurrente.", "expected_version": 2},
    )
    assert retry.status_code == 200
    detail = demo_client.get(f"/api/v1/stories/{story_id}").json()
    texts = [v["content"] for v in detail["script_versions"]]
    assert any("Edición A." in t for t in texts) and any("Edición B concurrente." in t for t in texts)


def test_identical_text_does_not_create_version(demo_client, worker):
    _create_and_process(demo_client, worker, CORTEXA_VIDEO)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    radar = [s for s in stories if "radar" in s["topic_key"]][0]
    demo_client.post(f"/api/v1/stories/{radar['id']}/draft")
    worker()
    detail = demo_client.get(f"/api/v1/stories/{radar['id']}").json()
    content = detail["script_versions"][0]["content"]
    response = demo_client.patch(
        f"/api/v1/stories/{radar['id']}/script",
        json={"content": content, "expected_version": 1},
    )
    assert response.status_code == 400
    assert "idéntico" in response.json()["detail"]


def test_reject_story(demo_client, worker):
    _create_and_process(demo_client, worker, VIREO_TEXT)
    stories = demo_client.get("/api/v1/stories").json()["items"]
    vireo = [s for s in stories if "vireo" in s["topic_key"]][0]
    response = demo_client.post(
        f"/api/v1/stories/{vireo['id']}/reject", json={"reason": "Ya lo cubrimos la semana pasada"}
    )
    assert response.status_code == 200
    assert demo_client.get(f"/api/v1/stories/{vireo['id']}").json()["status"] == "REJECTED"


# ------------------------------------------------------------------ LLM JSON defectuoso
def test_extract_json_block_repairs_fenced_json():
    raw = "```json\n{\"stories\": []}\n```"
    assert extract_json_block(raw) == '{"stories": []}'
    assert extract_json_block(' preamble {"a": 1} trailing ') == '{"a": 1}'


def test_malformed_llm_json_fails_without_saving(demo_client, worker, monkeypatch, app_env):
    from neuralnews.providers import llm as llm_mod

    def broken_call(self, system_prompt, user_content):
        return "esto no es json ni con vallas"

    monkeypatch.setattr(llm_mod.EditorialLLMProvider, "_call_llm", broken_call)
    settings = app_env["settings"]
    settings.demo_mode = False  # fuerza la ruta real del proveedor (aquí parcheada)

    payload = demo_client.post("/api/v1/sources", json={"text": CORTEXA_VIDEO}).json()
    source_id = payload["source"]["id"]
    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    job_id = next(j["id"] for j in jobs if j["type"] == PROCESS_SOURCE and j["status"] == "QUEUED")
    worker()
    job = demo_client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] in ("FAILED", "RETRYABLE_FAILED")
    assert "no ha devuelto" in (job["error"] or "") or "utilizable" in (job["error"] or "")
    # No se guardan candidatos engañosos para esa fuente.
    detail = demo_client.get(f"/api/v1/sources/{source_id}").json()
    assert detail["stories"] == []
