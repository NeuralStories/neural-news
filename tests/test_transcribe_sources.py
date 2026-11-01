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


def test_transcribe_on_manual_source_reports_honestly(demo_client):
    """No hay de dónde buscar una transcripción en una fuente manual sin URL:
    se responde el motivo en lugar de inventar texto."""
    src = demo_client.post("/api/v1/sources", json={"text": "Texto corto sin más."}).json()
    sid = src["source"]["id"]
    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 200  # la respuesta es honesta, no un error de servidor
    body = r.json()
    assert body["found"] is False and body["created"] is False
    assert "manual" in body["message"].lower()


def test_youtube_demo_transcript_is_returned(demo_client, worker):
    """En demo, la fuente de YouTube trae transcripción simulada tras procesarse;
    transcribe la devuelve tal cual sin crear otra."""
    src = demo_client.post(
        "/api/v1/sources",
        json={"text": GUION_NOTICIA, "url": "https://www.youtube.com/watch?v=demo1234567"},
    ).json()
    worker()
    sid = src["source"]["id"]
    r = demo_client.post(f"/api/v1/sources/{sid}/transcribe")
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True and body["created"] is False
    assert body["transcript"]["text"]


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
