"""NN-107 — Proveedor yt-dlp para transcripción completa de YouTube.

Se prueban las partes puras (selección de idioma, parseo VTT) y la detección
del binario; la descarga real se ha verificado en ejecución contra YouTube
(2 vídeos reales: uno con subtítulos VTT y otro con json3).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api" / "src"))

from neuralnews.providers.transcript import (  # noqa: E402
    PREFERRED_LANGS, _pick_language, _segments_from_vtt, parse_json3_events,
    yt_dlp_available_languages, yt_dlp_binary,
)

VTT = """WEBVTT
Kind: captions
Language: es-419

00:00:18.640 --> 00:00:21.880
Conocemos bien el amor

00:00:22.640 --> 00:00:26.960
Tú conoces las reglas,
igual que yo
"""


def test_language_preference_prefers_regional_variant():
    """YouTube usa variantes regionales: «es» puede no existir aunque exista
    «es-419», y pedir una variante inexistente devuelve error."""
    available = ["en", "de-DE", "ja", "pt-BR", "es-419", "ab-en", "aa-en"]
    assert _pick_language(available, PREFERRED_LANGS) == "es-419"


def test_language_preference_skips_chained_translations():
    """«es-es-419» o «en-zh-TW» son traducciones encadenadas, no la pista
    pedida: se descartan."""
    available = ["en-orig", "es-es-419", "en-zh-TW", "en"]
    chosen = _pick_language(available, PREFERRED_LANGS)
    # «en-orig» es la pista original (no una traducción encadenada): válida
    assert chosen == "en-orig"
    assert not chosen.startswith("en-zh")


def test_vtt_parser_reads_timestamps_and_text():
    segments = _segments_from_vtt(VTT)
    # El VTT parte la frase en dos líneas: se conservan como segmentos con
    # el mismo inicio (el texto se recompone luego en la transcripción).
    assert len(segments) == 3
    assert segments[0].start_ms == 18640
    assert segments[0].text == "Conocemos bien el amor"
    assert segments[1].start_ms == 22640
    assert segments[1].text == "Tú conoces las reglas,"
    assert segments[2].text == "igual que yo"


def test_json3_parser_reads_timestamps_and_text():
    segments = parse_json3_events({
        "events": [
            {"tStartMs": 0, "dDurationMs": 900,
             "segs": [{"utf8": "Hola "}, {"utf8": "mundo"}]},
            {"tStartMs": 900, "dDurationMs": 500, "segs": [{"utf8": "Segundo"}]},
        ]
    })
    assert [s.text for s in segments] == ["Hola mundo", "Segundo"]
    assert segments[1].end_ms == 1400


def test_ytdlp_binary_is_discoverable_or_absent_without_breaking():
    """El binario puede no estar instalado: el proveedor debe poder devolver
    None sin romperse (degrada al resto de la cadena)."""
    binary = yt_dlp_binary()
    assert binary is None or binary.exists()
    if binary is not None:
        assert yt_dlp_available_languages("dQw4w9WgXcQ") is not None
