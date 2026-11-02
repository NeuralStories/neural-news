"""Estados del dominio, sus transiciones permitidas y sus etiquetas para el usuario.

El usuario final nunca ve los nombres técnicos: sólo las etiquetas en español.
"""
from __future__ import annotations

SOURCE_STATES = ("NEW", "FETCHING", "READY", "PARTIAL", "METADATA_ONLY", "FAILED")
SOURCE_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"FETCHING", "READY", "PARTIAL", "METADATA_ONLY", "FAILED"},
    "FETCHING": {"READY", "PARTIAL", "METADATA_ONLY", "FAILED"},
    "READY": {"FETCHING"},
    "PARTIAL": {"FETCHING"},
    "METADATA_ONLY": {"FETCHING"},
    "FAILED": {"FETCHING"},
}

STORY_STATES = (
    "CANDIDATE",
    "RESEARCHING",
    "REVIEW_REQUIRED",
    "SCRIPT_DRAFT",
    "APPROVED",
    "REJECTED",
)
STORY_TRANSITIONS: dict[str, set[str]] = {
    "CANDIDATE": {"RESEARCHING", "SCRIPT_DRAFT", "REJECTED"},
    # RESEARCHING → RESEARCHING permite reinvestigar tras una ejecución interrumpida (idempotente).
    "RESEARCHING": {"REVIEW_REQUIRED", "SCRIPT_DRAFT", "RESEARCHING", "REJECTED"},
    "REVIEW_REQUIRED": {"SCRIPT_DRAFT", "RESEARCHING", "REJECTED"},
    "SCRIPT_DRAFT": {"APPROVED", "RESEARCHING", "REJECTED"},
    # APPROVED → RESEARCHING: reinvestigar una noticia aprobada es legítimo
    # (puede haber evidencia nueva). La aprobación queda anulada, igual que
    # cuando se edita el guion (hallazgo B23).
    "APPROVED": {"SCRIPT_DRAFT", "RESEARCHING", "REJECTED"},
    "REJECTED": set(),
}

JOB_STATES = ("QUEUED", "RUNNING", "DONE", "RETRYABLE_FAILED", "FAILED", "UNKNOWN")
JOB_TRANSITIONS: dict[str, set[str]] = {
    "QUEUED": {"RUNNING", "FAILED"},
    "RUNNING": {"DONE", "RETRYABLE_FAILED", "FAILED", "UNKNOWN"},
    "RETRYABLE_FAILED": {"QUEUED", "RUNNING", "FAILED"},
    "FAILED": set(),
    "DONE": set(),
    "UNKNOWN": {"QUEUED"},
}

PACKAGE_STATES = ("NOT_STARTED", "DRAFT", "READY_FOR_REVIEW", "EXPORTED")


def assert_transition(kind: str, current: str, target: str) -> None:
    table = {"source": SOURCE_TRANSITIONS, "story": STORY_TRANSITIONS, "job": JOB_TRANSITIONS}[kind]
    if target not in table.get(current, set()):
        raise ValueError(f"Transición de estado no permitida en {kind}: {current} → {target}")


SOURCE_LABELS = {
    "NEW": "Pendiente",
    "FETCHING": "Analizando",
    "READY": "Lista",
    "PARTIAL": "Parcial",
    "METADATA_ONLY": "Sin transcripción",
    "FAILED": "Error",
}

STORY_LABELS = {
    "CANDIDATE": "Candidata",
    "RESEARCHING": "Investigando",
    "REVIEW_REQUIRED": "Revisar",
    "SCRIPT_DRAFT": "Borrador de guion",
    "APPROVED": "Aprobada",
    "REJECTED": "Descartada",
}

JOB_LABELS = {
    "QUEUED": "En cola",
    "RUNNING": "En marcha",
    "DONE": "Terminado",
    "RETRYABLE_FAILED": "Reintentando",
    "FAILED": "Error",
    "UNKNOWN": "Estado desconocido",
}

APPROVAL_LABELS = {
    "ACTIVE": "Aprobada",
    "INVALIDATED": "Aprobación anulada (se editó el guion)",
    "REVOKED": "Retirada",
}

CONTENT_TYPE_LABELS = {
    "TRANSCRIPT": "Transcripción",
    "VIDEO_ANALYSIS": "Análisis del vídeo (no es transcripción literal)",
    "ARTICLE_TEXT": "Texto del artículo",
    "MANUAL_TEXT": "Texto aportado",
    "AUDIO_FILE": "Archivo de audio (pendiente de transcribir)",
    "METADATA_ONLY": "Solo información básica",
}

PACKAGE_LABELS = {
    "NOT_STARTED": "Sin empezar",
    "DRAFT": "Borrador",
    "READY_FOR_REVIEW": "Listo para revisar",
    "EXPORTED": "Exportado",
}

# Estados de verificación de una afirmación (afirmaciones del dossier).
CLAIM_VERIFICATION_LABELS = {
    "UNVERIFIED": "Sin verificar",
    "SUPPORTED": "Confirmada",
    "CONTRADICTED": "Contradicha",
    "NOT_VERIFIABLE": "No verificable (opinión)",
}

# Naturaleza de una evidencia aportada a una afirmación.
CLAIM_KIND_LABELS = {
    "PRIMARY": "Fuente primaria",
    "CORROBORATION": "Corroboración",
    "CONTRADICTING": "Contradicción",
    "REFERENCE": "Referencia",
}

# Todos los mapas de estado de la aplicación, en un solo sitio (NN-113.6).
# La web los recibe generados (`tools/generate_estados.py` → `lib/estados.generado.ts`)
# para que no haya dos definiciones que puedan divergir.
ESTADOS_DE_LA_APLICACION: dict[str, tuple[str, ...]] = {
    "fuente": SOURCE_STATES,
    "noticia": STORY_STATES,
    "trabajo": JOB_STATES,
    "paquete": PACKAGE_STATES,
}
