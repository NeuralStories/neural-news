"""Gráficos programáticos (NN-107 F4, cap. 11 de la especificación).

Un GraphicSpec toma sus valores de afirmaciones aprobadas o de datos que el
editor introduce y verifica; el SVG se genera de forma determinista y jamás se
pide a un modelo generativo que invente cifras. Cambiar el guion invalida los
gráficos derivados (invalidación dirigida del cap. 13).
"""
from __future__ import annotations

import html
from typing import Any

W, H = 480, 320
MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 70, 24, 40, 56
BAR_AREA_W = W - MARGIN_L - MARGIN_R
BAR_AREA_H = H - MARGIN_T - MARGIN_B


def render_bar_svg(spec: dict) -> str:
    """SVG determinista de barras a partir de `series` [{label, value, unit}].
    Los valores se dibujan exactamente como están en el spec (nunca inventados)
    y cada gráfico lleva su pie de fuente."""
    series: list[dict[str, Any]] = spec.get("series", [])
    if not series:
        raise ValueError("El gráfico no tiene series de datos")

    max_value = max(float(s.get("value", 0)) for s in series)
    if max_value <= 0:
        max_value = 1.0

    n = len(series)
    slot = BAR_AREA_W / n
    bar_w = min(slot * 0.62, 90.0)
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img">',
        f'<rect width="{W}" height="{H}" fill="#020617"/>',
        f'<text x="{MARGIN_L}" y="22" fill="#fbbf24" font-family="monospace" font-size="13">'
        f'{html.escape(str(spec.get("title", "Gráfico")))}</text>',
        f'<line x1="{MARGIN_L}" y1="{H - MARGIN_B}" x2="{W - MARGIN_R}" y2="{H - MARGIN_B}" stroke="#475569"/>',
    ]
    for i, item in enumerate(series):
        value = float(item.get("value", 0))
        unit = str(item.get("unit", "")).strip()
        label = html.escape(str(item.get("label", f"Serie {i + 1}")))
        bar_h = BAR_AREA_H * (value / max_value) if max_value else 0
        x = MARGIN_L + i * slot + (slot - bar_w) / 2
        y = H - MARGIN_B - bar_h
        value_text = html.escape(f"{value:g}{(' ' + unit) if unit else ''}")
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="#38bdf8"/>')
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" fill="#e2e8f0" font-family="monospace" '
            f'font-size="11" text-anchor="middle">{value_text}</text>'
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{H - MARGIN_B + 16:.1f}" fill="#94a3b8" '
            f'font-family="monospace" font-size="9" text-anchor="middle">{label[:14]}</text>'
        )
    source = html.escape(str(spec.get("source_note", "Datos del dossier editorial verificado")))
    parts.append(
        f'<text x="{MARGIN_L}" y="{H - 8}" fill="#64748b" font-family="monospace" font-size="8">{source}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
