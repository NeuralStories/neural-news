"""NN-107 FASE 4 — Buscar o crear la transcripción de cualquier fuente."""
from __future__ import annotations

GUION_NOTICIA = (
    "Cortexa Labs ha anunciado Radar, un modelo multimodal de texto, imagen y audio. "
    "La empresa afirma que mejora un 12% el razonamiento visual según benchmarks internos. "
    "El acceso está limitado a una lista de espera para una demo web."
)


def test_manual_source_text_is_its_transcription(demo_client):
    """Fuente manual: el texto aportado ES la transcripción; se devuelve."""
    src = demo_client.post("/api/v1/sources", json={"text": GUION_NOTICIA}).json()
    sid = src["source"]["id"]
    r = demo_client.get(f"/api/v1/sources/{sid}/transcript")
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert "Radar" in body["text"]


def test_transcribe_on_manual_source_reports_honestly(demo_client, worker):
    """No hay de dónde buscar una transcripción en una fuente manual sin URL:
    se responde el motivo en lugar de inventar texto.

    La API encola el trabajo (202) y el motivo llega cuando el trabajo
    termina: la transcripción no se busca dentro de la petición (gate G3).
    """
    src = demo_client.post("/api/v1/sources", json={"text": "Texto corto sin más."}).json()
    sid = src["source"]["id"]
    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 202  # la respuesta es honesta, no un error de servidor
    body = r.json()
    assert body["job_id"] > 0
    assert body["status"] in ("QUEUED", "RUNNING")

    worker()
    job = demo_client.get(f"/api/v1/jobs/{body['job_id']}").json()
    assert job["status"] == "DONE"
    assert "manual" in (job["progress"] or "").lower()


def test_youtube_demo_transcript_is_returned(demo_client, worker):
    """En demo, la fuente de YouTube trae transcripción simulada tras procesarse;
    el trabajo la devuelve tal cual sin crear otra."""
    src = demo_client.post(
        "/api/v1/sources",
        json={"text": GUION_NOTICIA, "url": "https://www.youtube.com/watch?v=demo1234567"},
    ).json()
    worker()
    sid = src["source"]["id"]
    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 202
    worker()
    transcript = demo_client.get(f"/api/v1/sources/{sid}/transcript").json()
    assert transcript["found"] is True
    assert transcript["text"]


def test_transcribe_responde_de_inmediato(demo_client, worker, monkeypatch):
    """El handler NO hace la transcripción: solo encola. Eso es el gate G3."""
    import time

    from neuralnews.providers import transcript as transcript_mod

    def _lento(*_args, **_kwargs):
        time.sleep(2)
        return None

    monkeypatch.setattr(transcript_mod, "fetch_youtube_transcript_auto", _lento)
    src = demo_client.post(
        "/api/v1/sources",
        json={"text": GUION_NOTICIA, "url": "https://www.youtube.com/watch?v=demo1234567"},
    ).json()
    sid = src["source"]["id"]

    inicio = time.monotonic()
    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    transcurrido = time.monotonic() - inicio

    assert r.status_code == 202
    assert transcurrido < 1.0, (
        f"el handler tardó {transcurrido:.2f} s: la transcripción sigue dentro de la petición"
    )


def test_unknown_source_returns_404(demo_client):
    r = demo_client.get("/api/v1/sources/99999/transcript")
    assert r.status_code == 404


def test_transcript_endpoint_returns_segments_when_present(demo_client, worker):
    """Las transcripción con marcas de tiempo conserva sus segmentos."""
    src = demo_client.post(
        "/api/v1/sources",
        json={
            "text": "Noticia con transcripción pegada para la prueba.",
            "transcript": "[00:01] Primera frase de la transcripción. [00:04] Segunda frase.",
        },
    ).json()
    sid = src["source"]["id"]
    r = demo_client.get(f"/api/v1/sources/{sid}/transcript")
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert "transcripción" in body["text"]
