"""Manejadores de trabajos del worker. Cada handler es idempotente.

Las operaciones de pago nunca se reintentan a ciegas tras un timeout: si el
presupuesto lo bloquea o ya se registró consumo, el trabajo falla de forma
definitiva con un mensaje claro.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .errors import ConectorFallido, MaterialFaltante, safe_error
from .models import Job, Source, Story
from .queue import mark_done, mark_failed, mark_retryable
from .services import budget as budget_service
from .services import batches as batch_service
from .services import research as research_service
from .services import scripts as script_service
from .services.sources import SourceNotAnalyzable, extract_stories_from_source, run_fetch

logger = logging.getLogger(__name__)

PROCESS_SOURCE = "process_source"
ANALYZE_VIDEO = "analyze_video"
RESEARCH_STORY = "research_story"
DRAFT_SCRIPT = "draft_script"
EXPORT_BATCH = "export_batch"
# Tipos que existían solo dentro del hilo de petición (NN-110). Ahora el
# trabajo pesado lo hace el worker y la API responde de inmediato.
TRANSCRIBE_SOURCE = "transcribe_source"
BUILD_MONTAGE = "build_montage"
PROBE_MEDIA = "probe_media"
EXTRACT_WEB = "extract_web"

HANDLERS = {}


def handler(job_type: str):
    def register(fn):
        HANDLERS[job_type] = fn
        return fn

    return register


@handler(PROCESS_SOURCE)
def handle_process_source(db: Session, job: Job) -> str:
    source_id = job.payload["source_id"]
    source = db.get(Source, source_id)
    if source is None:
        raise RuntimeError("La fuente ya no existe")
    run_fetch(db, source)
    try:
        stories = extract_stories_from_source(db, source)
    except SourceNotAnalyzable as exc:
        # Resultado esperado (fuente sin transcripción), no un fallo: no se reintenta.
        job.progress = str(exc)
        return str(exc)
    budget_service.record_usage(
        db,
        provider="demo_extraction" if source.demo else "extraction",
        model="demo" if source.demo else None,
        job_id=job.id,
        event="call",
        cost_estimate=0.0,
    )
    return f"Fuente procesada; {len(stories)} candidato(s) de noticias"


@handler(TRANSCRIBE_SOURCE)
def handle_transcribe_source(db: Session, job: Job) -> str:
    """Busca y guarda la transcripción de una fuente (YouTube, pódcast o web).

    Idempotente: si la transcripción ya está guardada, no se vuelve a
    descargar. Si no hay transcripción accesible, **no es un fallo**: el
    trabajo termina con el motivo exacto en `progress`.
    """
    source_id = job.payload["source_id"]
    source = db.get(Source, source_id)
    if source is None:
        raise RuntimeError("La fuente ya no existe")
    from .services import transcription as transcription_service

    outcome = transcription_service.transcribe_source_content(db, source)
    if not outcome.found:
        job.progress = outcome.message
        return outcome.message
    return outcome.message


@handler(EXTRACT_WEB)
def handle_extract_web(db: Session, job: Job) -> str:
    """Extrae el texto del artículo web de la URL canónica de la fuente."""
    source_id = job.payload["source_id"]
    source = db.get(Source, source_id)
    if source is None:
        raise RuntimeError("La fuente ya no existe")
    from .services import transcription as transcription_service

    outcome = transcription_service.extract_web_content(db, source)
    job.progress = outcome.message
    return outcome.message


@handler(BUILD_MONTAGE)
def handle_build_montage(db: Session, job: Job) -> str:
    """Construye la animática 9:16 real con FFmpeg.

    Idempotente: el montage se reconstruye sobre los mismos materiales y se
    persiste en el paso «resultado»; volver a lanzarlo no destruye nada.
    """
    project_id = job.payload["project_id"]
    from .models import ProductionProject
    from .services import montage as montage_service

    project = db.get(ProductionProject, project_id)
    if project is None:
        raise RuntimeError("El proyecto ya no existe")
    result = montage_service.build_animatica(db, project)
    if not result.get("ok"):
        # Falta material (o no hay FFmpeg): reintentar no cambiaría el resultado.
        raise MaterialFaltante(result.get("error") or "No se ha podido construir la animática")
    montage_service.persist_animatica(db, project, result, job.payload.get("actor_id"))
    db.flush()
    return f"Animática construida: {result.get('duration_s', '?')} s ({result.get('label', '')})"


@handler(PROBE_MEDIA)
def handle_probe_media(db: Session, job: Job) -> str:
    """Sondea un medio ya subido con ffprobe y guarda sus metadatos.

    El sondeo se hace aquí, no en la petición: ffprobe puede tardar y bloquear.
    """
    media_id = job.payload["media_id"]
    from .models import MediaAsset
    from .services import media_library

    asset = db.get(MediaAsset, media_id)
    if asset is None:
        raise RuntimeError("El medio ya no existe")
    media_library.probe_media_asset(db, asset)
    db.flush()
    return f"Medio sondeado: {asset.probe_status}"


@handler(ANALYZE_VIDEO)
def handle_analyze_video(db: Session, job: Job) -> str:
    """Análisis de vídeo real (Gemini) con control de presupuesto.

    En modo demo el contenido ya llegó con la fuente, así que este trabajo no
    necesita llamar a nada de pago.
    """
    from .config import get_settings
    from .providers.video_analysis import call_gemini_video_analysis
    from .services.sources import _store_content

    source_id = job.payload["source_id"]
    source = db.get(Source, source_id)
    if source is None:
        raise RuntimeError("La fuente ya no existe")
    settings = get_settings()
    if settings.demo_mode:
        return "Modo demo: el análisis simulado ya está incluido en la fuente"
    try:
        budget_service.assert_paid_call_allowed(db, "gemini", estimated_cost_eur=0.01)
    except budget_service.BudgetExceeded as exc:
        budget_service.record_usage(db, provider="gemini", job_id=job.id, event="blocked")
        mark_failed(db, job, str(exc), kind="budget")
        return "bloqueado por presupuesto"

    result = call_gemini_video_analysis(source.canonical_url or "")
    for draft in result.contents:
        _store_content(db, source, draft)
    source.status = "READY"
    budget_service.record_usage(
        db,
        provider="gemini",
        model=settings.llm_model,
        job_id=job.id,
        event="call",
        cost_estimate=0.01,
    )
    return "Análisis del vídeo guardado (no es transcripción literal)"


@handler(RESEARCH_STORY)
def handle_research_story(db: Session, job: Job) -> str:
    story_id = job.payload["story_id"]
    story = db.get(Story, story_id)
    if story is None:
        raise RuntimeError("La noticia ya no existe")
    from .providers.research import ResearchSearchProvider

    provider = ResearchSearchProvider()
    if not provider.demo:
        try:
            budget_service.assert_paid_call_allowed(db, "search", estimated_cost_eur=0.005)
        except budget_service.BudgetExceeded as exc:
            budget_service.record_usage(db, provider="search", job_id=job.id, event="blocked")
            mark_failed(db, job, str(exc))
            return "bloqueado por presupuesto"
    research_service.research_story(db, story)
    budget_service.record_usage(
        db,
        provider="demo_search" if provider.demo else "search",
        model=None,
        job_id=job.id,
        event="call",
        cost_estimate=0.0,
    )
    return "Investigación completada; la noticia queda pendiente de revisión"


@handler(DRAFT_SCRIPT)
def handle_draft_script(db: Session, job: Job) -> str:
    story_id = job.payload["story_id"]
    story = db.get(Story, story_id)
    if story is None:
        raise RuntimeError("La noticia ya no existe")
    script_service.create_draft_version(db, story)
    budget_service.record_usage(
        db,
        provider="demo_llm" if get_settings().demo_mode else "editorial_llm",
        model="demo" if get_settings().demo_mode else get_settings().llm_model,
        job_id=job.id,
        event="call",
        cost_estimate=0.0,
    )
    return "Borrador de guion creado"


@handler(EXPORT_BATCH)
def handle_export_batch(db: Session, job: Job) -> str:
    batch_id = job.payload["batch_id"]
    batch = db.get(batch_service.Batch, batch_id)
    if batch is None:
        raise RuntimeError("El lote ya no existe")
    package = batch_service.export_batch(db, batch)
    return f"Paquete exportado (v{package.package_version}, sha256 {package.sha256[:12]})"


def run_job(db: Session, job: Job) -> None:
    fn = HANDLERS.get(job.type)
    if fn is None:
        mark_failed(
            db, job, f"Tipo de trabajo desconocido: {job.type}", kind="unknown"
        )
        return
    try:
        summary = fn(db, job)
        if job.status not in ("DONE", "FAILED"):
            job.progress = summary
            mark_done(db, job)
    except budget_service.BudgetExceeded as exc:
        mark_failed(db, job, str(exc), kind="budget")
    except MaterialFaltante as exc:
        # Reintentar sin material daría el mismo resultado: no se reintenta.
        mark_failed(db, job, safe_error(exc), kind="material")
    except ConectorFallido as exc:
        # Fallo de proveedor: suele ser transitorio, se reintenta.
        mark_retryable(db, job, safe_error(exc), kind="connector")
    except Exception as exc:  # noqa: BLE001 — el worker registra y decide reintento
        # `job.error` se devuelve al cliente en GET /api/v1/jobs: se guarda un
        # resumen sin rutas ni secretos, y el detalle completo queda en el log.
        logger.exception("Fallo el trabajo %s (%s)", job.id, job.type)
        mark_retryable(db, job, safe_error(exc), kind="unknown")
