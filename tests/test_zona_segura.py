"""NN-117.2 — Zona segura: el rótulo respeta los márgenes del diseño.

Contexto de la decisión (no es un port literal):

  - El repo hermano define `SAFE_ZONE` en `app/domain/graphics.py`, pero **no
    lo usa en ninguna parte**: portarlo sería traer código muerto.
  - La carencia **real** estaba en el repo activo: el gráfico de barras usaba
    el sistema de márgenes (`MARGIN_L/R/T/B`) y el rótulo usaba coordenadas
    fijas (80, 500), que no respetaban ese margen. El texto podía salirse del
    área que la interfaz de la plataforma cubre.

Por eso NN-117.2 se resuelve **arreglando la incoherencia del repo activo**,
no copiando la constante muerta del hermano.
"""
from __future__ import annotations

import io

from PIL import Image

from neuralnews.services.graphics import (
    CARD_H,
    CARD_MARGIN_B,
    CARD_MARGIN_L,
    CARD_MARGIN_R,
    CARD_MARGIN_T,
    CARD_SAFE_W,
    CARD_W,
    MARGIN_B,
    MARGIN_L,
    MARGIN_R,
    MARGIN_T,
    render_chart_png_1080x1920,
    render_title_png_1080x1920,
)


def test_la_zona_segura_es_la_del_diseno_escalada():
    """La zona segura de la tarjeta son los márgenes del diseño, escalados."""
    assert CARD_MARGIN_L == MARGIN_L * (CARD_W / 480)
    assert CARD_MARGIN_R == MARGIN_R * (CARD_W / 480)
    assert CARD_MARGIN_T == MARGIN_T * (CARD_W / 480)
    assert CARD_MARGIN_B == MARGIN_B * (CARD_W / 480)


def test_el_rotulo_no_empieza_antes_del_margen_izquierdo():
    """El texto del rótulo empieza dentro del margen izquierdo."""
    png = render_title_png_1080x1920("TITULAR", ["Una línea"], "Fuente")
    img = Image.open(io.BytesIO(png)).convert("L")
    ancho, alto = img.size
    # La primera columna con píxeles claros es el borde izquierdo del texto.
    umbral = 60
    primera = None
    for x in range(ancho):
        for y in range(alto):
            if img.getpixel((x, y)) > umbral:
                primera = x
                break
        if primera is not None:
            break
    assert primera is not None, "el rótulo no tiene texto"
    assert primera >= CARD_MARGIN_L - 1, (
        f"el texto empieza en {primera} px, antes del margen {CARD_MARGIN_L:.0f}"
    )


def test_el_rotulo_no_se_sale_del_ancho_util():
    """Un texto muy largo se recorta por ancho real, no se desborda."""
    largo = "T" * 200
    png = render_title_png_1080x1920(largo, [largo], largo)
    img = Image.open(io.BytesIO(png)).convert("L")
    ancho, alto = img.size
    umbral = 60
    ultima = None
    for x in range(ancho - 1, -1, -1):
        for y in range(alto):
            if img.getpixel((x, y)) > umbral:
                ultima = x
                break
        if ultima is not None:
            break
    assert ultima is not None, "el rótulo no tiene texto"
    assert ultima <= CARD_W - CARD_MARGIN_R + 1, (
        f"el texto llega a {ultima} px, más allá del margen derecho {CARD_W - CARD_MARGIN_R:.0f}"
    )


def test_el_grafico_y_el_rotulo_comparten_zona_segura():
    """El gráfico y el rótulo respetan la misma zona: es el mismo diseño."""
    assert CARD_SAFE_W == CARD_W - CARD_MARGIN_L - CARD_MARGIN_R
    png_grafico = render_chart_png_1080x1920(
        {
            "title": "Un título",
            "series": [{"label": "mar 2026", "value": 10, "unit": "%"}],
            "source_note": "Fuente",
        }
    )
    png_rotulo = render_title_png_1080x1920("Un título", ["Una línea"], "Fuente")
    assert Image.open(io.BytesIO(png_grafico)).size == Image.open(io.BytesIO(png_rotulo)).size


def test_el_rotulo_sigue_siendo_una_imagen_valida():
    png = render_title_png_1080x1920("NEURAL NEWS", ["Rótulo"], "ANIMÁTICA")
    img = Image.open(io.BytesIO(png))
    assert img.size == (CARD_W, CARD_H)
    assert img.getpixel((10, 10)) == (2, 6, 23)  # fondo del diseño
