"use client";

/**
 * Mapa de estados **único** de la web (NN-113.6).
 *
 * Antes de este fichero el mismo mapa estado→insignia estaba copiado en tres
 * sitios (`app/noticias/page.tsx`, `app/noticias/[id]/page.tsx` y
 * `app/fuentes/page.tsx`) y un cuarto mapa, **distinto**, en
 * `features/studio/components/DossierPanel.tsx` (con dos estados que no existen
 * en el backend: `CONFIRMED` y `DESACTUALIZADA`). Cuatro definiciones que
 * pueden divergir; dos ya lo habían hecho.
 *
 * Ahora:
 *   - los **estados y las etiquetas en español** vienen generados del backend
 *     (`apps/api/src/neuralnews/states.py`) en `estados.generado.ts`;
 *   - las **insignias** (presentación, sólo de la web) están aquí, en un sitio;
 *   - las páginas importan de aquí. Si hace falta un estado nuevo, se añade en
 *     el backend, se regenera y salta el test `test_estados_compartidos.py`.
 */
import {
  ESTADOS_FUENTE,
  ESTADOS_NOTICIA,
  ESTADOS_PAQUETE,
  ESTADOS_TRABAJO,
  ETIQUETA_FUENTE,
  ETIQUETA_NOTICIA,
  ETIQUETA_PAQUETE,
  ETIQUETA_TRABAJO,
  ETIQUETA_TIPO_AFIRMACION,
  ETIQUETA_VERIFICACION,
} from "./estados.generado";

export {
  ESTADOS_FUENTE,
  ESTADOS_NOTICIA,
  ESTADOS_PAQUETE,
  ESTADOS_TRABAJO,
  ETIQUETA_FUENTE,
  ETIQUETA_NOTICIA,
  ETIQUETA_PAQUETE,
  ETIQUETA_TRABAJO,
  ETIQUETA_TIPO_AFIRMACION,
  ETIQUETA_VERIFICACION,
};

/** Insignias disponibles (definidas en `app/globals.css`). */
export type Insignia = "badge-ok" | "badge-warn" | "badge-err" | "badge-info" | "badge-neutral";

/** Estado → insignia. Un solo mapa por clase de estado. */
export const BADGE_DE_NOTICIA: Record<string, Insignia> = {
  CANDIDATE: "badge-neutral",
  RESEARCHING: "badge-info",
  REVIEW_REQUIRED: "badge-warn",
  SCRIPT_DRAFT: "badge-info",
  APPROVED: "badge-ok",
  REJECTED: "badge-neutral",
};

export const BADGE_DE_FUENTE: Record<string, Insignia> = {
  NEW: "badge-neutral",
  FETCHING: "badge-info",
  READY: "badge-ok",
  PARTIAL: "badge-warn",
  METADATA_ONLY: "badge-warn",
  FAILED: "badge-err",
};

export const BADGE_DE_TRABAJO: Record<string, Insignia> = {
  QUEUED: "badge-neutral",
  RUNNING: "badge-info",
  DONE: "badge-ok",
  RETRYABLE_FAILED: "badge-warn",
  FAILED: "badge-err",
  UNKNOWN: "badge-neutral",
};

export const BADGE_DE_PAQUETE: Record<string, Insignia> = {
  NOT_STARTED: "badge-neutral",
  DRAFT: "badge-info",
  READY_FOR_REVIEW: "badge-warn",
  EXPORTED: "badge-ok",
};

export const BADGE_DE_VERIFICACION: Record<string, Insignia> = {
  UNVERIFIED: "badge-warn",
  SUPPORTED: "badge-ok",
  CONTRADICTED: "badge-err",
  NOT_VERIFIABLE: "badge-neutral",
};

/**
 * Tono de un estado de verificación, para texto (no insignias). El panel del
 * dossier **no** usa insignias sino color del texto: sin este mapa, el mismo
 * estado se pintaría de dos maneras distintas según la pantalla.
 */
export type Tono = "ok" | "aviso" | "error" | "info" | "neutro";

export const TONO_DE_VERIFICACION: Record<string, Tono> = {
  UNVERIFIED: "aviso",
  SUPPORTED: "ok",
  CONTRADICTED: "error",
  NOT_VERIFIABLE: "neutro",
};

/**
 * Insignia de un estado, con reserva honesta: si el estado no está en el mapa
 * se muestra `badge-neutral` y **no** se inventa un color.
 */
export function insigniaDe(
  mapa: Record<string, Insignia>,
  estado: string | null | undefined,
): Insignia {
  if (!estado) return "badge-neutral";
  return mapa[estado] ?? "badge-neutral";
}

/** Etiqueta en español de un estado; si no se conoce, se devuelve el propio estado. */
export function etiquetaDe(
  mapa: Record<string, string>,
  estado: string | null | undefined,
  porDefecto?: string,
): string {
  if (estado && mapa[estado]) return mapa[estado];
  return porDefecto ?? estado ?? "";
}
