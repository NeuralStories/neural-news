"""Productor del contrato `production_handoff.v1`.

Emite el snapshot de una noticia con guion aprobado (o de un lote completo de
noticias aprobadas) para que NeuralStories Studio lo consuma. No inventa datos:
si falta un campo obligatorio (p. ej. `summary`) lanza `HandoffError` y no emite
nada; el contenido se corrige en editorial. La aprobación se comprueba en la
base de datos en el momento de emitir; nunca se confía en un campo del propio
JSON (ver RIESGOS.md R03). Cada emisión queda registrada en `storage/handoffs/`
y en `AuditLog`.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import (
    AuditLog,
    Batch,
    BatchItem,
    ScriptVersion,
    Source,
    Story,
    StorySource,
    utcnow,
)
from ..providers.image_prompt import build_storyboard
from .editorial_status import build_story_status
from .scripts import active_approval, latest_version

SCHEMA_VERSION = "production_handoff.v1"
HANDOFF_LANGUAGE = "es-ES"

# Identificadores lógicos del canon audiovisual declarado en
# flow-recovery/source/constants.ts (NeuralDotAI, fondos CRT, voz Algenib).
# Son referencias de perfil, no recursos licenciados (ver RIESGOS.md R05/R07).
CANON_PROFILE_BASE = {
    "profile_id": "neuralnews-canon-v1",
    "character_id": "neuraldotai",
    "voice_id": "algenib",
}


class HandoffError(Exception):
    """No se puede emitir el traspaso; el mensaje está pensado para el usuario."""


def default_style_profile(output_format: str = "9:16") -> dict:
    """Perfil canon según el formato de salida (presets CRT del Studio)."""
    return {
        **CANON_PROFILE_BASE,
        "studio_id": "crt_original_vertical" if output_format == "9:16" else "crt_original_wide",
    }


def _iso(value: datetime) -> str:
    return value.isoformat()


def story_handoff_problems(db: Session, story: Story) -> list[str]:
    """Motivos por los que la noticia no puede traspasarse (lista vacía = lista para emitir).

    Se apoya en el estado editorial compartido (`editorial_status`), de modo que
    la web, el lote y este traspaso cuentan la misma historia.
    """
    problems: list[str] = []
    version = latest_version(db, story.id)
    if version is None:
        return ["La noticia no tiene ningún guion todavía."]
    if story.status != "APPROVED":
        problems.append("La noticia no está en estado «aprobada» en editorial.")
    approval = active_approval(db, story.id)
    if approval is None:
        problems.append("El guion no tiene una aprobación vigente.")
    elif approval.script_version_id != version.id:
        problems.append(
            f"La aprobación vigente corresponde a la versión {approval.script_version_id} "
            f"y la última es la {version.version}: hay que volver a aprobar el guion actual."
        )
    elif approval.script_version.content_hash != version.content_hash:
        problems.append("El hash del guion aprobado no coincide con el guion guardado.")
    if version.language != HANDOFF_LANGUAGE:
        problems.append(
            f"El guion está en «{version.language}»; el contrato v1 sólo transporta «{HANDOFF_LANGUAGE}»."
        )
    links = db.scalars(select(StorySource).where(StorySource.story_id == story.id)).all()
    if not links:
        problems.append("La noticia no tiene ninguna fuente registrada.")

    # Bloqueos de producción (resumen ausente, afirmaciones sin evidencia,
    # contradicciones). Mismos motivos que expone la API.
    status = build_story_status(
        db,
        story,
        versions=[version],
        approved_version_id=approval.script_version_id if approval else None,
        pending_flag=False,
    )
    for blocker in status.production_blockers:
        if blocker not in problems:
            problems.append(blocker)
    return problems


def build_story_payload(db: Session, story: Story) -> dict:
    """Construye el objeto `story` del contrato. Lanza `HandoffError` si falta algo."""
    problems = story_handoff_problems(db, story)
    if problems:
        raise HandoffError(
            f"La noticia «{story.title}» (id {story.id}) no puede traspasarse:\n- "
            + "\n- ".join(problems)
        )
    version = latest_version(db, story.id)
    approval = active_approval(db, story.id)

    sources_payload: list[dict] = []
    for link in db.scalars(select(StorySource).where(StorySource.story_id == story.id)).all():
        source = db.get(Source, link.source_id)
        has_identifier = any(
            (value or "").strip() for value in (source.canonical_url, source.external_id, source.title)
        )
        if not has_identifier:
            raise HandoffError(
                f"La noticia «{story.title}» tiene una fuente (id {source.id}) sin URL, "
                "identificador externo ni título: no se puede traspasar sin inventar datos."
            )
        sources_payload.append(
            {
                "title": source.title,
                "url": source.canonical_url,
                "accessed_at": _iso(source.imported_at),
                "provider": source.provider,
                "external_id": source.external_id,
                "relevance": link.relevance,
                "published_at": _iso(source.published_at) if source.published_at else None,
            }
        )

    storyboard = build_storyboard(story, version, approval)
    return {
        "story_id": str(story.id),
        "revision": version.version,
        "title": story.title,
        "summary": story.summary.strip(),
        "language": version.language,
        "approved_script": version.content,
        "script_version_id": version.id,
        "content_hash": version.content_hash,
        "sources": sources_payload,
        "storyboard": storyboard.model_dump(mode="json")["scenes"],
        "editorial_approval": {
            "status": "approved",
            "approved_by": approval.actor_id,
            "approved_at": _iso(approval.approved_at),
        },
    }


def _finalize(
    db: Session,
    document: dict,
    *,
    story_id: int | None,
    actor_id: str,
    persist: bool,
) -> dict:
    """Asigna handoff_id determinista, created_at y registra la emisión.

    Si el mismo snapshot ya se emitió (idempotencia), se devuelve el fichero
    guardado tal cual, sin duplicar registros.
    """
    core = {k: v for k, v in document.items() if k not in ("handoff_id", "created_at")}
    core_json = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(core_json.encode("utf-8")).hexdigest()[:12]
    if document["mode"] == "single" and story_id is not None:
        handoff_id = f"hn1-s{story_id}-v{document['stories'][0]['revision']}-{digest}"
    else:
        handoff_id = f"hn1-batch-{digest}"
    document["handoff_id"] = handoff_id
    document["created_at"] = utcnow().isoformat()

    path = config.STORAGE_DIR / "handoffs" / f"{handoff_id}.json"
    if persist and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if persist:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    db.add(
        AuditLog(
            event="handoff.emitted",
            actor_id=actor_id,
            detail={
                "handoff_id": handoff_id,
                "mode": document["mode"],
                "output_format": document["output_format"],
                "stories": [
                    {"story_id": s["story_id"], "revision": s["revision"]}
                    for s in document["stories"]
                ],
            },
        )
    )
    return document


def emit_single_handoff(
    db: Session,
    story_id: int,
    *,
    output_format: str = "9:16",
    style_profile: dict | None = None,
    actor_id: str = "system",
    persist: bool = True,
) -> dict:
    """Emite (o devuelve, si ya existía) el handoff de una noticia aprobada."""
    story = db.get(Story, story_id)
    if story is None:
        raise HandoffError("Esa noticia no existe.")
    story_payload = build_story_payload(db, story)
    document = {
        "schema_version": SCHEMA_VERSION,
        "mode": "single",
        "output_format": output_format,
        "style_profile": style_profile or default_style_profile(output_format),
        "stories": [story_payload],
    }
    return _finalize(db, document, story_id=story.id, actor_id=actor_id, persist=persist)


def emit_batch_handoff(
    db: Session,
    batch_id: int,
    *,
    output_format: str = "9:16",
    style_profile: dict | None = None,
    actor_id: str = "system",
    persist: bool = True,
) -> dict:
    """Emite el handoff de un lote completo; si alguna noticia bloquea, no emite nada."""
    batch = db.get(Batch, batch_id)
    if batch is None:
        raise HandoffError("Ese lote no existe.")
    items = (
        db.scalars(
            select(BatchItem)
            .where(BatchItem.batch_id == batch.id)
            .order_by(BatchItem.position, BatchItem.id)
        )
        .all()
    )
    if len(items) not in (5, 10):
        raise HandoffError(
            f"El lote tiene {len(items)} noticias; el contrato sólo acepta lotes de 5 o 10."
        )
    report: list[str] = []
    for item in items:
        story = db.get(Story, item.story_id)
        if story is None:
            report.append(f"La noticia del lote (id {item.story_id}) no existe.")
            continue
        report.extend(f"«{story.title}» (id {story.id}): {p}" for p in story_handoff_problems(db, story))
    if report:
        raise HandoffError(
            "El lote no se puede traspasar; corrige estas noticias y vuelve a intentarlo:\n- "
            + "\n- ".join(report)
        )
    stories_payload = [build_story_payload(db, db.get(Story, item.story_id)) for item in items]
    document = {
        "schema_version": SCHEMA_VERSION,
        "mode": "batch",
        "output_format": output_format,
        "style_profile": style_profile or default_style_profile(output_format),
        "stories": stories_payload,
    }
    return _finalize(db, document, story_id=None, actor_id=actor_id, persist=persist)
