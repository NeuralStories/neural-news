"""NN-107 — Transcripción automática de CUALQUIER vídeo de YouTube.

La búsqueda por pistas manuales (timedtext) falla para la mayoría de vídeos;
la automática usa la API interna del reproductor para localizar las pistas
(incluidas las ASR) y convertirlas. El parser de json3 es puro y se prueba con
una respuesta canónica sin red; el endpoint se prueba con la búsqueda
simulada (monkeypatch) para verificar el almacenamiento.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api" / "src"))

import pytest  # noqa: E402
from neuralnews.providers.transcript import parse_json3_events  # noqa: E402  # noqa: E402

JSON3 = {
    "events": [
        {"tStartMs": 1000, "dDurationMs": 2500,
         "segs": [{"utf8": "Bienvenidos "}, {"utf8": "a NeuralStories "}, {"utf8": "News."}]},
        {"tStartMs": 3500, "dDurationMs": 2000,
         "segs": [{"utf8": "La cifra "}, {"utf8": "clave del trimestre."}]},
        {"segs": [{"utf8": "\n"}]},  # evento sin texto: se ignora
    ]
}


def test_parse_json3_builds_segments_with_timing():
    segments = parse_json3_events(JSON3)
    assert len(segments) == 2
    assert segments[0].start_ms == 1000 and segments[0].end_ms == 3500
    assert segments[0].text == "Bienvenidos a NeuralStories News."
    assert segments[1].text == "La cifra clave del trimestre."


def test_parse_json3_handles_empty_payload():
    assert parse_json3_events({}) == []


def test_transcribe_stores_auto_transcript_for_any_youtube_video(demo_client, worker, monkeypatch):
    """Cualquier vídeo (con ASR): el endpoint busca automáticamente, almacena la
    transcripción literal y la devuelve (found=True, created=True)."""
    import neuralnews.api.sources as sources_mod
    from neuralnews.providers.base import ContentDraft, SegmentDraft

    fake_draft = ContentDraft(
        content_type="TRANSCRIPT",
        text="Transcripción automática del vídeo completo.",
        is_verbatim=True,
        provider="youtube_asr",
        confidence="medium",
        segments=[SegmentDraft(text="Transcripción automática.", start_ms=0, end_ms=900, sequence=0)],
    )

    demo_client.post(
        "/api/v1/sources",
        json={"url": "https://www.youtube.com/watch?v=auto1234567", "text": "Contexto de la fuente."},
    ).json()
    worker()
    sid_src = demo_client.get("/api/v1/sources").json()["items"][0]["id"]

    captured = {}
    def fake_auto(video_id):
        captured["video_id"] = video_id
        return fake_draft

    monkeypatch.setattr(sources_mod, "_auto_transcript", fake_auto)
    r = demo_client.post(f"/api/v1/sources/{sid_src}/transcribe")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["found"] is True and body["created"] is True, body
    assert body["transcript"]["provider"] == "youtube_asr"
    assert captured["video_id"] == "auto1234567"

    # Persistida: GET transcript la devuelve
    got = demo_client.get(f"/api/v1/sources/{sid_src}/transcript").json()
    assert got["found"] is True and "automática" in got["text"]
