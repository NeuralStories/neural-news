"""Fuentes: alta con idempotencia, consulta, reprocesado y transcripciones aportadas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from ..config import get_settings
from ..db import get_db
from ..models import Claim, Job, Source, SourceContent, Story, StorySource
from ..queue import enqueue
from ..schemas import ProcessRequest, SourceCreate, SourceDetailOut, SourceOut
from ..security import get_current_actor
from ..services.sources import DuplicateSource, create_source
from ..states import CONTENT_TYPE_LABELS, SOURCE_LABELS, STORY_LABELS
from ..worker_tasks import ANALYZE_VIDEO, PROCESS_SOURCE  # noqa: F401  (ANALYZE_VIDEO usado)

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


@router.post("/{source_id}/transcribe")
def transcribe_source(source_id: int, db=Depends(get_db), actor=Depends(get_current_actor)) -> dict:
    """Busca o crea la transcripción de la fuente según su tipo:
    YouTube → subtítulos públicos; pódcast → podcast:transcript del feed;
    artículo web → texto del artículo; manual → el texto aportado.
    Nada se inventa: si no hay transcripción accesible, se responde el motivo."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Esa fuente no existe")

    def out(found: bool, created: bool, draft=None, message: str | None = None) -> dict:
        body: dict = {"found": found, "created": created}
        if message:
            body["message"] = message
        if draft is not None:
            body["transcript"] = {
                "text": draft.text,
                "provider": draft.provider,
                "segments": len(draft.segments),
            }
        return body

    existing = [
        c for c in db.scalars(
            select(SourceContent)
            .where(SourceContent.source_id == source.id)
            .order_by(SourceContent.id.desc())
        ).all()
        if c.content_type == "TRANSCRIPT"
    ]
    if existing:
        return out(True, False, existing[0], "Ya existe una transcripción; se devuelve tal cual")

    settings = get_settings()
    from ..services.sources import _store_content
    try:
        if source.provider == "youtube":
            if source.demo:
                demo_t = next((c for c in db.scalars(
                    select(SourceContent)
                    .where(SourceContent.source_id == source.id,
                           SourceContent.content_type == "TRANSCRIPT")
                ).all()), None)
                if demo_t is None:
                    return out(False, False, None,
                               "Fuente de demostración sin transcripción simulada almacenada")
                return out(True, False, type("D", (), {
                    "text": demo_t.text, "provider": demo_t.provider, "segments": [],
                })(), "Fuente de demostración: la transcripción simulada ya está almacenada")
            from ..providers.transcript import fetch_youtube_transcript
            video_id = source.external_id or ""
            draft = fetch_youtube_transcript(video_id)
            if draft is None:
                return out(False, False, None,
                           "El vídeo no tiene una pista de subtítulos pública accesible "
                           "(prueba con otro idioma o aporta la transcripción)")
        elif source.provider == "spotify":
            feed_url = (source.metadata or {}).get("feed_url")
            if not feed_url:
                return out(False, False, None,
                           "Spotify no expone la transcripción sin el feed RSS del programa: "
                           "añade feed_url a los metadatos de la fuente o pega la transcripción")
            from ..providers.transcript import fetch_podcast_transcript_from_feed
            draft = fetch_podcast_transcript_from_feed(
                feed_url, source.external_id, source.title)
            if draft is None:
                return out(False, False, None,
                           "El feed no incluye podcast:transcript para este episodio")
        elif source.provider in ("web_rss", "manual") and source.canonical_url:
            from ..providers.web_rss import fetch_web
            from ..services.sources import _store_content
            result = fetch_web(source.canonical_url)
            if result.status in ("READY", "PARTIAL") and result.contents:
                for draft in result.contents:
                    _store_content(db, source, draft)
                return out(True, True, result.contents[0],
                           "Texto del artículo extraído de nuevo desde la URL canónica")
            return out(False, False, None,
                       f"No se ha podido extraer el texto desde la URL: {result.error or result.status}")
        else:
            return out(False, False, None,
                       "Fuente manual: el texto aportado ES la transcripción; "
                       "guárdalo con «Guardar transcripción»")
    except FetchBlocked as exc:
        return out(False, False, None, f"Bloqueado por seguridad: {exc}")
    except Exception as exc:  # red u otro fallo real: se reporta, no se inventa
        return out(False, False, None, f"No se ha podido obtener la transcripción: {exc}")

    _store_content(db, source, draft)
    db.flush()
    return out(True, True, draft, "Transcripción creada y almacenada como texto literal")


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
