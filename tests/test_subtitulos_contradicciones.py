"""NN-117.6 y NN-117.7 — subtítulos SRT/VTT y contradicciones de cifras.

Ports del hermano congelado (`archive/neuralnews-20261101`), con la diferencia
de que aquí se comprueban contra el **modelo real** de este producto
(`SourceSegment`, `Claim`) y no contra el del hermano.

Reglas comprobadas:

  - el subtítulo lleva el texto **íntegro** del segmento (no se reescribe) y
    sus tiempos en orden;
  - una contradicción de cifras se **propone**, nunca se aplica: el estado de
    la afirmación no cambia solo (quien revisa es una persona);
  - dos afirmaciones que citan la misma cifra **no** se contradicen;
  - cifras con unidades distintas no se comparan.
"""
from __future__ import annotations

import pytest

from neuralnews.db import get_session_factory
from neuralnews.models import Claim, Story
from neuralnews.services import contradictions, subtitles


# --- NN-117.6: subtítulos ----------------------------------------------------


def _segmentos() -> list[dict]:
    return [
        {"start_ms": 0, "end_ms": 2500, "text": "Primera frase exacta"},
        {"start_ms": 2500, "end_ms": 5000, "text": "Segunda frase exacta"},
    ]


def test_srt_tiene_los_textos_integros() -> None:
    srt = subtitles.a_srt(_segmentos())
    assert "1\n00:00:00,000 --> 00:00:02,500\nPrimera frase exacta" in srt
    assert "2\n00:00:02,500 --> 00:00:05,000\nSegunda frase exacta" in srt


def test_vtt_empieza_por_webvtt_y_usa_puntos() -> None:
    vtt = subtitles.a_vtt(_segmentos())
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in vtt


def test_el_texto_sensible_no_añade_nada() -> None:
    assert (
        subtitles.texto_sensible(_segmentos())
        == "Primera frase exacta Segunda frase exacta"
    )


def test_los_tiempos_deben_ser_monotonos() -> None:
    assert subtitles.tiempos_monotonos(_segmentos())
    desordenados = [
        {"start_ms": 5000, "end_ms": 7000, "text": "Segunda"},
        {"start_ms": 0, "end_ms": 2000, "text": "Primera"},
    ]
    assert not subtitles.tiempos_monotonos(desordenados)


def test_los_subtitulos_salen_de_los_segmentos_de_la_base_de_datos(app_env) -> None:
    """El port real: `SourceSegment` (modelo) → SRT."""
    from neuralnews.models import SourceContent, SourceSegment, Source

    session_factory = get_session_factory()
    with session_factory() as db:
        fuente = Source(provider="manual", canonical_url="https://ejemplo.invalid/v", title="Fuente", status="READY")
        db.add(fuente)
        db.flush()
        contenido = SourceContent(
            source_id=fuente.id,
            content_type="TRANSCRIPT",
            text="Hola\nAdiós",
            content_hash="hash-de-prueba",
        )
        db.add(contenido)
        db.flush()
        db.add_all(
            [
                SourceSegment(content_id=contenido.id, start_ms=0, end_ms=1000, text="Hola", sequence=0),
                SourceSegment(content_id=contenido.id, start_ms=1000, end_ms=2000, text="Adiós", sequence=1),
            ]
        )
        db.commit()

    with session_factory() as db:
        from sqlalchemy import select

        segmentos = db.scalars(
            select(SourceSegment).where(SourceSegment.content_id == contenido.id).order_by(SourceSegment.sequence)
        ).all()
        srt = subtitles.a_srt(segmentos)
        assert "00:00:00,000 --> 00:00:01,000" in srt
        assert "Hola" in srt and "Adiós" in srt
        assert subtitles.tiempos_monotonos(segmentos)


# --- NN-117.7: contradicciones ------------------------------------------------


def _afirmaciones(app_env) -> tuple[int, list[int]]:
    session_factory = get_session_factory()
    with session_factory() as db:
        historia = Story(topic_key="clave-de-prueba", title="Historia", status="CANDIDATE")
        db.add(historia)
        db.flush()
        a = Claim(story_id=historia.id, statement="El radar mejora un 12% en rendimiento")
        b = Claim(story_id=historia.id, statement="El radar mejora un 18% en rendimiento")
        c = Claim(story_id=historia.id, statement="El radar mejora un 12% en rendimiento")
        db.add_all([a, b, c])
        db.commit()
        return historia.id, [a.id, b.id, c.id]


def test_una_cifra_distinta_con_las_mismas_palabras_se_propone(app_env) -> None:
    historia_id, ids = _afirmaciones(app_env)
    session_factory = get_session_factory()
    with session_factory() as db:
        conflictos = contradictions.conflictos_de_historia(db, historia_id)
    # A (12%) contra B (18%) y B contra C (12%): dos pares con cifras distintas.
    assert len(conflictos) == 2
    pares = {frozenset((c["claim_a"], c["claim_b"])) for c in conflictos}
    assert frozenset((str(ids[0]), str(ids[1]))) in pares
    assert frozenset((str(ids[1]), str(ids[2]))) in pares
    # A y C citan la MISMA cifra: no se contradicen.
    assert frozenset((str(ids[0]), str(ids[2]))) not in pares
    for conflicto in conflictos:
        assert conflicto["suggested_status"] == "CONTRADICTED"
        assert conflicto["action"] == "PROPOSED", "la contradicción se propone, no se aplica"


def test_la_misma_cifra_no_es_contradiccion(app_env) -> None:
    historia_id, _ids = _afirmaciones(app_env)
    session_factory = get_session_factory()
    with session_factory() as db:
        conflictos = contradictions.conflictos_de_historia(db, historia_id)
    # La tercera afirmación repite la primera: no hay conflicto con ella.
    for conflicto in conflictos:
        assert not (12.0 in conflicto["figures_a"] and 12.0 in conflicto["figures_b"])


def test_el_detector_no_cambia_el_estado_de_las_afirmaciones(app_env) -> None:
    """La regla: sin auto-cambio. El estado sigue siendo el que estaba."""
    historia_id, ids = _afirmaciones(app_env)
    session_factory = get_session_factory()
    with session_factory() as db:
        contradictions.conflictos_de_historia(db, historia_id)
    with session_factory() as db:
        for afirmacion_id in ids:
            afirmacion = db.get(Claim, afirmacion_id)
            assert afirmacion.verification_status == "UNVERIFIED"


def test_cifras_con_unidades_distintas_no_se_comparan(app_env) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        historia = Story(topic_key="clave-de-prueba", title="Historia", status="CANDIDATE")
        db.add(historia)
        db.flush()
        db.add_all(
            [
                Claim(story_id=historia.id, statement="El presupuesto es 500 € para el trimestre"),
                Claim(story_id=historia.id, statement="El presupuesto es 500 tokens para el trimestre"),
            ]
        )
        db.commit()
        historia_id = historia.id

    with session_factory() as db:
        conflictos = contradictions.conflictos_de_historia(db, historia_id)
    assert conflictos == []
