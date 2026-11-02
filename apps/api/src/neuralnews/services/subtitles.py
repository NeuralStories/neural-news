"""Subtítulos SRT/VTT a partir de los segmentos de transcripción (NN-117.6).

Port del módulo `app/domain/subtitles.py` del hermano congelado
(`archive/neuralnews-20261101`), con la diferencia de que aquí los segmentos son
los de `SourceSegment` de la base de datos (con `start_ms`, `end_ms` y `text`).

Regla del port: el texto sale **íntegro** (round-trip) con tiempos monótonos;
nada se reescribe ni se resume. Un subtítulo que «mejora» el texto de la fuente
sería una falsificación.
"""
from __future__ import annotations

from typing import Iterable, Protocol


class Segmento(Protocol):
    """Lo mínimo que hace falta de un segmento (modelo o diccionario)."""

    start_ms: int | None
    end_ms: int | None
    text: str


def _campos(segmento) -> tuple[int, int, str]:
    if isinstance(segmento, dict):
        return (
            int(segmento.get("start_ms") or 0),
            int(segmento.get("end_ms") or 0),
            str(segmento.get("text") or ""),
        )
    return (
        int(segmento.start_ms or 0),
        int(segmento.end_ms or 0),
        str(segmento.text or ""),
    )


def _ms_a_srt(ms: int) -> str:
    horas, resto = divmod(max(ms, 0), 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos, milis = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d},{milis:03d}"


def _ms_a_vtt(ms: int) -> str:
    return _ms_a_srt(ms).replace(",", ".")


def a_srt(segmentos: Iterable) -> str:
    """SRT con los tiempos del segmento y su texto íntegro."""
    bloques = []
    for indice, segmento in enumerate(segmentos, start=1):
        inicio, fin, texto = _campos(segmento)
        bloques.append(f"{indice}\n{_ms_a_srt(inicio)} --> {_ms_a_srt(fin)}\n{texto}\n")
    return "\n".join(bloques)


def a_vtt(segmentos: Iterable) -> str:
    """VTT (WebVTT) con los tiempos del segmento y su texto íntegro."""
    lineas = ["WEBVTT", ""]
    for indice, segmento in enumerate(segmentos, start=1):
        inicio, fin, texto = _campos(segmento)
        lineas.append(str(indice))
        lineas.append(f"{_ms_a_vtt(inicio)} --> {_ms_a_vtt(fin)}")
        lineas.append(texto)
        lineas.append("")
    return "\n".join(lineas)


def texto_sensible(segmentos: Iterable) -> str:
    """El texto completo, sin nada añadido: sirve para comparar con la fuente."""
    return " ".join(_campos(s)[2] for s in segmentos)


def tiempos_monotonos(segmentos: Iterable) -> bool:
    """¿Los tiempos van en orden y no se solapan? Un subtítulo no puede ir atrás."""
    anterior_fin = -1
    for segmento in segmentos:
        inicio, fin, _texto = _campos(segmento)
        if inicio < anterior_fin:
            return False
        anterior_fin = max(anterior_fin, fin)
    return True
