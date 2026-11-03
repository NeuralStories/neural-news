"use client";

import {
  APPROVAL_LABEL,
  ORIGIN_LABEL,
  STAGE_LABEL,
  VERIFICATION_LABEL,
  type ApprovalState,
  type ContentOrigin,
  type VerificationState,
  type WorkflowStage,
} from "@/lib/editorialState";

/**
 * Cabecera de decisión: dice en una pantalla dónde está la noticia, qué sabe,
 * qué versión vale, cuál es su origen y qué acción segura sigue.
 * Cada dimensión es independiente (etapa ≠ verificación ≠ aprobación ≠ origen).
 */
export function DecisionHeader({
  stage,
  verification,
  approval,
  origin,
  claimTotal,
  claimVerified,
  scriptVersion,
  approvedBy,
  approvedAt,
}: {
  stage: WorkflowStage;
  verification: VerificationState;
  approval: ApprovalState;
  origin: ContentOrigin;
  claimTotal: number;
  claimVerified: number;
  scriptVersion: number | null;
  approvedBy?: string | null;
  approvedAt?: string | null;
}) {
  const cells = [
    { label: "Etapa", value: STAGE_LABEL[stage] },
    {
      label: "Verificación",
      value:
        claimTotal === 0
          ? "Sin afirmaciones"
          : `${claimVerified} / ${claimTotal} afirmaciones`,
    },
    {
      label: "Guion",
      value: scriptVersion ? `v${scriptVersion}` : "Sin guion",
    },
    { label: "Aprobación", value: APPROVAL_LABEL[approval] },
    { label: "Origen", value: ORIGIN_LABEL[origin] },
  ];

  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 lg:grid-cols-5">
      {cells.map((cell) => (
        <div key={cell.label} className="min-w-0">
          <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
            {cell.label}
          </dt>
          <dd className="mt-0.5 truncate text-sm text-slate-100" title={cell.value}>
            {cell.value}
          </dd>
        </div>
      ))}
      {approval === "approved" && approvedAt && (
        <div className="col-span-2 sm:col-span-3 lg:col-span-5">
          <p className="text-xs text-emerald-300">
            Guion v{scriptVersion} aprobado por {approvedBy} el {approvedAt}.
          </p>
        </div>
      )}
    </dl>
  );
}

/** Task list de preparación: qué está hecho, qué requiere atención y qué falta. */
export function ReadinessChecklist({
  steps,
}: {
  steps: { key: string; label: string; state: "done" | "attention" | "pending"; detail?: string }[];
}) {
  const icon = { done: "✓", attention: "!", pending: "○" } as const;
  const tone = {
    done: "text-emerald-400",
    attention: "text-amber-400",
    pending: "text-slate-500",
  } as const;
  return (
    <ol className="space-y-1.5">
      {steps.map((step) => (
        <li key={step.key} className="flex items-start gap-2 text-sm">
          <span
            aria-hidden
            className={`mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold ${
              step.state === "done"
                ? "border-emerald-700 bg-emerald-950 text-emerald-300"
                : step.state === "attention"
                  ? "border-amber-700 bg-amber-950 text-amber-300"
                  : "border-slate-700 bg-slate-900 text-slate-500"
            }`}
          >
            {icon[step.state]}
          </span>
          <span className="min-w-0">
            <span className={tone[step.state]}>{step.label}</span>
            {step.detail && (
              <span className="ml-1.5 text-xs text-slate-400">{step.detail}</span>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}
