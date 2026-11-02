"""NN-114.3 — `providers/research.py` y `providers/video_analysis.py` sin test.

Los dos adaptadores son **capacidad real** (no código muerto) y sus reglas son
estrictas: el primero no debe fabricar citas y el segundo no debe presentar un
análisis como si fuera transcripción literal. Esas reglas no estaban cubiertas
por ninguna prueba.

Reglas comprobadas aquí:

  - `ResearchSearchProvider` en modo demo: la evidencia ficticia usa el
    dominio reservado `.invalid` y se marca como DEMO; una opinión no se
    «verifica»; una afirmación sin evidencia queda `UNVERIFIED` (nunca
    `SUPPORTED` porque la búsqueda no haya dado resultados.
  - En modo real, sin clave o con los servicios de pago desactivados, **falla**
    con un mensaje claro en lugar de devolver una simulación.
  - `call_gemini_video_analysis` exige clave y su salida se marca siempre
    `VIDEO_ANALYSIS` con `is_verbatim=False`.
  - `extract_json_block` recorta el objeto JSON aunque el modelo lo envuelva en
    vallas de código, y falla si no hay objeto.
  - `_mmss_to_ms` convierte bien los tiempos y devuelve `None` si no puede.
"""
from __future__ import annotations

import pytest

from neuralnews.providers import research as research_provider
from neuralnews.providers import video_analysis as video_provider


# --- providers/research.py ---------------------------------------------------


def test_demo_una_opinion_no_se_verifica() -> None:
    proveedor = research_provider.ResearchSearchProvider(demo=True)
    borrador = proveedor.research(["Es una opinión personal sobre el futuro del sector"])
    afirmacion = borrador.claims[0]
    assert afirmacion.verification_status == "NOT_VERIFIABLE"
    assert afirmacion.evidence == []
    assert "opinión" in (afirmacion.verification_notes or "").lower()


def test_demo_la_evidencia_ficticia_usa_el_dominio_reservado_y_se_marca() -> None:
    proveedor = research_provider.ResearchSearchProvider(demo=True)
    borrador = proveedor.research(["Radar mejoró un 12% en benchmarks"])
    afirmacion = borrador.claims[0]
    assert afirmacion.verification_status == "SUPPORTED"
    assert afirmacion.evidence, "debería adjuntar la evidencia de demo"
    for evidencia in afirmacion.evidence:
        # El dominio reservado es `.invalid` (RFC 2606): la URL **no** termina
        # en él porque lleva ruta debajo.
        host = evidencia.url.split("//", 1)[-1].split("/", 1)[0]
        assert host.endswith(".invalid"), evidencia.url
        assert "demo.neuralnews.invalid" in evidencia.url
    assert "DEMO" in (afirmacion.verification_notes or "")


def test_demo_sin_evidencia_no_se_da_por_confirmada() -> None:
    proveedor = research_provider.ResearchSearchProvider(demo=True)
    borrador = proveedor.research(["Vireo mueve 40 millones de usuarios al mes"])
    afirmacion = borrador.claims[0]
    assert afirmacion.verification_status == "UNVERIFIED"
    assert afirmacion.evidence == []


def test_demo_una_afirmacion_desconocida_queda_sin_verificar() -> None:
    proveedor = research_provider.ResearchSearchProvider(demo=True)
    borrador = proveedor.research(["Una afirmación sin ningún patrón conocido"])
    afirmacion = borrador.claims[0]
    assert afirmacion.verification_status == "UNVERIFIED"
    assert afirmacion.evidence == []


def test_la_evidencia_de_demo_es_determinista() -> None:
    """Dos llamadas con la misma afirmación dan las mismas URLs."""
    primero = research_provider.ResearchSearchProvider(demo=True).research(["Radar mejoró un 12%"])
    segundo = research_provider.ResearchSearchProvider(demo=True).research(["Radar mejoró un 12%"])
    assert [e.url for e in primero.claims[0].evidence] == [
        e.url for e in segundo.claims[0].evidence
    ]


