"use client";

import type {
  ApprovalState,
  ContentOrigin,
  VerificationState,
  WorkflowStage,
} from "@/lib/types";

/**
 * Ayudas de presentación sobre el estado editorial.
 *
 * El estado (etapa, verificación, aprobación, procedencia y bloqueos) lo
 * calcula el backend en `services/editorial_status.py` y llega ya resuelto en
 * cada noticia: aquí sólo se formatea y se construye el checklist de
 * preparación, sin recalcular nada.
 */

export type {
  ApprovalState,
  ContentOrigin,
  VerificationState,
  WorkflowStage,
};

export const STAGE_LABEL: Record<WorkflowStage, string> = {
  candidate: "Candidata",
  research: "Investigación",
  script: "Guion",
  approved: "Aprobada",
  rejected: "Descartada",
};

export const VERIFICATION_LABEL: Record<VerificationState, string> = {
  unverified: "Sin verificar",
  in_review: "En revisión",
  verified: "Verificada",
  disputed: "Con contradicciones",
  opinion: "No verificable (opinión)",
};

export const APPROVAL_LABEL: Record<ApprovalState, string> = {
  not_requested: "No solicitada",
  pending: "Pendiente de aprobación",
  approved: "Aprobada por una persona",
  superseded: "Anulada por una edición posterior",
};

export const ORIGIN_LABEL: Record<ContentOrigin, string> = {
  real: "Contenido real",
  demo: "Contenido ficticio (DEMO)",
  manual: "Aportado a mano",
  unknown: "Origen no determinado",
};

export interface ReadinessStep {
  key: string;
  label: string;
  state: "done" | "attention" | "pending";
  detail?: string;
}

export interface ReadinessInput {
  status: string;
  sourcesCount: number;
  hasContent: boolean;
  claims: { verification_status: string }[];
  versions: { version: number }[];
  approval: ApprovalState;
  inBatch: boolean;
  productionBlockers?: string[];
}

/**
 * Estado de preparación: qué está hecho y qué falta, en el orden del flujo
 * (fuente → contenido → verificación → guion → aprobación → lote → traspaso).
 */
export function readinessSteps(input: ReadinessInput): ReadinessStep[] {
  const steps: ReadinessStep[] = [];
  const unverified = input.claims.filter((c) => c.verification_status === "UNVERIFIED").length;
  const contradicted = input.claims.filter((c) => c.verification_status === "CONTRADICTED").length;
  const latest = input.versions.length > 0 ? input.versions[input.versions.length - 1].version : null;

  steps.push({
    key: "fuente",
    label: "Fuente registrada",
    state: input.sourcesCount > 0 ? "done" : "attention",
    detail:
      input.sourcesCount > 0
        ? `${input.sourcesCount} fuente(s) vinculada(s)`
        : "La noticia no tiene ninguna fuente",
  });
  steps.push({
    key: "contenido",
    label: "Contenido disponible",
    state: input.hasContent ? "done" : "pending",
    detail: input.hasContent ? "Hay texto o transcripción analizable" : "Sin contenido analizable",
  });
  steps.push({
    key: "afirmaciones",
    label: "Afirmaciones verificadas",
    state:
      input.claims.length === 0 ? "attention" : unverified > 0 || contradicted > 0 ? "attention" : "done",
    detail:
      input.claims.length === 0
        ? "Aún no hay afirmaciones: lanza «Investigar»"
        : contradicted > 0
          ? `${contradicted} afirmación(es) contradichas por la evidencia`
          : unverified > 0
            ? `${unverified} afirmación(es) sin evidencia suficiente`
            : `${input.claims.length} afirmación(es) respaldadas`,
  });
  steps.push({
    key: "guion",
    label: "Guion vigente",
    state: latest !== null ? "done" : "pending",
    detail: latest !== null ? `v${latest}` : "Sin guion: genera un borrador",
  });
  steps.push({
    key: "aprobacion",
    label: "Aprobación humana",
    state:
      input.approval === "approved"
        ? "done"
        : input.approval === "superseded" || input.approval === "pending"
          ? "attention"
          : "pending",
    detail:
      input.approval === "approved"
        ? "Guion aprobado"
        : input.approval === "superseded"
          ? "La edición posterior anuló la aprobación: vuelve a aprobar"
          : input.approval === "pending"
            ? "Pendiente de aprobación"
            : "Todavía no se ha aprobado ningún guion",
  });
  steps.push({
    key: "lote",
    label: "Añadida a un lote",
    state: input.inBatch ? "done" : "pending",
    detail: input.inBatch ? "En un lote editorial" : "Pendiente de añadir a un lote",
  });
  steps.push({
    key: "traspaso",
    label: "Traspaso a producción",
    state:
      input.approval === "approved" && (input.productionBlockers?.length ?? 0) === 0
        ? "done"
        : input.approval === "approved"
          ? "attention"
          : "pending",
    detail:
      input.approval === "approved"
        ? (input.productionBlockers?.length ?? 0) === 0
          ? "Se puede generar el traspaso para Studio"
          : (input.productionBlockers ?? [])[0]
        : "Requiere un guion aprobado",
  });
  return steps;
}
