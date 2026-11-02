// GENERADO POR tools/generate_estados.py — NO EDITAR A MANO.
//
// La fuente de verdad es `apps/api/src/neuralnews/states.py`.
// Regenerar: `python tools/generate_estados.py`
// Comprobar (CI): `python tools/generate_estados.py --check`

// --- Estados ---------------------------------------------------------------

export const ESTADOS_FUENTE = ["NEW", "FETCHING", "READY", "PARTIAL", "METADATA_ONLY", "FAILED"] as const;
export const ESTADOS_NOTICIA = ["CANDIDATE", "RESEARCHING", "REVIEW_REQUIRED", "SCRIPT_DRAFT", "APPROVED", "REJECTED"] as const;
export const ESTADOS_TRABAJO = ["QUEUED", "RUNNING", "DONE", "RETRYABLE_FAILED", "FAILED", "UNKNOWN"] as const;
export const ESTADOS_PAQUETE = ["NOT_STARTED", "DRAFT", "READY_FOR_REVIEW", "EXPORTED"] as const;

// --- Etiquetas en español ---------------------------------------------------

export const ETIQUETA_FUENTE: Record<string, string> = {
  NEW: "Pendiente",
  FETCHING: "Analizando",
  READY: "Lista",
  PARTIAL: "Parcial",
  METADATA_ONLY: "Sin transcripción",
  FAILED: "Error"
};
export const ETIQUETA_NOTICIA: Record<string, string> = {
  CANDIDATE: "Candidata",
  RESEARCHING: "Investigando",
  REVIEW_REQUIRED: "Revisar",
  SCRIPT_DRAFT: "Borrador de guion",
  APPROVED: "Aprobada",
  REJECTED: "Descartada"
};
export const ETIQUETA_TRABAJO: Record<string, string> = {
  QUEUED: "En cola",
  RUNNING: "En marcha",
  DONE: "Terminado",
  RETRYABLE_FAILED: "Reintentando",
  FAILED: "Error",
  UNKNOWN: "Estado desconocido"
};
export const ETIQUETA_PAQUETE: Record<string, string> = {
  NOT_STARTED: "Sin empezar",
  DRAFT: "Borrador",
  READY_FOR_REVIEW: "Listo para revisar",
  EXPORTED: "Exportado"
};
export const ETIQUETA_APROBACION: Record<string, string> = {
  ACTIVE: "Aprobada",
  INVALIDATED: "Aprobación anulada (se editó el guion)",
  REVOKED: "Retirada"
};
export const ETIQUETA_TIPO_CONTENIDO: Record<string, string> = {
  TRANSCRIPT: "Transcripción",
  VIDEO_ANALYSIS: "Análisis del vídeo (no es transcripción literal)",
  ARTICLE_TEXT: "Texto del artículo",
  MANUAL_TEXT: "Texto aportado",
  AUDIO_FILE: "Archivo de audio (pendiente de transcribir)",
  METADATA_ONLY: "Solo información básica"
};
export const ETIQUETA_VERIFICACION: Record<string, string> = {
  UNVERIFIED: "Sin verificar",
  SUPPORTED: "Confirmada",
  CONTRADICTED: "Contradicha",
  NOT_VERIFIABLE: "No verificable (opinión)"
};
export const ETIQUETA_TIPO_AFIRMACION: Record<string, string> = {
  PRIMARY: "Fuente primaria",
  CORROBORATION: "Corroboración",
  CONTRADICTING: "Contradicción",
  REFERENCE: "Referencia"
};