def test_modo_real_sin_clave_falla_en_vez_de_simular(monkeypatch) -> None:
    monkeypatch.setattr(
        research_provider.secrets_service, "clave_de_proveedor", lambda *_a, **_k: None
    )
    proveedor = research_provider.ResearchSearchProvider(demo=False)
    assert proveedor.has_key is False
    with pytest.raises(RuntimeError) as exc:
        proveedor.research(["Afirmación cualquiera"])
    assert "clave" in str(exc.value).lower()


def test_modo_real_con_pago_desactivado_falla(monkeypatch) -> None:
    monkeypatch.setattr(
        research_provider.secrets_service, "clave_de_proveedor", lambda *_a, **_k: "clave-falsa"
    )

    class _Ajustes:
        demo_mode = False
        paid_services_enabled = False
        search_base_url = "https://api.search.brave.com/res/v1/web/search"

    monkeypatch.setattr(research_provider, "get_settings", lambda: _Ajustes())
    proveedor = research_provider.ResearchSearchProvider(demo=False)
    with pytest.raises(RuntimeError) as exc:
        proveedor.research(["Afirmación cualquiera"])
    assert "pago" in str(exc.value).lower()


# --- providers/video_analysis.py ----------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [("01:30", 90_000), ("00:05", 5_000), ("12:00", 720_000), ("1:00", 60_000)],
)
def test_mmss_a_milisegundos(entrada, esperado) -> None:
    assert video_provider._mmss_to_ms(entrada) == esperado


@pytest.mark.parametrize("entrada", [None, "", "no-es-tiempo", "1:2:3", "99"])
def test_mmss_a_milisegundos_devuelve_none_si_no_puede(entrada) -> None:
    assert video_provider._mmss_to_ms(entrada) is None


def test_extract_json_block_quita_las_vallas_de_codigo() -> None:
    texto = '```json\n{"summary": "hola"}\n```'
    assert video_provider.extract_json_block(texto) == '{"summary": "hola"}'


def test_extract_json_block_recorta_al_objeto_principal() -> None:
    texto = 'Aquí tienes el JSON: {"summary": "hola", "topics": []} — listo.'
    assert video_provider.extract_json_block(texto) == '{"summary": "hola", "topics": []}'


def test_extract_json_block_falla_si_no_hay_objeto() -> None:
    with pytest.raises(ValueError):
        video_provider.extract_json_block("no hay json aquí")


def test_analisis_de_video_sin_clave_falla_en_vez_de_simular(monkeypatch) -> None:
    monkeypatch.setattr(
        video_provider.secrets_service, "clave_de_proveedor", lambda *_a, **_k: None
    )
    with pytest.raises(RuntimeError) as exc:
        video_provider.call_gemini_video_analysis("https://www.youtube.com/watch?v=abc")
    assert "gemini" in str(exc.value).lower()


def test_la_salida_de_video_marca_que_no_es_transcripcion(monkeypatch) -> None:
    """La rama real: se comprueba el contrato de la salida, sin llamar a Gemini."""
    monkeypatch.setattr(
        video_provider.secrets_service,
        "clave_de_proveedor",
        lambda *_a, **_k: "clave-falsa",
    )

    class _Respuesta:
        @staticmethod
        def raise_for_status() -> None:
            return None

        @staticmethod
        def json() -> dict:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"summary": "Resumen del vídeo", "topics": '
                                        '[{"title": "t", "facts": ["f"], "timestamps": '
                                        '[{"mmss": "00:10", "fact": "hecho"}]}]}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    class _Ajustes:
        llm_model = "modelo-de-prueba"

    monkeypatch.setattr(video_provider, "get_settings", lambda: _Ajustes())
    monkeypatch.setattr(video_provider.httpx, "post", lambda *a, **k: _Respuesta())

    resultado = video_provider.call_gemini_video_analysis("https://www.youtube.com/watch?v=abc")
    contenido = resultado.contents[0]
    assert contenido.content_type == "VIDEO_ANALYSIS"
    assert contenido.is_verbatim is False
    assert "no es transcripción literal" in contenido.text
    assert contenido.segments[0].start_ms == 10_000
    assert resultado.metadata["demo"] is False
