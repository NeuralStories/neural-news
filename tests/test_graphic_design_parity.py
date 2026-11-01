"""NN-107 — Paridad de diseño gráfico: UN solo sistema.

El SVG de la UI y la tarjeta PNG del montaje derivan del mismo modelo
(chart_model) con la misma paleta y geometría: no existen dos versiones
gráficas de un mismo gráfico."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api" / "src"))

from PIL import Image

from neuralnews.services.graphics import (
    CARD_H, CARD_SCALE, CARD_W, COLORS, H, W, chart_model, render_bar_svg,
    render_chart_png_1080x1920, render_title_png_1080x1920,
)

SPEC = {
    "title": "Valoración de Anthropic (miles de millones USD)",
    "series": [
        {"label": "mar 2025", "value": 61.5, "unit": "G$"},
        {"label": "feb 2026", "value": 380, "unit": "G$"},
        {"label": "may 2026", "value": 965, "unit": "G$"},
    ],
    "source_note": "Fuente: Reuters",
}


def test_svg_and_png_derive_from_the_same_model():
    model = chart_model(SPEC)
    assert [b["value_text"] for b in model["bars"]] == ["61.5 G$", "380 G$", "965 G$"]
    # geometría normalizada idéntica en ambos renderizadores (mismo modelo)
    svg = render_bar_svg(SPEC)
    assert all(f'fill="{COLORS["bar"]}"' in svg for _ in [1])
    assert "61.5 G$" in svg and "380 G$" in svg and "965 G$" in svg
    assert COLORS["title"] in svg and COLORS["source"] in svg


def test_png_card_uses_same_palette_and_exact_values():
    png_bytes = render_chart_png_1080x1920(SPEC)
    img = Image.open(__import__("io").BytesIO(png_bytes))
    assert img.size == (CARD_W, CARD_H)  # 1080x1920 para el montaje 9:16
    # paleta única: el fondo y una barra del gráfico son los colores del diseño
    assert img.getpixel((10, 10)) == (2, 6, 23)  # bg #020617
    # el píxel central de la barra más alta es el color de barra del diseño
    model = chart_model(SPEC)
    tallest = max(model["bars"], key=lambda b: b["h"])
    cx = int(tallest["value_center_x"] * CARD_SCALE)
    cy = int((tallest["y"] + tallest["h"] / 2) * CARD_SCALE) + (CARD_H - round(H * CARD_SCALE)) // 2
    assert img.getpixel((cx, cy)) == (56, 189, 248)  # #38bdf8


def test_title_card_uses_the_same_identity():
    png_bytes = render_title_png_1080x1920("NEURAL NEWS - PILOTO 001",
                                           ["Rótulo de apertura"], "ANIMÁTICA")
    img = Image.open(__import__("io").BytesIO(png_bytes))
    assert img.size == (CARD_W, CARD_H)
    assert img.getpixel((10, 10)) == (2, 6, 23)


def test_montage_timeline_uses_the_shared_design():
    from neuralnews.services.montage import timeline  # importa el montaje unificado
    import neuralnews.services.montage as m
    assert "render_chart_png_1080x1920" in Path(m.__file__).read_text(encoding="utf-8")
    assert "_render_card" not in Path(m.__file__).read_text(encoding="utf-8")
