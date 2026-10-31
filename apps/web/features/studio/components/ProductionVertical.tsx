'use client';

/**
 * Recorrido vertical de producción (NN-107 F3): director audiovisual
 * determinista → tomas persistidas → prompts versionados → FlowManualPackage
 * exportable → importación del MP4 generado externamente → revisión y
 * aprobación humana. Nada simula generación ni conexión con Flow.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ProjectConflict,
  projectApi,
} from '../lib/projectApi';

interface ShotOut {
  id: number;
  sequence: number;
  shot_kind: string;
  rationale: string | null;
  start_s: number | null;
  end_s: number | null;
  max_duration_s: number | null;
  data: { beat_texts?: string[]; est_duration_s?: number };
}

interface TakeOut {
  id: number;
  shot_id: number | null;
  take_number: number;
  status: string;
  imported_media: { id: number; sha256: string; duration_s: number | null; orientation: string | null } | null;
  prompt_versions: number;
}

interface ProductionVerticalProps {
  projectId: number;
  shots: ShotOut[];
  takes: TakeOut[];
  onChanged: () => void;
}

const KIND_LABELS: Record<string, string> = {
  USER_VIDEO: 'Vídeo propio',
  FLOW_MAXDOTAI: 'maxDotAi (Flow)',
  DOCUMENTARY: 'Documental / captura real',
  DATA_GRAPHIC: 'Gráfico programático',
  GENERATIVE_BROLL: 'B-roll generativo (ilustrativo)',
  TITLE_CARD: 'Rótulo programático',
  PENDING: 'Pendiente de recurso',
};

function promptFromShot(shot: ShotOut | undefined, takeNumber: number): string {
  if (!shot) {
    return `News broadcast take ${takeNumber} featuring anchor maxDotAi, canonical CRT studio setup.`;
  }
  const dialogue = (shot.data?.beat_texts ?? []).join(' ');
  const parts: string[] = [];
  parts.push(`Objective: ${KIND_LABELS[shot.shot_kind] ?? shot.shot_kind} shot ${takeNumber} of the news piece.`);
  parts.push('Presenter: canonical maxDotAi identity from the saved master sheet; never describe a new character.');
  parts.push(`Aspect ratio: ${shot.shot_kind === 'DATA_GRAPHIC' ? 'n/a (programmatic graphic)' : 'as configured in the project'}.`);
  parts.push(`Framing and duration: shot window ${shot.start_s ?? 0}s–${shot.end_s ?? 0}s, provider clip capability respected.`);
  parts.push(`Literal narration for this window: "${dialogue}"`);
  parts.push('Constraints: identity continuity with the master sheet; purely optical effects; no invented on-screen numbers (data graphics are programmatic).');
  parts.push('Checks: references attached per manifest; script integrity; no simulated generation.');
  return parts.join(' ');
}

export const ProductionVertical: React.FC<ProductionVerticalProps> = ({
  projectId,
  shots,
  takes,
  onChanged,
}) => {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planNote, setPlanNote] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<Record<number, File>>({});
  const [graphics, setGraphics] = useState<Array<{ id: number; title: string; status: string }>>([]);
  const [graphicTitle, setGraphicTitle] = useState('Cifra destacada');
  const [graphicLabel, setGraphicLabel] = useState('Valor');
  const [graphicValue, setGraphicValue] = useState('');
  const [graphicUnit, setGraphicUnit] = useState('%');
  const fileInputs = useRef<Record<number, HTMLInputElement | null>>({});

  const takesByShot = useMemo(() => {
    const map = new Map<number, TakeOut>();
    takes.forEach((t) => {
      if (t.shot_id !== null) map.set(t.shot_id, t);
    });
    return map;
  }, [takes]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (err) {
      if (err instanceof ProjectConflict) {
        setError('El proyecto cambió en el servidor; estado recargado. Reintenta la acción.');
        onChanged();
      } else {
        setError(err instanceof Error ? err.message : 'Error inesperado');
      }
    } finally {
      setBusy(null);
    }
  };

  const runDirector = () =>
    run('director', async () => {
      const plan = await projectApi.directorPlan(projectId, 8);
      const full = await projectApi.get(projectId);
      for (const shot of full.shots as unknown as ShotOut[]) {
        if (!takesByShot.has(shot.id)) {
          await projectApi.createTake(projectId, shot.id, shot.sequence + 1);
        }
      }
      setPlanNote(
        `Plan determinista: ${plan.beats.length} beats de locución continua (${plan.total_seconds}s) ` +
          `y ${plan.shots.length} tomas (cortes solo por capacidad del proveedor: ${plan.provider_max_clip_s}s).`,
      );
    });

  const generatePrompt = (take: TakeOut) =>
    run(`prompt-${take.id}`, async () => {
      const shot = shots.find((s) => s.id === take.shot_id);
      await projectApi.savePrompt(projectId, {
        take_id: take.id,
        prompt_en: promptFromShot(shot, take.take_number),
        explanation_es:
          'Prompt compilado en orden fijo (cap. 9): objetivo, presentador confirmado, ratio, ventana y diálogo literal.',
        constraints: [
          'Continuidad de identidad con la hoja maestra de maxDotAi',
          'Cifras nunca generadas por el modelo (gráficos programáticos)',
        ],
        checklist: { prompt_copiado: false, referencias_adjuntadas: false, importar_mp4: false },
      });
    });

  const downloadPackage = (take: TakeOut) =>
    run(`package-${take.id}`, async () => {
      const pkg = await projectApi.flowPackage(projectId, take.id);
      const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `flow_manual_package_take_${take.take_number}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    });

  const importMedia = (take: TakeOut) =>
    run(`import-${take.id}`, async () => {
      const file = selectedFile[take.id];
      if (!file) throw new Error('Selecciona antes el MP4 generado en Flow');
      await projectApi.uploadTakeMedia(projectId, take.id, file);
    });

  const loadGraphics = async () => {
    const res = await fetch(`/api/v1/projects/${projectId}/graphics`, { credentials: 'same-origin' });
    if (res.ok) setGraphics((await res.json()).items ?? []);
  };
  useEffect(() => {
    void loadGraphics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const createGraphic = () =>
    run('graphic', async () => {
      const res = await fetch(`/api/v1/projects/${projectId}/graphics`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: graphicTitle,
          chart_type: 'BAR',
          series: [{ label: graphicLabel, value: Number(graphicValue.replace(',', '.')), unit: graphicUnit }],
        }),
      });
      if (!res.ok) {
        const detail = (await res.json().catch(() => null))?.detail;
        throw new Error(typeof detail === 'string' ? detail : 'No se pudo crear el gráfico');
      }
      setGraphicValue('');
      await loadGraphics();
    });

  const approveTake = (take: TakeOut, status: 'APROBADA' | 'RECHAZADA') =>
    run(`approve-${take.id}`, async () => {
      await projectApi.approveTake(projectId, take.id, status);
    });

  return (
    <div className="space-y-4 rounded-lg border border-amber-900/60 bg-slate-900/70 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-amber-400">theaters</span>
          Producción vertical (director determinista → tomas → paquete Flow → importación)
        </h3>
        <button
          onClick={runDirector}
          disabled={busy !== null}
          className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-amber-400 disabled:opacity-50 cursor-pointer"
        >
          {busy === 'director' ? 'Planificando…' : shots.length > 0 ? 'Replanificar con el director' : 'Ejecutar director audiovisual'}
        </button>
      </div>

      {planNote && <p className="text-[11px] font-mono text-emerald-300">{planNote}</p>}
      {error && (
        <p className="rounded border border-rose-900 bg-rose-950/60 p-2 text-[11px] text-rose-200">{error}</p>
      )}

      {shots.length === 0 && (
        <p className="text-xs text-slate-400">
          Todavía no hay plan: ejecuta el director para descomponer el guion en beats y tomas.
          La locución es continua; los cortes solo responden a la capacidad del proveedor.
        </p>
      )}

      <ul className="space-y-3">
        {shots.map((shot) => {
          const take = takesByShot.get(shot.id);
          return (
            <li key={shot.id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="font-mono font-bold text-amber-300">
                  Toma {shot.sequence + 1} · {KIND_LABELS[shot.shot_kind] ?? shot.shot_kind}
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  {shot.start_s}s → {shot.end_s}s (máx. proveedor {shot.max_duration_s}s)
                </span>
              </div>
              <p className="text-[11px] text-slate-400">{shot.rationale}</p>

              {!take && (
                <p className="text-[11px] text-slate-500">Sin toma asociada; replanifica para crearla.</p>
              )}

              {take && (
                <div className="space-y-2 border-t border-slate-800 pt-2">
                  <p className="text-[11px] font-mono text-slate-300">
                    Toma #{take.id} · estado: <strong>{take.status}</strong> · prompt: v{take.prompt_versions}
                  </p>
                  <div className="flex flex-wrap gap-2 text-[11px]">
                    <button
                      onClick={() => generatePrompt(take)}
                      disabled={busy !== null}
                      className="rounded border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-50 cursor-pointer"
                    >
                      {busy === `prompt-${take.id}` ? 'Compilando…' : 'Generar prompt de la toma'}
                    </button>
                    <button
                      onClick={() => downloadPackage(take)}
                      disabled={busy !== null}
                      className="rounded border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-50 cursor-pointer"
                    >
                      {busy === `package-${take.id}` ? 'Preparando…' : 'Descargar FlowManualPackage'}
                    </button>
                    <input
                      ref={(el) => {
                        fileInputs.current[take.id] = el;
                      }}
                      type="file"
                      accept="video/mp4"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) setSelectedFile((prev) => ({ ...prev, [take.id]: file }));
                      }}
                    />
                    <button
                      onClick={() => fileInputs.current[take.id]?.click()}
                      className="rounded border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800 cursor-pointer"
                    >
                      {selectedFile[take.id]?.name ?? 'Elegir MP4 generado en Flow'}
                    </button>
                    <button
                      onClick={() => importMedia(take)}
                      disabled={busy !== null || !selectedFile[take.id]}
                      className="rounded bg-slate-800 px-2 py-1 text-slate-100 hover:bg-slate-700 disabled:opacity-50 cursor-pointer"
                    >
                      {busy === `import-${take.id}` ? 'Importando…' : 'Importar y asociar a la toma'}
                    </button>
                  </div>

                  {take.imported_media && (
                    <div className="space-y-2">
                      <p className="text-[11px] font-mono text-emerald-300">
                        MP4 importado · sha256 {take.imported_media.sha256.slice(0, 12)}… ·{' '}
                        {take.imported_media.duration_s ?? 'duración desconocida'}s ·{' '}
                        {take.imported_media.orientation ?? 'orientación desconocida'}
                      </p>
                      <video
                        controls
                        className="max-h-64 w-full rounded border border-slate-800 bg-black"
                        src={`/api/v1/media/${take.imported_media.id}/file`}
                      />
                      {take.status === 'IMPORTADA' && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => approveTake(take, 'APROBADA')}
                            disabled={busy !== null}
                            className="rounded bg-emerald-700 px-2 py-1 text-[11px] font-bold text-white hover:bg-emerald-600 disabled:opacity-50 cursor-pointer"
                          >
                            Aprobar toma
                          </button>
                          <button
                            onClick={() => approveTake(take, 'RECHAZADA')}
                            disabled={busy !== null}
                            className="rounded bg-rose-800 px-2 py-1 text-[11px] font-bold text-white hover:bg-rose-700 disabled:opacity-50 cursor-pointer"
                          >
                            Rechazar toma
                          </button>
                        </div>
                      )}
                      {take.status === 'APROBADA' && (
                        <p className="text-[11px] font-semibold text-emerald-400">
                          Toma aprobada por revisión humana.
                        </p>
                      )}
                      {take.status === 'RECHAZADA' && (
                        <p className="text-[11px] font-semibold text-rose-400">Toma rechazada.</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
      <div className="space-y-2 rounded-lg border border-sky-900/60 bg-slate-900/70 p-3">
        <h4 className="text-xs font-bold text-sky-300 flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[16px]">bar_chart</span>
          Gráficos programáticos (datos verificados, nunca inventados)
        </h4>
        <div className="flex flex-wrap items-end gap-2 text-[11px]">
          <label className="space-y-0.5">
            <span className="text-slate-500">Título</span>
            <input value={graphicTitle} onChange={(e) => setGraphicTitle(e.target.value)}
              className="block w-40 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100" />
          </label>
          <label className="space-y-0.5">
            <span className="text-slate-500">Etiqueta</span>
            <input value={graphicLabel} onChange={(e) => setGraphicLabel(e.target.value)}
              className="block w-28 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100" />
          </label>
          <label className="space-y-0.5">
            <span className="text-slate-500">Valor</span>
            <input value={graphicValue} onChange={(e) => setGraphicValue(e.target.value)} inputMode="decimal"
              className="block w-20 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100" />
          </label>
          <label className="space-y-0.5">
            <span className="text-slate-500">Unidad</span>
            <input value={graphicUnit} onChange={(e) => setGraphicUnit(e.target.value)}
              className="block w-16 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100" />
          </label>
          <button onClick={createGraphic} disabled={busy !== null || graphicValue === ''}
            className="rounded bg-sky-700 px-2 py-1 font-semibold text-white hover:bg-sky-600 disabled:opacity-50 cursor-pointer">
            {busy === 'graphic' ? 'Creando…' : 'Crear gráfico'}
          </button>
        </div>
        {graphics.length === 0 && (
          <p className="text-[10px] text-slate-500">
            Sin gráficos aún. Si el guion cambia, los gráficos derivados se marcan INVALIDADO para revisión (cap. 13).
          </p>
        )}
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {graphics.map((g) => (
            <li key={g.id} className="space-y-1">
              <p className="text-[11px] font-mono text-slate-300">
                #{g.id} {g.title} · <strong className={g.status === 'INVALIDADO' ? 'text-rose-400' : 'text-emerald-400'}>{g.status}</strong>
              </p>
              {g.status !== 'INVALIDADO' && (
                <img
                  alt={`Gráfico ${g.title}`}
                  className="w-full rounded border border-slate-800"
                  src={`/api/v1/projects/${projectId}/graphics/${g.id}/svg`}
                />
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
