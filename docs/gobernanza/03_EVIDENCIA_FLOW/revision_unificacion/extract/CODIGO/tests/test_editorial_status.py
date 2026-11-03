"""Integración del estado editorial (Fases 1-2 del plan de corrección).

Verifica que lista, detalle, lote y traspaso cuentan la misma historia:
- `ready_count` conserva su significado histórico (guiones aprobados).
- La procedencia DEMO viene de fuentes y evidencias, nunca del titular.
- La elegibilidad de traspaso usa los mismos motivos que expone la API.
- Las afirmaciones sin evidencia no bloquean pero se advertían.
"""
from __future__ import annotations

from neuralnews.db import session_scope
from neuralnews.models import Claim, Evidence, ScriptVersion, Source, Story, StorySource


def _create_story(db, *, demo: bool, title: str, summary: str | None = "Resumen real."):
    story = Story(topic_key=title[:40], title=title, summary=summary, demo=demo)
    db.add(story)
    db.flush()
    source = Source(
        provider="web_rss",
        canonical_url="https://ejemplo.test/a",
        title="Fuente de ejemplo",
        demo=demo,
        status="READY",
    )
    db.add(source)
    db.flush()
    db.add(StorySource(story_id=story.id, source_id=source.id, relevance="primary"))
    db.flush()
    return story


def _add_claim(db, story, *, status: str, demo: bool = False):
    claim = Claim(story_id=story.id, statement=f"Afirmación {status}", verification_status=status)
    db.add(claim)
    db.flush()
    if status == "SUPPORTED":
        db.add(
            Evidence(
                claim_id=claim.id,
                url="https://ejemplo.test/evidencia",
                publisher="Fuente",
                kind="PRIMARY",
                confidence="high",
                demo=demo,
            )
        )
        db.flush()
    return claim


def _add_version(db, story, *, approved: bool):
    version = ScriptVersion(
        story_id=story.id,
        version=1,
        content="Guion de prueba.",
        language="es-ES",
        content_hash="a" * 64,
    )
    db.add(version)
    db.flush()
    if approved:
        from neuralnews.models import Approval

        db.add(
            Approval(
                story_id=story.id,
                script_version_id=version.id,
                actor_id="editor",
                status="ACTIVE",
            )
        )
        db.flush()
        story.status = "APPROVED"
    return version


def test_procedencia_demo_viene_de_las_fuentes_y_no_del_titular(app_env):
    from neuralnews.services.editorial_status import build_story_status

    with session_scope() as db:
        # Título sin la palabra "demo", pero fuente ficticia → la procedencia es DEMO.
        story = _create_story(db, demo=True, title="Titular sin la palabra demo")
        _add_claim(db, story, status="SUPPORTED", demo=True)
        status = build_story_status(db, story, versions=[], claims=[])
        assert status.origin == "demo"

        # Título con la palabra "demo" pero fuente real → la procedencia es real.
        story2 = _create_story(db, demo=False, title="Noticia demo con fuente real")
        status2 = build_story_status(db, story2, versions=[], claims=[])
        assert status2.origin == "real"

        # Sin fuentes: origen no determinado (nunca se afirma que sea real).
        story3 = Story(topic_key="k3", title="Sin fuentes", summary="x")
        db.add(story3)
        db.flush()
        status3 = build_story_status(db, story3, versions=[], claims=[])
        assert status3.origin == "unknown"


def test_afirmaciones_sin_evidencia_advierten_pero_no_bloquean(app_env):
    from neuralnews.services.editorial_status import build_story_status

    with session_scope() as db:
        story = _create_story(db, demo=False, title="Con afirmación sin evidencia")
        _add_claim(db, story, status="UNVERIFIED")
        _add_version(db, story, approved=True)
        from neuralnews.models import Approval

        approval = db.query(Approval).filter_by(story_id=story.id).one()
        status = build_story_status(
            db,
            story,
            versions=db.query(ScriptVersion).filter_by(story_id=story.id).all(),
            claims=db.query(Claim).filter_by(story_id=story.id).all(),
            approved_version_id=approval.script_version_id,
            pending_flag=False,
        )
        assert status.production_ready is True
        assert status.production_warnings, "debe avisar de la verificación incompleta"
        assert not any("sin evidencia" in b for b in status.production_blockers)


def test_afirmaciones_contradichas_bloquean_la_produccion(app_env):
    from neuralnews.services.editorial_status import build_story_status

    with session_scope() as db:
        story = _create_story(db, demo=False, title="Con contradicción")
        _add_claim(db, story, status="CONTRADICTED")
        _add_version(db, story, approved=True)
        from neuralnews.models import Approval

        approval = db.query(Approval).filter_by(story_id=story.id).one()
        status = build_story_status(
            db,
            story,
            versions=db.query(ScriptVersion).filter_by(story_id=story.id).all(),
            claims=db.query(Claim).filter_by(story_id=story.id).all(),
            approved_version_id=approval.script_version_id,
            pending_flag=False,
        )
        assert status.production_ready is False
        assert any("contradicha" in b for b in status.production_blockers)


