"""Director audiovisual determinista (NN-107 F3, cap. 7 de la especificación).

Convierte el guion del proyecto en beats de locución y ventanas de tomas SIN
imponer cortes de 8 segundos (F-05: la locución es continua; los cortes solo
responden a la capacidad del proveedor, `provider_max_clip_s`).

Reglas de selección de recurso (cap. 7, deterministas y auditables):
  1. Afirmación con cita/atribución explícita → DOCUMENTARY (evidencia auténtica).
  2. Cifra exacta (número, porcentaje, moneda) → DATA_GRAPHIC (gráfico
     programático; nunca se pide a un generativo que invente cifras).
  3. Apertura y cierre con el presentador → FLOW_MAXDOTAI (ficha canónica).
  4. Contenido abstracto de relleno → GENERATIVE_BROLL etiquetado ilustrativo.
  5. Por defecto → PENDING si faltan activos; el cheapest válido prevalece
     salvo veracidad/continuidad.

Devuelve dicts listos para persistir en NarrationBeat y Shot (endpoints F1).
El mismo guion produce siempre el mismo plan (determinista).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

WORDS_PER_SECOND = 2.85  # misma constante que utils/scriptAnalyzer.ts (hipótesis editable)
CLAUSE_REGEX = re.compile(r"[^.!?;\n]+(?:[.!?;\n]+|$)")
NUMBER_REGEX = re.compile(r"\d+([.,]\d+)?\s?(%|por ciento|€|\$|mil millones|millones)")
QUOTE_REGEX = re.compile(r"(«[^»]+»|\"[^\"]+\")|según|declaró|afirmó|anunció|confirmó", re.IGNORECASE)


@dataclass
class DirectorPlan:
    beats: list[dict]
    shots: list[dict]


def _sentences(text: str) -> list[str]:
    clauses = [m.group(0).strip() for m in CLAUSE_REGEX.finditer(text.strip()) if m.group(0).strip()]
    return clauses or ([text.strip()] if text.strip() else [])


def _est_seconds(sentence: str) -> float:
    words = len([w for w in sentence.split() if w])
    return round(words / WORDS_PER_SECOND, 2)


def _shot_kind(sentences: list[str], is_first: bool, is_last: bool) -> tuple[str, str]:
    """Decide el recurso del shot y por qué (cap. 7: registrar por qué se ve eso)."""
    joined = " ".join(sentences)
    if NUMBER_REGEX.search(joined):
        return (
            "DATA_GRAPHIC",
            "Contiene cifras exactas: gráfico programático con los valores verificados; "
            "nunca se pide a un generativo que invente números.",
        )
    if QUOTE_REGEX.search(joined):
        return (
            "DOCUMENTARY",
            "Atribución o cita explícita: se usa material auténtico o captura real con "
            "procedencia, no recreación generativa.",
        )
    if is_first or is_last:
        return (
            "FLOW_MAXDOTAI",
            "Apertura/cierre del bloque con el presentador canónico maxDotAi desde su "
            "ficha maestra (una sola identidad, sin describir un personaje nuevo por prompt).",
        )
    return (
        "GENERATIVE_BROLL",
        "Contexto abstracto: B-roll generativo etiquetado como ilustrativo, sin simular "
        "evidencia de hechos reales.",
    )


def build_plan(
    script_text: str,
    provider_max_clip_s: float = 8.0,
    target_duration_s: float | None = None,
) -> DirectorPlan:
    """Beats = frases del guion (locución continua, sin cortes impuestos).
    Shots = ventanas que cubren la línea temporal agrupando beats hasta
    `provider_max_clip_s` (capacidad del proveedor, no límite narrativo)."""
    sentences = _sentences(script_text)
    beats: list[dict] = []
    for i, sentence in enumerate(sentences):
        beats.append(
            {
                "sequence": i,
                "text": sentence,
                "est_seconds": _est_seconds(sentence),
                "claim_ids": [],
            }
        )

    shots: list[dict] = []
    window: list[dict] = []
    window_seconds = 0.0

    def close_window():
        nonlocal window, window_seconds
        if not window:
            return
        start = round(sum(b["est_seconds"] for b in beats[: window[0]["sequence"]]), 2)
        duration = round(sum(b["est_seconds"] for b in window), 2)
        texts = [b["text"] for b in window]
        kind, rationale = _shot_kind(texts, is_first=not shots, is_last=False)
        shots.append(
            {
                "sequence": len(shots),
                "beat_id": None,
                "shot_kind": kind,
                "rationale": rationale,
                "start_s": start,
                "end_s": round(start + duration, 2),
                "max_duration_s": provider_max_clip_s,
                "data": {"beat_texts": texts, "est_duration_s": duration},
            }
        )
        window = []
        window_seconds = 0.0

    for beat in beats:
        if window and window_seconds + beat["est_seconds"] > provider_max_clip_s:
            close_window()
        window.append(beat)
        window_seconds += beat["est_seconds"]
    close_window()

    # El cierre siempre es del presentador (regla cap. 7), si hay tomas.
    if shots:
        last = shots[-1]
        kind, rationale = _shot_kind(last["data"]["beat_texts"], is_first=False, is_last=True)
        last["shot_kind"] = kind
        last["rationale"] = rationale

    return DirectorPlan(beats=beats, shots=shots)
