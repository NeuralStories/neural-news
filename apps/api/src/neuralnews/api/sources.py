"""Fuentes: alta con idempotencia, consulta, reprocesado y transcripciones aportadas."""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from ..config import get_settings
from ..db import get_db
from ..models import Claim, Job, Source, SourceContent, Story, StorySource
from ..queue import enqueue
from ..schemas import ProcessRequest, SourceCreate, SourceDetailOut, SourceOut
from ..providers.safety import FetchBlocked  # noqa: F401  (re-exportado para los routers)
from ..security import get_current_actor, require_paid_services
from ..services.sources import DuplicateSource, create_source
from ..states import CONTENT_TYPE_LABELS, SOURCE_LABELS, STORY_LABELS
from ..worker_tasks import (  # noqa: F401  (ANALYZE_VIDEO re-exportado)
    ANALYZE_VIDEO,
    PROCESS_SOURCE,
    TRANSCRIBE_SOURCE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


def source_to_out(db, source: Source) -> SourceOut:
    return SourceOut(
        id=source.id,
        provider=source.provider,
        external_id=source.external_id,
        canonical_url=source.canonical_url,
        title=source.title,
        author=source.author,
        published_at=source.published_at,
        imported_at=source.imported_at,
        language=source.language,
        status=source.status,
        status_label=SOURCE_LABELS.get(source.status, source.status),
        demo=source.demo,
        metadata=source.metadata_json or {},
    )


@router.post("", response_model=dict)
def add_source(
    payload: SourceCreate,
    request: Request,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Registra una fuente. Con Idempotency-Key, repetir la llamada no duplica nada."""
    idempotency_key = request.headers.get("Idempotency-Key")
    try:
        source = create_source(
            db,
            url=payload.url,
            text=payload.text,
            title=payload.title,
            author=payload.author,
            published_at=payload.published_at,
            transcript=payload.transcript,
        )
    except DuplicateSource as exc:
        job = None
        if idempotency_key:
            job, _ = enqueue(
                db, PROCESS_SOURCE, {"source_id": exc.source.id},
                dedupe_key=f"process:{exc.source.id}:{idempotency_key}",
            )
        db.flush()
        return {
            "source": source_to_out(db, exc.source),
            "job_id": job.id if job else None,
            "created": False,
            "message": str(exc),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job, created = enqueue(
        db,
        PROCESS_SOURCE,
        {"source_id": source.id},
        dedupe_key=(
            f"process:{source.id}:{idempotency_key}" if idempotency_key else f"process:{source.id}"
        ),
    )
    db.flush()
    return {
        "source": source_to_out(db, source),
        "job_id": job.id,
        "created": True,
        "message": None,
    }


@router.get("")
def list_sources(
    db=Depends(get_db),
    actor=Depends(get_current_actor),
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = select(Source).order_by(Source.imported_at.desc())
    if status:
        query = query.where(Source.status == status)
    if provider:
        query = query.where(Source.provider == provider)
    total = len(db.scalars(query).all())
    rows = db.scalars(query.limit(min(limit, 200)).offset(offset)).all()
    return {
        "total": total,
        "items": [source_to_out(db, s).model_dump(mode="json") for s in rows],
    }


@router.get("/{source_id}")
def get_source(source_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    out = SourceDetailOut(
        **source_to_out(db, source).model_dump(),
        contents=[],
        stories=[],
    )
    contents = db.scalars(
        select(SourceContent).where(SourceContent.source_id == source.id)
    ).all()
    for content in contents:
        out.contents.append(
            {
                "id": content.id,
                "content_type": content.content_type,
                "content_type_label": CONTENT_TYPE_LABELS.get(content.content_type, content.content_type),
                "is_verbatim": content.is_verbatim,
                "provider": content.provider,
                "model": content.model,
                "coverage": content.coverage,
                "confidence": content.confidence,
                "extracted_at": content.extracted_at.isoformat(),
                "char_count": len(content.text),
                "segment_count": len(content.segments),
            }
        )
    links = db.scalars(select(StorySource).where(StorySource.source_id == source.id)).all()
    for link in links:
        story = db.get(Story, link.story_id)
        out.stories.append(
            {
                "id": story.id,
                "title": story.title,
                "status": story.status,
                "status_label": STORY_LABELS.get(story.status, story.status),
            }
        )
    return out.model_dump(mode="json")


@router.get("/{source_id}/transcript")
def get_transcript(source_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Devuelve la transcripción vigente de la fuente (texto + segmentos)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    for content in db.scalars(
        select(SourceContent)
        .where(SourceContent.source_id == source.id)
        .order_by(SourceContent.id.desc())
    ).all():
        if content.content_type in ("TRANSCRIPT", "ARTICLE_TEXT", "MANUAL_TEXT"):
            return {
                "found": True,
                "content_type": content.content_type,
                "content_type_label": CONTENT_TYPE_LABELS.get(content.content_type, content.content_type),
                "is_verbatim": content.is_verbatim,
                "provider": content.provider,
                "text": content.text,
                "segments": [
                    {
                        "start_ms": seg.start_ms,
                        "end_ms": seg.end_ms,
                        "text": seg.text,
                        "sequence": seg.sequence,
                    }
                    for seg in content.segments
                ],
            }
    return {"found": False, "message": "Esta fuente todavía no tiene transcripción"}


@router.post("/{source_id}/transcribe", status_code=202)
def transcribe_source(
    source_id: int,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Encola la búsqueda de la transcripción de la fuente.

    **No se hace aquí.** Buscar la transcripción puede tardar minutos (yt-dlp,
    feed RSS del pódcast, extracción del artículo) y no debe bloquear el hilo
    de la petición (gate G3). La respuesta es `202` con el identificador del
    trabajo; el resultado se consulta en `/sources/{id}/transcript` cuando el
    trabajo termina.

    - YouTube → subtítulos públicos; pódcast → podcast:transcript del feed;
      artículo web → texto del artículo; manual → el texto aportado.
    Nada se inventa: si no hay transcripción accesible, el trabajo termina con
    el motivo y ese motivo llega a la interfaz.
    """
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")

    job, created = enqueue(
        db,
        TRANSCRIBE_SOURCE,
        {"source_id": source.id, "actor_id": actor["actor_id"]},
        dedupe_key=f"transcribe:{source.id}",
    )
    db.flush()
    return {
        "job_id": job.id,
        "created": created,
        "status": job.status,
        "message": (
            "Transcripción en cola; se avisará cuando termine."
            if created
            else "Ya había una transcripción en marcha; se reutiliza."
        ),
    }


@router.post("/{source_id}/process")
def process_source(
    source_id: int,
    payload: ProcessRequest,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Reprocesa la fuente. Es idempotente: si ya hay un trabajo vivo, se reutiliza."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    job, created = enqueue(
        db,
        PROCESS_SOURCE,
        {"source_id": source.id},
        dedupe_key=f"process:{source.id}",
    )
    db.flush()
    return {"job_id": job.id, "created": created}


@router.post("/{source_id}/analyze")
def analyze_video(
    source_id: int,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Pide el análisis del vídeo de la fuente (adaptador Gemini; requiere clave, salvo demo)."""
    require_paid_services()
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    if source.provider != "youtube":
        raise HTTPException(
            status_code=400,
            detail="El análisis de vídeo sólo aplica a fuentes de YouTube; para otros tipos, "
            "aporta el texto o una transcripción",
        )
    job, created = enqueue(
        db,
        ANALYZE_VIDEO,
        {"source_id": source.id},
        dedupe_key=f"analyze:{source.id}",
    )
    db.flush()
    return {"job_id": job.id, "created": created}


@router.post("/{source_id}/transcript")
def add_transcript(
    source_id: int,
    payload: SourceCreate,
    db=Depends(get_db),
    actor=Depends(get_current_actor),
) -> dict:
    """Añade una transcripción real aportada por el usuario (queda marcada como literal)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")
    if not payload.transcript or not payload.transcript.strip():
        raise HTTPException(status_code=400, detail="Escribe o pega la transcripción")
    from ..providers.base import ContentDraft
    

    _store_content(
        db,
        source,
        ContentDraft(
            content_type="TRANSCRIPT",
            text=payload.transcript.strip(),
            is_verbatim=True,
            provider="manual",
            coverage=1.0,
            confidence="high",
        ),
    )
    if source.status in ("METADATA_ONLY", "PARTIAL", "FAILED"):
        source.status = "READY"
    db.flush()
    return {"ok": True, "message": "Transcripción guardada como texto literal aportado"}
