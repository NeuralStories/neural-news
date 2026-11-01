'use client';

/**
 * Dossier editorial del proyecto (NN-107 F4, decisión D7): fuentes, afirmaciones
 * y estados de verificación leídos del motor editorial (/v1/stories), nunca de
 * una redacción paralela. Importar una noticia no la verifica (F-08/F-03).
 */
import React, { useEffect, useState } from 'react';

interface DossierData {
  linked: boolean;
  message?: string;
  story?: { id: number; title: string; status: string };
  sources?: Array<{ source_id: number; title: string | null; canonical_url: string | null; provider: string; relevance: string | null }>;
  claims?: Array<{ claim_id: number; statement: string; verification_status: string }>;
}

const STATUS_LABELS: Record<string, string> = {
  UNVERIFIED: 'Sin verificar',
  SUPPORTED: 'Respaldada',
  CONTRADICTED: 'Contradicha',
  CONFIRMED: 'Confirmada',
  DESACTUALIZADA: 'Desactualizada',
};

export const DossierPanel: React.FC<{ projectId: number }> = ({ projectId }) => {
  const [dossier, setDossier] = useState<DossierData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/v1/projects/${projectId}/dossier`, { credentials: 'same-origin' })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Error ${r.status}`))))
      .then((data) => {
        if (alive) setDossier(data);
      })
      .catch((err: Error) => {
        if (alive) setError(err.message);
      });
    return () => {
      alive = false;
    };
  }, [projectId]);

  if (error) {
    return (
      <p className="rounded border border-rose-900 bg-rose-950/50 p-2 text-[11px] text-rose-200">
        No se pudo cargar el dossier editorial: {error}
      </p>
    );
  }
  if (!dossier) {
    return <p className="text-[11px] text-slate-500">Cargando dossier editorial…</p>;
  }
  if (!dossier.linked) {
    return (
      <p className="rounded border border-slate-800 bg-slate-900/70 p-2 text-[11px] text-slate-400">
        Dossier editorial: sin noticia vinculada. Vincula una historia del motor para traer sus
        fuentes y afirmaciones verificadas (una sola redacción).
      </p>
    );
  }
  return (
    <div className="space-y-2 rounded-lg border border-sky-900/60 bg-slate-900/70 p-3">
      <p className="text-xs font-bold text-sky-300">
        Dossier editorial vinculado · historia #{dossier.story?.id} · {dossier.story?.status}
      </p>
      {dossier.sources && dossier.sources.length > 0 && (
        <ul className="space-y-1 text-[11px] text-slate-300">
          {dossier.sources.map((s) => (
            <li key={s.source_id}>
              <span className="text-slate-500">[{s.provider}]</span> {s.title}
              {s.canonical_url ? ` · ${s.canonical_url}` : ''}
            </li>
          ))}
        </ul>
      )}
      {dossier.claims && dossier.claims.length > 0 && (
        <ul className="space-y-1 text-[11px]">
          {dossier.claims.map((c) => (
            <li key={c.claim_id}>
              <span
                className={
                  c.verification_status === 'CONTRADICTED'
                    ? 'font-mono text-rose-400'
                    : c.verification_status === 'SUPPORTED' || c.verification_status === 'CONFIRMED'
                      ? 'font-mono text-emerald-400'
                      : 'font-mono text-amber-400'
                }
              >
                {STATUS_LABELS[c.verification_status] ?? c.verification_status}
              </span>{' '}
              {c.statement}
            </li>
          ))}
        </ul>
      )}
      <p className="text-[10px] text-slate-500">
        El estado de verificación lo decide el motor editorial; importar o traspasar nunca verifica (F-08).
      </p>
    </div>
  );
};