def test_sin_resumen_no_es_apto_para_produccion(app_env):
    from neuralnews.services.editorial_status import build_story_status

    with session_scope() as db:
        story = _create_story(db, demo=False, title="Sin resumen", summary=None)
        _add_claim(db, story, status="SUPPORTED")
        _add_version(db, story, approved=True)
        from neuralnews.models import Approval

        approval = db.query(Approval).filter_by(story_id=story.id).one()
        status = build_story_status(
            db,
            story,
            versions=db.query(ScriptVersion).filter_by(story_id=story.id).all(),
            claims=db.query(Claim).filter_by(story_id=story.id).all(),
            approved_version_id=approval.script_version_id,
            pending_flag=False,
        )
        assert status.production_ready is False
        assert any("resumen" in b for b in status.production_blockers)


def test_los_recuentos_de_lote_conservan_su_significado(demo_client, worker):
    """Criterio de aceptación de Fase 1: 10 con 8 aprobadas → 8/2; 5 aprobadas → 5/0."""
    from neuralnews.services.batches import create_batch
    from neuralnews.models import Story as S

    ids = []
    for i in range(10):
        text = (
            f"Noticia de recuento número {i}: la empresa ficticia Acme Instruments ha presentado "
            f"el dispositivo R{i} con mejoras documentadas en su web de demostración."
        )
        payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
        worker()
        detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
        story_id = detail["stories"][0]["id"]
        demo_client.post(f"/api/v1/stories/{story_id}/research")
        demo_client.post(f"/api/v1/stories/{story_id}/draft")
        worker()
        det = demo_client.get(f"/api/v1/stories/{story_id}").json()
        demo_client.post(
            f"/api/v1/stories/{story_id}/approve",
            json={"script_version_id": det["script_versions"][-1]["id"]},
        )
        ids.append(story_id)

    with session_scope() as db:
        batch = create_batch(db, name="Recuento", target_size=10, story_ids=ids)
        batch_id = batch.id

    overview = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert overview["ready_count"] == 10, "los 10 tienen aprobación vigente"
    assert overview["pending_count"] == 0
    # La métrica nueva informa de cuántos están además listos para producción.
    assert 0 <= overview["production_ready_count"] <= overview["ready_count"]
    assert overview["production_ready_count"] + overview["blocked_count"] == 10

    # Bloquear la aprobación de dos noticias → 8 aprobadas / 2 pendientes.
    with session_scope() as db:
        from neuralnews.models import Approval

        for sid in ids[:2]:
            db.query(Approval).filter_by(story_id=sid).update({"status": "INVALIDATED"})
    overview2 = demo_client.get(f"/api/v1/batches/{batch_id}").json()
    assert overview2["ready_count"] == 8
    assert overview2["pending_count"] == 2


def test_api_lista_y_detalle_coinciden_en_procedencia_y_aprobacion(demo_client, worker):
    """Criterio de aceptación de Fase 2: misma etiqueta DEMO y mismo estado en lista y detalle."""
    text = (
        "Cortexa Labs ha anunciado Radar, un modelo multimodal de texto e imagen con un 12% más de "
        "acierto en razonamiento visual según benchmarks internos."
    )
    payload = demo_client.post("/api/v1/sources", json={"text": text}).json()
    worker()
    detail = demo_client.get(f"/api/v1/sources/{payload['source']['id']}").json()
    story_id = detail["stories"][0]["id"]
    demo_client.post(f"/api/v1/stories/{story_id}/research")
    demo_client.post(f"/api/v1/stories/{story_id}/draft")
    worker()
    det = demo_client.get(f"/api/v1/stories/{story_id}").json()
    demo_client.post(
        f"/api/v1/stories/{story_id}/approve",
        json={"script_version_id": det["script_versions"][-1]["id"]},
    )

    listado = demo_client.get("/api/v1/stories").json()
    fila = next((s for s in listado["items"] if s["id"] == story_id), None)
    assert fila is not None
    detalle = demo_client.get(f"/api/v1/stories/{story_id}").json()
    assert fila["origin"] == detalle["origin"]
    assert fila["approval"] == detalle["approval"]
    assert fila["verification"] == detalle["verification"]
    assert fila["production_ready"] == detalle["production_ready"]
    assert fila["claim_total"] == detalle["claim_total"]


def test_filtros_de_servidor_con_recuentos_coherentes(demo_client, worker):
    """Criterio de aceptación de Fase 3: los recuentos coinciden con los resultados."""
    listado = demo_client.get("/api/v1/stories").json()
    assert "counts" in listado and "total" in listado and "limit" in listado
    attention = demo_client.get("/api/v1/stories?attention=true").json()
    assert attention["total"] == len(attention["items"])
    assert attention["total"] <= listado["counts"]["all"]
    # Las descartadas no cuentan como «requieren atención».
    for item in attention["items"]:
        assert item["stage"] != "rejected"
    # Búsqueda en servidor
    busqueda = demo_client.get("/api/v1/stories?q=Acme").json()
    assert all("acme" in (s["title"] + (s["summary"] or "")).lower() for s in busqueda["items"])
    # Paginación
    pagina = demo_client.get("/api/v1/stories?limit=1&offset=0").json()
    assert len(pagina["items"]) <= 1
    assert pagina["limit"] == 1 and pagina["offset"] == 0
