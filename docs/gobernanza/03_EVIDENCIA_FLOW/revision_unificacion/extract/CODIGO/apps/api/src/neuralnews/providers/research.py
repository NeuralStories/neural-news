"""Proveedor de investigación: convierte afirmaciones en búsquedas y evidencia.

- demo: evidencia determinista con URLs del dominio .invalid (reservado), claramente marcada.
- real: adaptador de búsqueda web (Brave Search API compatible); implementado, NO validado.
  Nunca fabrica citas: si la búsqueda no aporta resultados, la afirmación queda sin verificar.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import httpx

from ..config import get_settings
from .base import ClaimResearchDraft, EvidenceDraft, ResearchDraft

PROMPT_RESEARCH = (
    "Eres un verificador de datos. Dada una afirmación entre <afirmacion> y </afirmacion>, "
    "enumera las consultas de búsqueda que harías. No es necesario aquí: este módulo sólo "
    "compone consultas; las búsquedas y sus resultados provienen del proveedor real."
)


def _stable_slug(text: str, prefix: str) -> str:
    digest = hashlib.sha256(text.encode()).hexdigest()[:10]
    return f"{prefix}-{digest}"


class ResearchSearchProvider:
    def __init__(self, demo: bool | None = None) -> None:
        settings = get_settings()
        self.demo = settings.demo_mode if demo is None else demo
        self.has_key = bool(settings.search_api_key)

    def research(self, claims: list[str]) -> ResearchDraft:
        if self.demo:
            return self._research_demo(claims)
        results: list[ClaimResearchDraft] = []
        for claim in claims:
            hits = self._search_brave(claim)
            evidence = [
                EvidenceDraft(
                    url=hit["url"],
                    publisher=hit.get("publisher"),
                    excerpt_or_paraphrase=(hit.get("description") or "")[:500] or None,
                    kind="REFERENCE",
                    confidence="medium",
                )
                for hit in hits[:5]
            ]
            # Sólo la evidencia realmente recuperada; el estado humano/modelo decide después.
            status = "UNVERIFIED"
            results.append(
                ClaimResearchDraft(
                    claim=claim,
                    verification_status=status,
                    verification_notes=(
                        "Resultados de búsqueda recuperados; requieren revisión humana antes de "
                        "considerarse verificados"
                        if evidence
                        else "La búsqueda no ha devuelto resultados; sin evidencia"
                    ),
                    evidence=evidence,
                )
            )
        return ResearchDraft(claims=results)

    def _research_demo(self, claims: list[str]) -> ResearchDraft:
        results: list[ClaimResearchDraft] = []
        for claim in claims:
            lowered = claim.lower()
            if "opinión" in lowered or "predicci" in lowered or "intuici" in lowered:
                results.append(
                    ClaimResearchDraft(
                        claim=claim,
                        verification_status="NOT_VERIFIABLE",
                        verification_notes="Es una opinión o predicción personal; no hay hecho verificable",
                        evidence=[],
                    )
                )
                continue
            if "12%" in claim or "radar" in lowered:
                results.append(
                    ClaimResearchDraft(
                        claim=claim,
                        verification_status="SUPPORTED",
                        verification_notes=(
                            "DEMO: la evidencia adjunta es ficticia y procede de un fixture local; "
                            "sustitúyela por búsqueda real antes de publicar"
                        ),
                        evidence=[
                            EvidenceDraft(
                                url=_stable_slug_url(claim, "comunicado-cortexa"),
                                publisher="Blog de Cortexa Labs (fixture DEMO)",
                                published_at=datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc),
                                excerpt_or_paraphrase=(
                                    "DEMO — El comunicado de la empresa describe Radar y su mejora del 12% "
                                    "en benchmarks internos (dato ficticio de prueba)"
                                ),
                                kind="PRIMARY",
                                confidence="medium",
                            ),
                            EvidenceDraft(
                                url=_stable_slug_url(claim, "cobertura-ficha-tecnica"),
                                publisher="Medio de ejemplo (fixture DEMO)",
                                published_at=datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc),
                                excerpt_or_paraphrase=(
                                    "DEMO — Cobertura independiente del anuncio; sin confirmación externa "
                                    "de los benchmarks (dato ficticio de prueba)"
                                ),
                                kind="CORROBORATION",
                                confidence="low",
                            ),
                        ],
                    )
                )
                continue
            if "40 millones" in claim or "vireo" in lowered:
                results.append(
                    ClaimResearchDraft(
                        claim=claim,
                        verification_status="UNVERIFIED",
                        verification_notes=(
                            "DEMO: no se ha encontrado evidencia en esta simulación; la afirmación "
                            "queda sin verificar en lugar de darse por confirmada"
                        ),
                        evidence=[],
                    )
                )
                continue
            results.append(
                ClaimResearchDraft(
                    claim=claim,
                    verification_status="UNVERIFIED",
                    verification_notes="DEMO: sin evidencia disponible en este modo simulado",
                    evidence=[],
                )
            )
        return ResearchDraft(claims=results)

    def _search_brave(self, query: str) -> list[dict]:
        """Búsqueda real con Brave Search API. Requiere NEURAL_SEARCH_API_KEY. No validado."""
        settings = get_settings()
        if not self.has_key:
            raise RuntimeError(
                "No hay clave del buscador configurada; configura NEURAL_SEARCH_API_KEY o usa el modo demo"
            )
        if not settings.paid_services_enabled:
            raise RuntimeError("Los servicios de pago están desactivados en la configuración")
        response = httpx.get(
            settings.search_base_url,
            params={"q": query, "count": 5},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": settings.search_api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("web", {}).get("results", [])


def _stable_slug_url(claim: str, prefix: str) -> str:
    slug = _stable_slug(claim, prefix)
    return f"https://demo.neuralnews.invalid/evidencia/{slug}"
