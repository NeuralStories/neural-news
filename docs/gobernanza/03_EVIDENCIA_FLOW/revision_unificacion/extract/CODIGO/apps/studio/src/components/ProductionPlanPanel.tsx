import React, { useMemo, useState } from 'react';
import type { NewsArticle } from '../studio/types';
import {
  NEURALNEWS_CANON_PROFILE,
  findProfile,
} from '../data/avProfiles';
import {
  type ProductionProject,
  applySceneEdit,
  checkConsistency,
  createProductionProject,
  exportProjectJson,
  loadProjectVersions,
  saveProjectVersion,
  totalEstimatedSeconds,
} from '../lib/productionProject';
import {
  type RenderSummary,
  ApiError,
  ApiNotReachableError,
  downloadRender,
  listRenders,
  pollJobUntilSettled,
  requestRender,
} from '../lib/apiClient';

interface ProductionPlanPanelProps {
  article?: NewsArticle;
}

/**
 * Previsualización del plan de producción audiovisual (T412): convierte la
 * noticia activa en un proyecto con escenas editables, prompts por tipo de
 * escena, encuadres y transiciones del perfil canon, versiones guardadas y
 * verificación de consistencia. No genera imagen, vídeo ni voz.
 */
export const ProductionPlanPanel: React.FC<ProductionPlanPanelProps> = ({ article }) => {
  const [project, setProject] = useState<ProductionProject | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [renderPhase, setRenderPhase] = useState<
    { phase: 'idle' } | { phase: 'working'; message: string } | { phase: 'ready'; render: RenderSummary } | { phase: 'error'; message: string }
  >({ phase: 'idle' });

  const profile = useMemo(() => findProfile('neuralnews-canon-v1') ?? NEURALNEWS_CANON_PROFILE, []);

  const handleCreate = () => {
    if (!article) return;
    setProject(createProductionProject(article, profile, { outputFormat: '9:16' }));
    setFeedback(null);
  };

  const consistency = useMemo(
    () => (project ? checkConsistency(project, profile) : null),
    [project, profile]
  );
  const versions = useMemo(
    () => (project ? loadProjectVersions(project.projectId) : []),
    [project]
  );

  const handleSaveVersion = () => {
    if (!project) return;
    saveProjectVersion(project);
    setFeedback(`Versión ${project.planVersion} del plan guardada.`);
  };

  const handleDownload = () => {
    if (!project) return;
    const blob = new Blob([exportProjectJson(project)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${project.projectId}-v${project.planVersion}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  /** Composición con el motor local: encola el plan y espera el vídeo (T608 integrado). */
  const handleRender = async () => {
    if (!project) return;
    setRenderPhase({ phase: 'working', message: 'Enviando el plan al motor editorial…' });
    try {
      const info = await requestRender(JSON.parse(exportProjectJson(project)));
      setRenderPhase({
        phase: 'working',
        message: info.created
          ? 'Composición en cola; esperando al motor local…'
          : 'Este plan ya estaba en cola; esperando al motor local…',
      });
      const job = await pollJobUntilSettled(info.job_id, {
        onTick: (status) =>
          setRenderPhase({ phase: 'working', message: `Estado del trabajo: ${status}…` }),
      });
      if (job.status !== 'DONE') {
        setRenderPhase({
          phase: 'error',
          message: job.error || 'La composición terminó con error; revisa el detalle del trabajo.',
        });
        return;
      }
      const renders = await listRenders(project.projectId);
      const render = renders.items.find((item) => item.job_id === info.job_id) ?? renders.items[0];
      setRenderPhase({ phase: 'ready', render });
    } catch (err) {
      const message =
        err instanceof ApiNotReachableError || err instanceof ApiError
          ? err.message
          : 'No se pudo completar la composición.';
      setRenderPhase({ phase: 'error', message });
    }
  };

  const handleDownloadVideo = async () => {
    if (renderPhase.phase !== 'ready') return;
    const render = renderPhase.render;
    try {
      await downloadRender(
        render.render_id,
        `neuralstories-${render.project_id}-${render.output_format.replace(':', 'x')}.mp4`
      );
    } catch (err) {
      setRenderPhase({
        phase: 'error',
        message: err instanceof ApiError ? err.message : 'No se pudo descargar el vídeo.',
      });
    }
  };

  if (!article) {
    return (
      <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-xs text-slate-400">
        Activa una noticia aprobada en la pestaña «1. Noticias» (botón «Producir en Vídeo») para
        crear su plan de producción audiovisual.
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-cyan-700/60 bg-slate-900/70 p-4 space-y-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-cyan-400">theater_comedy</span>
          <h2 className="text-sm font-semibold text-cyan-200">Plan de producción audiovisual</h2>
        </div>
        {project ? (
          <span className="text-[11px] text-slate-400">
            {project.projectId} · perfil {project.profileId} v{project.profileVersion} · plan v{project.planVersion} ·{' '}
            {project.scenes.length} escena(s) · ~{totalEstimatedSeconds(project)} s
          </span>
        ) : null}
      </header>

      {!project ? (
        <div className="space-y-2">
          <p className="text-xs text-slate-400">
            Se creará un proyecto con el perfil canon <strong>{profile.profileId}</strong> (personaje{' '}
            {profile.character.displayName}, plató CRT, voz {profile.voice.profile}), dividiendo el
            guion en escenas de ~8 segundos con prompt, encuadre y transición por escena.
          </p>
          <button
            type="button"
            onClick={handleCreate}
            className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-500"
          >
            Crear plan para «{article.title.slice(0, 40)}…»
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {consistency && consistency.warnings.length > 0 && (
            <div className="rounded border border-amber-800 bg-amber-950/60 p-3 text-xs text-amber-200">
              <p className="font-semibold">Revisa la consistencia del plan:</p>
              <ul className="mt-1 list-disc pl-4">
                {consistency.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {project.scenes.map((scene) => (
            <div key={scene.sceneIndex} className="rounded border border-slate-700 bg-slate-950/60 p-3 space-y-2">
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                <span className="rounded bg-cyan-900/60 px-2 py-0.5 font-semibold text-cyan-200">
                  Escena {scene.sceneIndex} · {scene.sceneType}
                </span>
                <span>~{scene.estDurationSeconds} s</span>
                <span>· transición: {scene.transition}</span>
                <span>· movimiento: {scene.movement}</span>
              </div>
              <label className="block text-[11px] text-slate-400">
                Locución de la escena
                <textarea
                  value={scene.scriptSnippet}
                  onChange={(event) =>
                    setProject((prev) =>
                      prev
                        ? applySceneEdit(prev, scene.sceneIndex, { scriptSnippet: event.target.value })
                        : prev
                    )
                  }
                  rows={2}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950/80 p-2 text-xs text-slate-200 focus:border-cyan-600 focus:outline-none"
                />
              </label>
              <label className="block text-[11px] text-slate-400">
                Prompt de imagen (editable)
                <textarea
                  value={scene.imagePrompt}
                  onChange={(event) =>
                    setProject((prev) =>
                      prev ? applySceneEdit(prev, scene.sceneIndex, { imagePrompt: event.target.value }) : prev
                    )
                  }
                  rows={3}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-950/80 p-2 font-mono text-[11px] text-slate-200 focus:border-cyan-600 focus:outline-none"
                />
              </label>
            </div>
          ))}

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleSaveVersion}
              className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-500"
            >
              Guardar versión del plan
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="rounded border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-cyan-600"
            >
              Descargar plan (JSON)
            </button>
            {versions.length > 0 && (
              <span className="text-[11px] text-slate-400">
                Versiones guardadas: {versions.map((v) => `v${v.planVersion}`).join(', ')}
              </span>
            )}
          </div>
          {feedback && <p className="text-xs text-emerald-300">{feedback}</p>}

          <div className="rounded border border-slate-700 bg-slate-950/60 p-3 space-y-2">
            <p className="text-[11px] font-semibold text-slate-300">Componer el vídeo (motor local, activos simulados)</p>
            {renderPhase.phase === 'idle' && (
              <button
                type="button"
                onClick={handleRender}
                className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-emerald-500"
              >
                Enviar a componer con FFmpeg
              </button>
            )}
            {renderPhase.phase === 'working' && (
              <p className="text-xs text-amber-200">⏳ {renderPhase.message}</p>
            )}
            {renderPhase.phase === 'ready' && (
              <div className="space-y-1">
                <p className="text-xs text-emerald-300">
                  Vídeo listo: {renderPhase.render.output_format} · {renderPhase.render.duration_s.toFixed(1)} s ·{' '}
                  {renderPhase.render.scene_count} escena(s) · sha256 {renderPhase.render.sha256.slice(0, 12)}…
                </p>
                <button
                  type="button"
                  onClick={handleDownloadVideo}
                  className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-emerald-500"
                >
                  Descargar vídeo (MP4)
                </button>
                <button
                  type="button"
                  onClick={handleRender}
                  className="ml-2 rounded border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-emerald-600"
                >
                  Volver a componer
                </button>
              </div>
            )}
            {renderPhase.phase === 'error' && (
              <div className="rounded border border-rose-800 bg-rose-950/70 p-3 text-xs text-rose-200">
                <p>{renderPhase.message}</p>
                <button
                  type="button"
                  onClick={handleRender}
                  className="mt-2 rounded border border-rose-700 px-3 py-1 text-[11px] text-rose-100 hover:border-rose-400"
                >
                  Intentar de nuevo
                </button>
              </div>
            )}
          </div>

          <p className="text-[11px] text-slate-500">
            Voz: {project.voice.profile} ({project.voice.locale}) · {project.voice.speedNote} Este plan no
            genera imagen, vídeo ni voz: es la previsualización editable de la producción.
          </p>
        </div>
      )}
    </section>
  );
};
