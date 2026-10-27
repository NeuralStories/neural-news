"""Conector manual: texto pegado o archivo de texto subido por el usuario. Totalmente real."""
from __future__ import annotations

import re
from datetime import datetime

from ..models import Source
from .base import ContentDraft, FetchResult, SegmentDraft

# Tipos MIME de texto aceptados para carga de archivos
ACCEPTED_TEXT_MIME = {
    "text/plain",
    "text/markdown",
    "application/json",
    "text/html",
    "application/pdf",  # se rechaza más abajo con mensaje claro en MVP
}
MAX_TEXT_CHARS = 2_000_000


def split_paragraphs(text: str) -> list[SegmentDraft]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return [SegmentDraft(text=b, sequence=i) for i, b in enumerate(blocks)]


def normalize_input(url: str | None, text: str | None, filename: str | None = None) -> tuple[str | None, str]:
    """Valida la entrada manual y devuelve (url_normalizada|None, texto)."""
    if not text or not text.strip():
        raise ValueError("No has aportado ningún texto; pega el contenido o sube un archivo de texto")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("El texto supera el límite de 2 millones de caracteres")
    clean_url = url.strip() if url else None
    if filename and filename.lower().endswith(".pdf"):
        raise ValueError("De momento no se leen PDF: guarda el texto como .txt o pégalo directamente")
    return clean_url, text.strip()


def fetch_manual(source: Source, text: str, url: str | None = None) -> FetchResult:
    """Construye el resultado para texto aportado por el usuario (verbatim, cobertura 1.0)."""
    return FetchResult(
        provider="manual",
        external_id=None,
        canonical_url=url,
        title=source.title or "Texto aportado",
        author=source.author,
        published_at=source.published_at or datetime.now().astimezone(),
        language=source.language or "es",
        status="READY",
        contents=[
            ContentDraft(
                content_type="MANUAL_TEXT",
                text=text,
                is_verbatim=True,
                provider="manual",
                coverage=1.0,
                confidence="high",
                segments=split_paragraphs(text),
            )
        ],
        metadata={"demo": bool(source.demo)},
    )
