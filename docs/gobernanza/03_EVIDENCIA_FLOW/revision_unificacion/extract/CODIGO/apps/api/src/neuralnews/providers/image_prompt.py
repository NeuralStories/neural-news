"""Generador de prompts de imagen y storyboard.

Implementación local determinista (plantilla editorial): no llama a APIs ni gasta
créditos. Genera prompts preliminares para usarlos manualmente en Google Flow u
otra herramienta; nunca afirma haber generado imágenes o vídeo.
"""
from __future__ import annotations

import re

from ..models import Approval, ScriptVersion, Story
from .base import ScriptSceneDraft, StoryboardDraft

VISUAL_STYLE = (
    "personaje @neuraldotai en plató retro con pantallas CRT, encuadre vertical 9:16, "
    "plano cercano, luz neutra, estilo realista de estudio; sin texto garabateado"
)


def estimate_duration(content: str, words_per_minute: int = 150) -> int:
    words = len(re.findall(r"\S+", content))
    return max(10, round(words / words_per_minute * 60))


def build_storyboard(story: Story, script: ScriptVersion, approval: Approval | None) -> StoryboardDraft:
    """Divide el guion en escenas orientativas (~8 s) y compone un prompt por escena."""
    paragraphs = [p.strip() for p in script.content.split("\n\n") if p.strip()]
    scenes: list[ScriptSceneDraft] = []
    for idx, paragraph in enumerate(paragraphs[:12]):
        seconds = min(15, max(4, estimate_duration(paragraph, 150)))
        first_words = " ".join(paragraph.split()[:10])
        scenes.append(
            ScriptSceneDraft(
                message=first_words + ("…" if len(paragraph.split()) > 10 else ""),
                seconds=seconds,
                visual=(
                    "Plano cercano del presentador en el plató, gesto de cierre/énfasis"
                    if idx == len(paragraphs) - 1
                    else "Plano cercano del presentador señalando a la pantalla CRT lateral"
                ),
                data_source=(
                    f"{story.title} — versión {script.version} "
                    + ("(guion aprobado)" if approval and approval.status == "ACTIVE" else "(guion no aprobado)")
                ),
                image_prompt=(
                    f"Plano vertical 9:16, {VISUAL_STYLE}. Escena {idx + 1}: {first_words}. "
                    "Sin marcas ni logotipos reales."
                ),
                overlay_text=first_words[:40],
            )
        )
    if not scenes:
        scenes.append(
            ScriptSceneDraft(
                message="Guion vacío",
                seconds=8,
                visual="Pantalla neutra",
                image_prompt=f"Plano vertical 9:16, {VISUAL_STYLE}, escena neutra",
                data_source=f"{story.title} — versión {script.version}",
            )
        )
    return StoryboardDraft(scenes=scenes)
