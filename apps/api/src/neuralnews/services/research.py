"""Investigación y puntuación editorial.

La investigación adjunta evidencia realmente recuperada (o simulada en demo, marcada);
nunca convierte por sí sola un dato no verificado en verificado. La puntuación es
orientativa, configurable y registra el desglose de criterios.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Claim, Evidence, Story, StorySource, utcnow
from ..providers.research import ResearchSearchProvider
from ..states import STORY_TRANSITIONS, assert_transition

DEFAULT_SCORE_WEIGHTS = {
    "impacto": 35,
    "verificacion": 30,
    "novedad": 20,
    "visual": 15,
}
NOVELTY_BONUS = {"NEW_EVENT": 1.0, "UPDATE": 0.7, "ANALYSIS": 0.4, "OPINION": 0.1}


def get_score_weights(db: Session) -> dict:
    from ..models import Setting

    row = db.get(Setting, "score_weights")
    if row and isinstance(row.value, dict):
        return {**DEFAULT_SCORE_WEIGHTS, **row.value}
    return dict(DEFAULT_SCORE_WEIGHTS)


def score_story(db: Session, story: Story) -> float:
    """Puntuación sobre 100: impacto 35, verificación 30, novedad 20, potencial visual 15."""
    weights = get_score_weights(db)
    claims = db.scalars(select(Claim).where(Claim.story_id == story.id)).all()
    supported = [c for c in claims if c.verification_status == "SUPPORTED"]
    contradicted = [c for c in claims if c.verification_status == "CONTRADICTED"]
    unverified = [c for c in claims if c.verification_status == "UNVERIFIED"]
    not_verifiable = [c for c in claims if c.verification_status == "NOT_VERIFIABLE"]

    # Impacto: heurística simple sobre entidades y hechos confirmados (demo determinista).
    impact = 0.5
    if supported and not contradicted:
        impact = 0.8
    if contradicted:
        impact = 0.3
    if story.is_opinion:
        impact = 0.2

    verification = 0.0
    if claims:
        verification = len(supported) / len(claims) * (0.7 if unverified or not_verifiable else 1.0)
    verification = min(1.0, verification)

    novelty = NOVELTY_BONUS.get(
        story.score_breakdown.get("novelty", "NEW_EVENT") if story.score_breakdown else "NEW_EVENT", 0.5
    )
    visual = 0.5
    if supported:
        visual = 0.7

    breakdown = {
        "impacto": round(impact * weights["impacto"], 1),
        "verificacion": round(verification * weights["verificacion"], 1),
        "novedad": round(novelty * weights["novedad"], 1),
        "visual": round(visual * weights["visual"], 1),
        "criterios": {
            "pesos": weights,
            "claims_totales": len(claims),
            "claims_confirmadas": len(supported),
            "claims_sin_verificar": len(unverified),
            "claims_contradichas": len(contradicted),
            "no_verificables": len(not_verifiable),
        },
    }
    story.score_breakdown = breakdown
    story.editorial_score = round(sum(v for k, v in breakdown.items() if isinstance(v, (int, float))), 1)
    return story.editorial_score


def research_story(db: Session, story: Story) -> Story:
    """Ejecuta la investigación de las afirmaciones de una noticia."""
    assert_transition("story", story.status, "RESEARCHING")
    story.status = "RESEARCHING"
    db.flush()

    claims = db.scalars(select(Claim).where(Claim.story_id == story.id)).all()
    provider = ResearchSearchProvider()
    draft = provider.research([c.statement for c in claims])

    existing_evidence = db.scalars(
        select(Evidence).join(Claim, Evidence.claim_id == Claim.id).where(Claim.story_id == story.id)
    ).all()
    existing_urls = {(e.claim_id, e.url) for e in existing_evidence}

    for claim, claim_research in zip(claims, draft.claims):
        if claim_research.verification_status in ("SUPPORTED", "CONTRADICTED", "NOT_VERIFIABLE"):
            claim.verification_status = claim_research.verification_status
        claim.verification_notes = claim_research.verification_notes
        for ev in claim_research.evidence:
            if (claim.id, ev.url) in existing_urls:
                continue
            db.add(
                Evidence(
                    claim_id=claim.id,
                    url=ev.url,
                    publisher=ev.publisher,
                    published_at=ev.published_at,
                    retrieved_at=utcnow(),
                    excerpt_or_paraphrase=ev.excerpt_or_paraphrase,
                    kind=ev.kind,
                    confidence=ev.confidence,
                    demo=get_settings().demo_mode or provider.demo,
                )
            )
        existing_urls.add((claim.id, ev.url))

    score_story(db, story)
    assert_transition("story", story.status, "REVIEW_REQUIRED")
    story.status = "REVIEW_REQUIRED"
    db.flush()
    return story
