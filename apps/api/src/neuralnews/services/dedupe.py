"""Detección de posibles duplicados entre noticias.

No fusiona automáticamente: señala candidatos para que el editor decida. Se apoya en
el `topic_key` (mismo tema exacto) y en similitud de título (tokens significativos).
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Story

STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "en",
    "con", "por", "para", "su", "sus", "se", "al", "a", "the", "of", "and", "to", "in",
    "que", "como", "más", "mas", "ya", "es", "son", "ha", "han", "no", "si", "lo",
}


def _tokens(title: str) -> set[str]:
    words = re.findall(r"[a-záéíóúüñ0-9]+", (title or "").lower())
    return {w for w in words if len(w) > 3 and w not in STOPWORDS}


def title_similarity(a: str, b: str) -> float:
    """Jaccard sobre tokens significativos."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def find_possible_duplicates(db: Session, story: Story, threshold: float = 0.5) -> list[dict]:
    """Devuelve las noticias que podrían ser la misma historia que `story`."""
    candidates = db.scalars(
        select(Story).where(Story.id != story.id, Story.status != "REJECTED")
    ).all()
    found: list[dict] = []
    for other in candidates:
        if other.topic_key == story.topic_key:
            reason = "mismo tema"
            score = 1.0
        else:
            score = title_similarity(story.title, other.title)
            if score < threshold:
                continue
            reason = f"títulos parecidos ({int(score * 100)}%)"
        found.append(
            {
                "story_id": other.id,
                "title": other.title,
                "status_label": other.status,
                "reason": reason,
                "similarity": round(score, 2),
            }
        )
    found.sort(key=lambda item: item["similarity"], reverse=True)
    return found


def duplicates_for_all(db: Session) -> dict[int, list[dict]]:
    """Mapa noticia → duplicados posibles (para el listado)."""
    stories = db.scalars(select(Story).where(Story.status != "REJECTED")).all()
    result: dict[int, list[dict]] = {}
    for index, story in enumerate(stories):
        matches: list[dict] = []
        for other in stories[index + 1 :]:
            if other.topic_key == story.topic_key:
                score, reason = 1.0, "mismo tema"
            else:
                score = title_similarity(story.title, other.title)
                if score < 0.5:
                    continue
                reason = f"títulos parecidos ({int(score * 100)}%)"
            matches.append(
                {
                    "story_id": other.id,
                    "title": other.title,
                    "status_label": other.status,
                    "reason": reason,
                    "similarity": round(score, 2),
                }
            )
        if matches:
            result[story.id] = matches
    return result
