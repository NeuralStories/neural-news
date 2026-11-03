"""Manejadores de trabajos del worker. Cada handler es idempotente.

Las operaciones de pago nunca se reintentan a ciegas tras un timeout: si el
presupuesto lo bloquea o ya se registró consumo, el trabajo falla de forma
definitiva con un mensaje claro.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Job, Source, Story
from .queue import mark_done, mark_failed, mark_retryable
from .services import budget as budget_service
from .services import av_jobs
from .services import batches as batch_service
from .services import research as research_service
from .services import scripts as script_service
from .services.sources import SourceNotAnalyzable, extract_stories_from_source, run_fetch

PROCESS_SOURCE = "process_source"
ANALYZE_VIDEO = "analyze_video"
RESEARCH_STORY = "research_story"
DRAFT_SCRIPT = "draft_script"
EXPORT_BATCH = "export_batch"
AV_GENERATE = "av_generate"
AV_RENDER = "av_render"

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
        mark_failed(db, job, str(exc))
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


@handler(AV_GENERATE)
def handle_av_generate(db: Session, job: Job) -> str:
    """Generación audiovisual con proveedor simulado (coste 0, sin servicios de pago).

    Idempotente: el proveedor deduplica por huella del pedido; los reintentos y
    la recuperación tras interrupción nunca generan artefactos repetidos.
    """
    from .providers.av_generation import AvGenerationRequest, SimulatedAvProvider

    request = AvGenerationRequest(**job.payload["request"])
    result = SimulatedAvProvider().generate(request)
    budget_service.record_usage(
        db,
        provider=result.provider,
        job_id=job.id,
        event="call",
        cost_estimate=0.0,
    )
    return (
        f"{result.kind} simulado generado: {result.artifact_relpath} "
        f"(sha256 {result.sha256[:12]})"
    )


@handler(AV_RENDER)
def handle_av_render(db: Session, job: Job) -> str:
    """Composición local del vídeo del plan con FFmpeg (Fase 6, coste 0).

    Idempotente por huella del plan: reintentos o repeticiones reutilizan el
    fichero ya compuesto. Los errores de plan son fallos definitivos (sin
    reintentos) porque no se corrigen solos.
    """
    from .services import av_render as av_render_service

    plan = job.payload["plan"]
    max_cost_eur = job.payload.get("max_cost_eur")
    batch_id = job.payload.get("batch_id")
    estimated = float(job.payload.get("estimated_cost_eur") or 0.0)
    try:
        render = av_render_service.render_plan_video(db, plan, job_id=job.id, max_cost_eur=max_cost_eur)
    except av_render_service.PlanInvalid as exc:
        mark_failed(db, job, str(exc))
        av_jobs.release_batch_budget(db, batch_id, estimated)
        return "plan no válido: no se compuso nada"
    except budget_service.BudgetExceeded as exc:
        # Se agotó el presupuesto: fallo definitivo, se libera la reserva.
        mark_failed(db, job, str(exc))
        av_jobs.release_batch_budget(db, batch_id, estimated)
        budget_service.record_usage(db, provider="ffmpeg_render", job_id=job.id, event="blocked")
        return "bloqueado por presupuesto"
    budget_service.record_usage(
        db,
        provider="ffmpeg_render",
        job_id=job.id,
        event="call",
        cost_estimate=estimated,
    )
    # La reserva se liquida con el coste real (0 € en el proveedor simulado).
    av_jobs.settle_batch_budget(db, batch_id, estimated, estimated)
    return (
        f"Vídeo compuesto: {render.storage_path} "
        f"({render.output_format}, {render.duration_s:.1f} s, sha256 {render.sha256[:12]})"
    )


def run_job(db: Session, job: Job) -> None:
    fn = HANDLERS.get(job.type)
    if fn is None:
        mark_failed(db, job, f"Tipo de trabajo desconocido: {job.type}")
        return
    try:
        summary = fn(db, job)
        if job.status not in ("DONE", "FAILED"):
            job.progress = summary
            mark_done(db, job)
    except budget_service.BudgetExceeded as exc:
        mark_failed(db, job, str(exc))
    except Exception as exc:  # noqa: BLE001 — el worker registra y decide reintento
        mark_retryable(db, job, f"{exc.__class__.__name__}: {exc}")
