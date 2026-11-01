"""Gráficos programáticos (NN-107 F4, cap. 11 de la especificación).

UN ÚNICO SISTEMA DE DISEÑO GRÁFICO: todas las representaciones (SVG para la
UI y tarjetas PNG 1080x1920 para el montaje) derivan del mismo modelo
(`chart_model`) con la misma paleta y la misma geometría. No existen dos
versiones gráficas de un mismo gráfico.

Los valores se toman exactamente del spec (afirmaciones aprobadas o datos que
el editor verifica); jamás se pide a un modelo generativo que invente cifras.
Cambiar el guion invalida los gráficos derivados (invalidación dirigida).
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paleta y geometría del diseño único (identidad neural.news Studio)
# ---------------------------------------------------------------------------
W, H = 480, 320
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 70, 24, 40, 56
BAR_AREA_W = W - MARGIN_L - MARGIN_R
BAR_AREA_H = H - MARGIN_T - MARGIN_B

COLORS = {
    "bg": "#020617",
    "title": "#fbbf24",
    "bar": "#38bdf8",
    "value": "#e2e8f0",
    "axis": "#475569",
    "label": "#94a3b8",
    "source": "#64748b",
}
FONT_FAMILY = "monospace"
FONT_TITLE_PX = 13
FONT_VALUE_PX = 11
FONT_LABEL_PX = 9
FONT_SOURCE_PX = 8


def chart_model(spec: dict) -> dict:
    """Modelo normalizado del gráfico: una sola fuente de verdad de geometría,
    valores formateados y textos, compartida por el SVG y el PNG."""
    series: list[dict[str, Any]] = spec.get("series", [])
    if not series:
        raise ValueError("El gráfico no tiene series de datos")

    max_value = max(float(s.get("value", 0)) for s in series)
    if max_value <= 0:
        max_value = 1.0

    n = len(series)
    slot = BAR_AREA_W / n
    bar_w = min(slot * 0.62, 90.0)

    bars: list[dict[str, Any]] = []
    for i, item in enumerate(series):
        value = float(item.get("value", 0))
        unit = str(item.get("unit", "")).strip()
        label = str(item.get("label", f"Serie {i + 1}"))
        bar_h = BAR_AREA_H * (value / max_value) if max_value else 0
        x = MARGIN_L + i * slot + (slot - bar_w) / 2
        y = H - MARGIN_B - bar_h
        value_text = f"{value:g}{(' ' + unit) if unit else ''}"
        bars.append({
            "x": x, "y": y, "w": bar_w, "h": bar_h,
            "label": label[:14],
            "value_text": value_text,
            "value_center_x": x + bar_w / 2,
        })

    return {
        "title": str(spec.get("title", "Gráfico")),
        "bars": bars,
        "axis_y": H - MARGIN_B,
        "source_note": str(spec.get("source_note", "Datos del dossier editorial verificado")),
    }


def render_bar_svg(spec: dict) -> str:
    """SVG determinista para la UI, derivado del modelo único."""
    model = chart_model(spec)
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img">',
        f'<rect width="{W}" height="{H}" fill="{COLORS["bg"]}"/>',
        f'<text x="{MARGIN_L}" y="22" fill="{COLORS["title"]}" font-family="{FONT_FAMILY}" '
        f'font-size="{FONT_TITLE_PX}">{html.escape(model["title"])}</text>',
        f'<line x1="{MARGIN_L}" y1="{model["axis_y"]}" x2="{W - MARGIN_R}" y2="{model["axis_y"]}" '
        f'stroke="{COLORS["axis"]}"/>',
    ]
    for bar in model["bars"]:
        parts.append(
            f'<rect x="{bar["x"]:.1f}" y="{bar["y"]:.1f}" width="{bar["w"]:.1f}" height="{bar["h"]:.1f}" '
            f'fill="{COLORS["bar"]}"/>'
        )
        parts.append(
            f'<text x="{bar["value_center_x"]:.1f}" y="{bar["y"] - 6:.1f}" fill="{COLORS["value"]}" '
            f'font-family="{FONT_FAMILY}" font-size="{FONT_VALUE_PX}" text-anchor="middle">'
            f'{html.escape(bar["value_text"])}</text>'
        )
        parts.append(
            f'<text x="{bar["value_center_x"]:.1f}" y="{model["axis_y"] + 16:.1f}" fill="{COLORS["label"]}" '
            f'font-family="{FONT_FAMILY}" font-size="{FONT_LABEL_PX}" text-anchor="middle">'
            f'{html.escape(bar["label"])}</text>'
        )
    parts.append(
        f'<text x="{MARGIN_L}" y="{H - 8}" fill="{COLORS["source"]}" font-family="{FONT_FAMILY}" '
        f'font-size="{FONT_SOURCE_PX}">{html.escape(model["source_note"])}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Tarjetas 1080x1920 para el montaje (mismo diseño, escalado 2,25× y centrado)
# ---------------------------------------------------------------------------
CARD_W, CARD_H = 1080, 1920
CARD_SCALE = CARD_W / W  # 2,25
_CARD_FONT_CACHE: dict[int, Any] = {}


def _card_font(px_design: int) -> Any:
    """Fuente monospace del sistema al tamaño del diseño escalado."""
    from PIL import ImageFont
    size = max(12, round(px_design * CARD_SCALE))
    if size in _CARD_FONT_CACHE:
        return _CARD_FONT_CACHE[size]
    font = None
    for cand in ("C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/consola.ttf",
                 "C:/Windows/Fonts/cour.ttf"):
        if Path(cand).exists():
            font = ImageFont.truetype(cand, size)
            break
    if font is None:
        font = ImageFont.load_default()
    _CARD_FONT_CACHE[size] = font
    return font


def _draw_design(draw: Any, model: dict, offset_y: int) -> None:
    """Dibuja el modelo único sobre el lienzo (misma geometría escalada)."""
    draw.rectangle([0, offset_y, CARD_W, offset_y + round(H * CARD_SCALE)], fill=COLORS["bg"])
    draw.text((MARGIN_L * CARD_SCALE, offset_y + 22 * CARD_SCALE - 26), model["title"],
              font=_card_font(FONT_TITLE_PX), fill=COLORS["title"])
    draw.line([MARGIN_L * CARD_SCALE, offset_y + model["axis_y"] * CARD_SCALE,
               (W - MARGIN_R) * CARD_SCALE, offset_y + model["axis_y"] * CARD_SCALE],
              fill=COLORS["axis"], width=3)
    for bar in model["bars"]:
        x, y = bar["x"] * CARD_SCALE, offset_y + bar["y"] * CARD_SCALE
        w, h = bar["w"] * CARD_SCALE, bar["h"] * CARD_SCALE
        draw.rectangle([x, y, x + w, y + h], fill=COLORS["bar"])
        draw.text((bar["value_center_x"] * CARD_SCALE, y - 34), bar["value_text"],
                  font=_card_font(FONT_VALUE_PX), fill=COLORS["value"], anchor="mm")
        draw.text((bar["value_center_x"] * CARD_SCALE, offset_y + model["axis_y"] * CARD_SCALE + 36),
                  bar["label"], font=_card_font(FONT_LABEL_PX), fill=COLORS["label"], anchor="mm")
    draw.text((MARGIN_L * CARD_SCALE, offset_y + (H - 8) * CARD_SCALE), model["source_note"],
              font=_card_font(FONT_SOURCE_PX), fill=COLORS["source"])


def render_chart_png_1080x1920(spec: dict) -> bytes:
    """Tarjeta de gráfico 1080x1920: el MISMO diseño del SVG (misma paleta,
    misma geometría escalada 2,25× y centrada verticalmente)."""
    from io import BytesIO

    from PIL import Image, ImageDraw
    model = chart_model(spec)
    img = Image.new("RGB", (CARD_W, CARD_H), COLORS["bg"])
    d = ImageDraw.Draw(img)
    offset_y = (CARD_H - round(H * CARD_SCALE)) // 2
    _draw_design(d, model, offset_y)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_title_png_1080x1920(title: str, lines: list[str], source_note: str = "") -> bytes:
    """Rótulo/titular 1080x1920 con la misma identidad (paleta única)."""
    from io import BytesIO

    from PIL import Image, ImageDraw
    img = Image.new("RGB", (CARD_W, CARD_H), COLORS["bg"])
    d = ImageDraw.Draw(img)
    d.text((80, 500), title[:34], font=_card_font(FONT_TITLE_PX), fill=COLORS["title"])
    y = 640
    for line in lines:
        d.text((80, y), line[:30], font=_card_font(FONT_VALUE_PX), fill=COLORS["value"])
        y += 160
    if source_note:
        d.text((80, CARD_H - 200), source_note[:60], font=_card_font(FONT_SOURCE_PX),
               fill=COLORS["source"])
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
