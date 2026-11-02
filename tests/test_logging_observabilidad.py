"""NN-110.e — Registro estructurado y motivo normalizado del fallo.

Dos cosas que antes solo se podían leer «a ojo»:

  1. El log del worker era texto libre: un fallo no se podía consultar sin
     parsear mensajes. Ahora cada evento es una línea JSON.
  2. El motivo de un fallo no existía: solo había un texto. Ahora el trabajo
     registra **por qué** falló (presupuesto, material, conector…) en el momento
     del fallo, no deducido después.
"""
from __future__ import annotations

import json
import logging

from neuralnews.db import get_session_factory
from neuralnews.models import Job
from neuralnews.queue import enqueue


def test_el_registro_es_una_linea_json_por_evento():
    """Cada evento se serializa como JSON con sus campos."""
    import io

    from neuralnews.logging_setup import JsonFormatter, log_event

    flujo = io.StringIO()
    manejador = logging.StreamHandler(flujo)
    manejador.setFormatter(JsonFormatter())
    registro = logging.getLogger("prueba-json")
    registro.handlers = [manejador]
    registro.setLevel(logging.INFO)
    registro.propagate = False

    log_event(registro, "job.done", "job #7 terminó como DONE", job_id=7, status="DONE")

    lineas = [l for l in flujo.getvalue().splitlines() if l.strip()]
    assert len(lineas) == 1
    datos = json.loads(lineas[0])
    assert datos["event"] == "job.done"
    assert datos["job_id"] == 7
    assert datos["status"] == "DONE"
    assert datos["level"] == "INFO"
    assert datos["ts"]


def test_configure_logging_no_duplica_handlers():
    """Instalar el registro dos veces no duplica la salida."""
    import io

    from neuralnews.logging_setup import configure_logging

    flujo = io.StringIO()
    configure_logging(flujo)
    raiz = logging.getLogger()
    despues_primera = len(raiz.handlers)
    json_primera = sum(
        1 for h in raiz.handlers if getattr(h, "_neural_json", False)
    )

    configure_logging(flujo)
    configure_logging(flujo)

    assert len(raiz.handlers) == despues_primera, "no debe añadir handlers"
    assert (
        sum(1 for h in raiz.handlers if getattr(h, "_neural_json", False))
        == json_primera
        == 1
    )


def _encolar(tipo: str = "process_source", dedupe: str = "k", payload: dict | None = None) -> int:
    with get_session_factory()() as db:
        job, _ = enqueue(db, tipo, payload or {"source_id": 1}, dedupe_key=dedupe)
        job_id = job.id
        db.commit()
    return job_id


def test_el_motivo_del_fallo_queda_registrado(demo_client, worker, monkeypatch):
    """Un trabajo que falla por falta de material registra ese motivo."""
    from neuralnews.services import montage as montage_mod

    def _sin_material(*_args, **_kwargs):
        return {"ok": False, "error": "No hay ningún segmento renderizable", "missing": []}

    monkeypatch.setattr(montage_mod, "build_animatica", _sin_material)
    proyecto = demo_client.post(
        "/api/v1/projects", json={"name": "Sin material", "ratio": "9:16"}
    ).json()
    job_id = _encolar(
        "build_montage", "montaje-sin-material", {"project_id": proyecto["id"]}
    )
    worker()

    with get_session_factory()() as db:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status == "FAILED", job.error
        assert job.error_kind == "material"
        assert "renderizable" in (job.error or "")


def test_un_fallo_de_conector_registra_su_motivo(demo_client, worker, monkeypatch):
    """Un proveedor que falla se registra como «conector» y se reintenta."""
    from neuralnews.providers import transcript as transcript_mod

    def _fallo(*_args, **_kwargs):
        raise RuntimeError("la red no responde")

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _fallo)
    src = demo_client.post(
        "/api/v1/sources", json={"url": "https://youtu.be/aaaaaaaaaaa"}
    ).json()["source"]["id"]
    job_id = _encolar("transcribe_source", f"conector-{src}")
    worker()

    with get_session_factory()() as db:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.error_kind == "connector"
        assert job.status in ("RETRYABLE_FAILED", "FAILED")


def test_la_api_expone_el_motivo_normalizado(demo_client, worker, monkeypatch):
    """`GET /api/v1/jobs` devuelve el motivo y su etiqueta legible."""
    from neuralnews.providers import transcript as transcript_mod

    def _fallo(*_args, **_kwargs):
        raise RuntimeError("la red no responde")

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _fallo)
    src = demo_client.post(
        "/api/v1/sources", json={"url": "https://youtu.be/bbbbbbbbbbb"}
    ).json()["source"]["id"]
    demo_client.post(f"/api/v1/sources/{src}/transcribe")
    worker()

    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    con_error = [j for j in jobs if j.get("error")]
    assert con_error, "debe haber un trabajo con error"
    for j in con_error:
        assert j["error_kind"] in ("connector", "unknown", "budget", "material")
        if j["error_kind"]:
            assert j["error_kind_label"], "un motivo debe tener etiqueta legible"


def test_un_trabajo_correcto_no_tiene_motivo_de_fallo(demo_client, worker):
    """Un trabajo que va bien no lleva motivo de fallo."""
    demo_client.post("/api/v1/sources", json={"text": "Una fuente cualquiera."})
    worker()
    jobs = demo_client.get("/api/v1/jobs").json()["items"]
    for j in jobs:
        if j["status"] == "DONE":
            assert j["error_kind"] is None
            assert j["error_kind_label"] == ""
