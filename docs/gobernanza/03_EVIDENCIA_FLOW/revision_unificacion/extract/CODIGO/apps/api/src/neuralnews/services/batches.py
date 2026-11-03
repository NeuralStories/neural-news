"""Lotes editoriales (5 o 10 noticias) y exportación del paquete editorial.

El paquete ZIP contiene: guiones en Markdown, manifiesto JSON (noticias, afirmaciones,
evidencia, fuentes, storyboard y prompts de imagen) y estados de aprobación exactos.
Ninguna noticia sin aprobación aparece como lista para publicar.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import STORAGE_DIR
from ..models import (
    Approval,
    Batch,
    BatchItem,
    Claim,
    Evidence,
    ProductionPackage,
    ScriptVersion,
    Source,
    Story,
    StorySource,
    utcnow,
)
from ..providers.image_prompt import build_storyboard
from .editorial_status import build_story_status
from ..services.scripts import active_approval, latest_version
from ..states import SOURCE_LABELS, STORY_LABELS

BATCH_SIZES = (5, 10)


class BatchError(ValueError):
    pass


def create_batch(db: Session, *, name: str, target_size: int, story_ids: list[int]) -> Batch:
    if target_size not in BATCH_SIZES:
        raise BatchError("El lote debe ser de 5 o 10 noticias")
    if len(story_ids) != target_size:
        raise BatchError(f"Selecciona exactamente {target_size} noticias (has elegido {len(story_ids)})")
    if len(set(story_ids)) != len(story_ids):
        raise BatchError("Hay noticias repetidas en la selección")
    stories = db.scalars(select(Story).where(Story.id.in_(story_ids))).all()
    found = {s.id for s in stories}
    missing = [sid for sid in story_ids if sid not in found]
    if missing:
        raise BatchError(f"Alguna noticia no existe: {missing}")

    batch = Batch(name=name or f"Lote de {target_size}", target_size=target_size, status="DRAFT")
    db.add(batch)
    db.flush()
    for position, story_id in enumerate(story_ids):
        db.add(BatchItem(batch_id=batch.id, story_id=story_id, position=position))
    db.flush()
    return batch


def batch_overview(db: Session, batch: Batch) -> dict:
    items = db.scalars(
        select(BatchItem).where(BatchItem.batch_id == batch.id).order_by(BatchItem.position)
    ).all()
    stories = []
    for item in items:
        story = db.get(Story, item.story_id)
        approval = active_approval(db, story.id)
        version = latest_version(db, story.id)
        approved = bool(approval and approval.status == "ACTIVE")

        # Estado editorial completo (misma fuente de verdad que la web y el traspaso).
        status = build_story_status(
            db,
            story,
            versions=[version] if version else [],
            claims=list(db.scalars(select(Claim).where(Claim.story_id == story.id)).all()),
            approved_version_id=approval.script_version_id if approval else None,
            pending_flag=False,
        )
        stories.append(
            {
                "position": item.position,
                "story_id": story.id,
                "title": story.title,
                "status": story.status,
                "status_label": STORY_LABELS.get(story.status, story.status),
                # `approved` mantiene su significado histórico: hay guion aprobado.
                "approved": approved,
                "script_version": version.version if version else None,
                "pending_reason": (
                    None
                    if approved
                    else "Este guion necesita aprobación antes de grabarse"
                ),
                # Nuevos campos: motivo real y disponibilidad para producción.
                "blockers": status.production_blockers,
                "production_ready": status.production_ready,
                "origin": status.origin,
                "claim_count": status.claim_total,
                "unverified_claims": status.claim_unverified,
                "has_summary": status.has_summary,
            }
        )
    return {
        "id": batch.id,
        "name": batch.name,
        "target_size": batch.target_size,
        "status": batch.status,
        "stories": stories,
        # Semántica histórica conservada: aprobadas / no aprobadas.
        "ready_count": sum(1 for s in stories if s["approved"]),
        "pending_count": sum(1 for s in stories if not s["approved"]),
        # Métrica nueva: además de aprobadas, sin bloqueos de producción.
        "production_ready_count": sum(1 for s in stories if s["production_ready"]),
        "blocked_count": sum(1 for s in stories if not s["production_ready"]),
    }

def _safe_filename(story_id: int, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"{story_id:04d}-{slug or 'noticia'}"


def export_batch(db: Session, batch: Batch, actor_id: str = "system") -> ProductionPackage:
    """Genera el paquete ZIP (Markdown + JSON) y lo registra con su hash."""
    overview = batch_overview(db, batch)
    manifest_stories: list[dict] = []
    md_parts: list[str] = []
    md_parts.append(f"# Lote editorial: {batch.name}\n")
    md_parts.append(f"Generado: {utcnow().isoformat()} · Tamaño: {batch.target_size}\n")
    md_parts.append(
        "Estado por noticia: sólo los guiones marcados como «Aprobada» están listos para locución.\n"
    )

    for entry in overview["stories"]:
        story = db.get(Story, entry["story_id"])
        version = latest_version(db, story.id)
        approval = active_approval(db, story.id)
        approved = entry["approved"]

        sources_rows = db.scalars(
            select(StorySource).where(StorySource.story_id == story.id)
        ).all()
        sources_payload = []
        for link in sources_rows:
            source = db.get(Source, link.source_id)
            sources_payload.append(
                {
                    "source_id": source.id,
                    "provider": source.provider,
                    "canonical_url": source.canonical_url,
                    "title": source.title,
                    "published_at": source.published_at.isoformat() if source.published_at else None,
                    "status": source.status,
                    "status_label": SOURCE_LABELS.get(source.status, source.status),
                    "relevance": link.relevance,
                }
            )

        claims_payload = []
        for claim in db.scalars(select(Claim).where(Claim.story_id == story.id)).all():
            evidence_rows = db.scalars(select(Evidence).where(Evidence.claim_id == claim.id)).all()
            claims_payload.append(
                {
                    "statement": claim.statement,
                    "verification_status": claim.verification_status,
                    "verification_notes": claim.verification_notes,
                    "evidence": [
                        {
                            "url": e.url,
                            "publisher": e.publisher,
                            "published_at": e.published_at.isoformat() if e.published_at else None,
                            "retrieved_at": e.retrieved_at.isoformat() if e.retrieved_at else None,
                            "excerpt_or_paraphrase": e.excerpt_or_paraphrase,
                            "kind": e.kind,
                            "confidence": e.confidence,
                            "demo": e.demo,
                        }
                        for e in evidence_rows
                    ],
                }
            )

        storyboard = build_storyboard(story, version, approval) if version else None
        manifest_stories.append(
            {
                "story_id": story.id,
                "title": story.title,
                "summary": story.summary,
                "status": story.status,
                "status_label": entry["status_label"],
                "approval": (
                    {
                        "status": approval.status,
                        "approved_at": approval.approved_at.isoformat(),
                        "actor": approval.actor_id,
                        "script_version_id": approval.script_version_id,
                        "content_hash": approval.script_version.content_hash,
                    }
                    if approval
                    else None
                ),
                "editorial_score": story.editorial_score,
                "score_breakdown": story.score_breakdown,
                "script": (
                    {
                        "version": version.version,
                        "content": version.content,
                        "target_duration_s": version.target_duration_s,
                        "author_type": version.author_type,
                        "content_hash": version.content_hash,
                        "approved": approved,
                    }
                    if version
                    else None
                ),
                "sources": sources_payload,
                "claims": claims_payload,
                "storyboard": storyboard.model_dump(mode="json") if storyboard else None,
                "visual_note": (
                    "Prompts preliminares para usar manualmente en la herramienta de vídeo elegida. "
                    "No se han generado imágenes ni vídeo."
                ),
            }
        )

        md_parts.append(f"\n## {entry['position'] + 1}. {story.title}\n")
        state_line = f"- Estado: **{entry['status_label']}**"
        if approved:
            state_line += " (aprobada, lista para locución)"
        else:
            state_line += " — PENDIENTE DE APROBACIÓN, no grabar todavía"
        md_parts.append(state_line)
        if version:
            md_parts.append(
                f"- Guion: versión {version.version} · hash {version.content_hash[:12]} · "
                f"duración estimada {version.target_duration_s} s"
            )
            md_parts.append("")
            md_parts.append("```")
            md_parts.append(version.content)
            md_parts.append("```")
        if claims_payload:
            md_parts.append("\nAfirmaciones y verificación:\n")
            for c in claims_payload:
                md_parts.append(f"- [{c['verification_status']}] {c['statement']}")
                for e in c["evidence"]:
                    md_parts.append(f"  - Evidencia ({e['kind']}): {e['url']} — {e['publisher']}")

    manifest = {
        "package": "neural.news paquete editorial",
        "generated_at": utcnow().isoformat(),
        "batch": {"id": batch.id, "name": batch.name, "target_size": batch.target_size},
        "approved_count": overview["ready_count"],
        "pending_count": overview["pending_count"],
        "stories": manifest_stories,
        "disclaimer": (
            "Prompts de imagen y storyboard son orientativos. Este paquete no contiene "
            "imágenes ni vídeo generados."
        ),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lote/manifiesto.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("lote/guiones.md", "\n".join(md_parts))
        for story in manifest_stories:
            script = story.get("script")
            if script:
                zf.writestr(
                    f"lote/guiones/{_safe_filename(story['story_id'], story['title'])}.md",
                    f"# {story['title']}\n\n{script['content']}\n",
                )
    data = buffer.getvalue()

    packages_dir = STORAGE_DIR / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    latest_id = db.scalar(select(ProductionPackage.id).order_by(ProductionPackage.id.desc()).limit(1))
    package_version = (latest_id or 0) + 1
    filename = f"lote-{batch.id}-v{package_version}.zip"
    path = packages_dir / filename
    path.write_bytes(data)

    for pkg in db.scalars(
        select(ProductionPackage).where(ProductionPackage.batch_id == batch.id)
    ).all():
        pkg.state = "DRAFT"

    package = ProductionPackage(
        batch_id=batch.id,
        package_version=package_version,
        mime_type="application/zip",
        storage_path=str(path),
        sha256=hashlib.sha256(data).hexdigest(),
        state="EXPORTED",
    )
    db.add(package)
    batch.status = "READY_FOR_REVIEW"
    db.flush()
    return package


def read_package(package: ProductionPackage) -> bytes:
    return Path(package.storage_path).read_bytes()
