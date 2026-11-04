import React, { useState } from 'react';
import {
  MasterSheetState,
  VoiceConfig,
  VisualReferenceItem,
  MultiSceneScriptAnalysis,
  SceneProductionPlan,
  NewsArticle 
} from '../types';

interface ResultTabProps {
  finalPrompt: string;
  onGenerateVideo: (promptToUse?: string) => Promise<void>;
  isGeneratingVideo: boolean;
  generatedVideoBase64?: string;
  generatedVideoMime?: string;
  sheetState: MasterSheetState;
  aspectRatio: '16:9' | '9:16';
  voiceConfig: VoiceConfig;
  multiSceneAnalysis: MultiSceneScriptAnalysis;
  selectedReferences: VisualReferenceItem[];
  activeArticle?: NewsArticle;
  onExportProductionPackage: () => Promise<void>;
  /** Runtime de Flow disponible (solo dentro del editor); fuera, render = BLOCKED. */
  flowHosted?: boolean;
  /**
   * Toma seleccionada en el paso Resultado. Se controla desde el Studio para que
   * el paso se persista y sobreviva a una recarga (hallazgo B3: el paso
   * «resultado» era el único de los ocho que no se guardaba).
   */
  selectedSceneIndex?: number;
  onSelectSceneIndex?: (index: number) => void;
}

export const ResultTab: React.FC<ResultTabProps> = ({
  finalPrompt,
  onGenerateVideo,
  isGeneratingVideo,
  generatedVideoBase64,
  generatedVideoMime,
  sheetState,
  aspectRatio,
  voiceConfig,
  multiSceneAnalysis,
  selectedReferences,
  activeArticle,
  onExportProductionPackage,
  flowHosted = false,
  selectedSceneIndex: selectedSceneIndexProp,
  onSelectSceneIndex,
}) => {
  const [copied, setCopied] = useState(false);
  // Estado controlado desde el Studio (persistencia del paso «resultado»),
  // con valor interno como respaldo si el Studio no lo controla.
  const [internalSceneIndex, setInternalSceneIndex] = useState(0);
  const selectedSceneIndex = selectedSceneIndexProp ?? internalSceneIndex;
  const setSelectedSceneIndex = (index: number) => {
    setInternalSceneIndex(index);
    onSelectSceneIndex?.(index);
  };
  const [spendAuthorized, setSpendAuthorized] = useState(false);

  const activeScene: SceneProductionPlan | undefined = multiSceneAnalysis.scenes[selectedSceneIndex];
  const promptToRender = activeScene?.compiledPrompt || finalPrompt;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(promptToRender);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Clasificación de referencias audiovisuales: transferibles con mediaId real vs descriptivas en prompt
  const mediaIdRefs = selectedReferences.filter(r => Boolean(r.mediaId));
  const promptOnlyRefs = selectedReferences.filter(r => !r.mediaId);

  return (
    <div className="space-y-6">
      {/* Resumen del paquete de producción */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="card-compact">
          <span className="text-[10px] uppercase font-mono text-neutral-500 block">Noticia Editorial</span>
          <span className="text-xs font-semibold text-ink flex items-center gap-1 mt-1 truncate" title={activeArticle?.title}>
            {activeArticle ? activeArticle.title : 'Guion Manual'}
          </span>
        </div>
        <div className="card-compact">
          <span className="text-[10px] uppercase font-mono text-neutral-500 block">Escenario & Ratio</span>
          <span className="text-xs font-semibold text-ink flex items-center gap-1 mt-1">
            CRT {aspectRatio}
          </span>
        </div>
        <div className="card-compact">
          <span className="text-[10px] uppercase font-mono text-neutral-500 block">Voz Algenib</span>
          <span className="text-xs font-semibold text-ink flex items-center gap-1 mt-1">
            {voiceConfig.speedMultiplier.toFixed(2)}x (+18%)
          </span>
        </div>
        <div className="card-compact">
          <span className="text-[10px] uppercase font-mono text-neutral-500 block">Refs Canónicas</span>
          <span className="text-xs font-semibold text-sky-400 flex items-center gap-1 mt-1 font-mono">
            {selectedReferences.length} activas
          </span>
        </div>
        <div className="card-compact col-span-2 sm:col-span-1">
          <span className="text-[10px] uppercase font-mono text-neutral-500 block">Escenas Generables</span>
          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1 mt-1 font-mono">
            {multiSceneAnalysis.scenes.length || 1} tomas (≈{multiSceneAnalysis.scenes.length > 0 ? Math.round(multiSceneAnalysis.scenes.reduce((acc, sc) => acc + sc.estDurationSeconds, 0) / multiSceneAnalysis.scenes.length * 10) / 10 : 0}s c/u)
          </span>
        </div>
      </div>

      {/* Auditoría de Referencias Transmitidas a Google Flow */}
      <div className="card">
        <h4 className="text-xs font-bold text-ink uppercase tracking-wider flex items-center gap-2 mb-2">
          Auditoría de Insumos para Omni 1.1 Flash (Google Flow)
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded bg-neutral-950 border border-neutral-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-emerald-300 font-mono text-[11px]">
                Referencias Visuales Reales (mediaId):
              </span>
              <span className="text-[10px] font-mono text-emerald-400">
                {mediaIdRefs.length + (sheetState.mediaId ? 1 : 0)} activas
              </span>
            </div>
            <p className="text-[11px] text-neutral-400 leading-relaxed">
              Transmitidas a <code>Flow.generate.video()</code> en <code>referenceImageMediaIds</code>.
            </p>
            <div className="space-y-1 pt-1 font-mono text-[10px]">
              {sheetState.mediaId ? (
                <div className="text-emerald-400">
                  • Hoja Maestra maxDotAi: ID <code>{sheetState.mediaId}</code>
                </div>
              ) : (
                <div className="text-sky-400/90">
                  • Hoja Maestra: Sin mediaId de galería (se usa descripción de prompt)
                </div>
              )}
              {mediaIdRefs.map(r => (
                <div key={r.id} className="text-emerald-400 truncate">
                  • [{r.identifier}] {r.name}: ID <code>{r.mediaId}</code>
                </div>
              ))}
            </div>
          </div>

          <div className="p-3 rounded bg-neutral-950 border border-neutral-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sky-300 font-mono text-[11px]">
                Directivas Textuales en Prompt:
              </span>
              <span className="text-[10px] font-mono text-sky-400">
                {promptOnlyRefs.length} elementos
              </span>
            </div>
            <p className="text-[11px] text-neutral-400 leading-relaxed">
              No cuentan con mediaId en la galería de Flow. Su estilo e identidad se garantizan mediante el descriptor textual detallado.
            </p>
            <div className="space-y-1 pt-1 font-mono text-[10px] text-neutral-400">
              {promptOnlyRefs.map(r => (
                <div key={r.id} className="truncate">
                  • [{r.identifier}] {r.name} (Directriz prompt)
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Selector de Escenas Audiovisuales para render */}
      {multiSceneAnalysis.scenes.length > 1 && (
        <div className="card-compact">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-ink flex items-center gap-1.5">
              Secuencia de Escenas del Noticiero ({multiSceneAnalysis.scenes.length} fragmentos, duración calculada por palabras)
            </span>
            <button
              onClick={onExportProductionPackage}
              className="px-2.5 py-1 bg-neutral-800 hover:bg-neutral-700 text-sky-400 rounded text-xs font-mono border border-neutral-700 transition cursor-pointer flex items-center gap-1"
            >
              Descargar Paquete de Producción JSON
            </button>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {multiSceneAnalysis.scenes.map((s, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedSceneIndex(idx)}
                className={`px-3 py-1.5 rounded-md text-xs font-mono transition cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                  selectedSceneIndex === idx
                    ? 'bg-sky-500 text-neutral-950 font-bold shadow'
                    : 'bg-neutral-950 text-neutral-400 border border-neutral-800 hover:text-ink'
                }`}
              >
                <span>Toma {s.sceneIndex}</span>
                <span className="text-[10px] opacity-80">({s.estDurationSeconds}s)</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Visor de vídeo o prompt */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Lado izquierdo: Prompt de la toma seleccionada */}
        <div className="lg:col-span-7 space-y-4">
          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-neutral-200 uppercase tracking-wider flex items-center gap-1.5">
                Prompt de Toma {selectedSceneIndex + 1} (duración calculada)
              </span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-3 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs rounded border border-neutral-700 transition cursor-pointer"
              >
                <span>{copied ? 'Copiado al portapapeles' : 'Copiar Prompt de Toma'}</span>
              </button>
            </div>

            <textarea
              readOnly
              value={promptToRender}
              rows={8}
              className="w-full text-xs font-mono bg-neutral-950 border border-neutral-800 rounded p-3 text-neutral-200 leading-relaxed resize-none focus:outline-none focus:border-sky-600"
            />

            {!flowHosted && (
              <div className="p-3 rounded bg-sky-950/70 border border-sky-800 text-sky-200 text-xs space-y-1">
                <p className="font-semibold flex items-center gap-1.5">
                  BLOCKED — generación de vídeo no disponible fuera del editor de Flow
                </p>
                <p>
                  El prompt de esta toma está listo y es reproducible. Copia el prompt, genera la
                  toma en Google Flow e importa el MP4 resultante: quedará asociado a esta toma y a
                  su revisión. La generación no se simula ni se automatiza sin autorización.
                </p>
              </div>
            )}
            {/* Control de Seguridad: Autorización de Gasto de Créditos (solo con runtime hosted) */}
            <div className={`p-3 rounded bg-neutral-950 border border-neutral-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${flowHosted ? '' : 'hidden'}`}>
              <label className="flex items-center gap-2 text-neutral-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={spendAuthorized}
                  onChange={(e) => setSpendAuthorized(e.target.checked)}
                  className="accent-sky-500 w-4 h-4 rounded cursor-pointer"
                />
                <span className="font-semibold text-sky-300">
                  Autorizo explícitamente el consumo de créditos para renderizar esta toma (duración calculada)
                </span>
              </label>

              <span className="text-[11px] font-mono text-neutral-400">
                Consumo estimado: <strong>según proveedor</strong> (720p, duración de la toma)
              </span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
              <span className="text-[11px] text-neutral-400 font-mono">
                Modelo: <strong className="text-ink">Omni 1.1 Flash</strong> (T2V / R2V 720p, duración según capacidad del proveedor)
              </span>
              <button
                disabled={isGeneratingVideo || !spendAuthorized}
                onClick={() => onGenerateVideo(promptToRender)}
                className={`px-4 py-2 rounded-md font-bold text-xs flex items-center gap-1.5 transition cursor-pointer shadow-sm ${
                  !spendAuthorized
                    ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed opacity-60'
                    : 'bg-info/20 text-info hover:bg-info/30 text-neutral-950 shadow-sky-500/20'
                }`}
              >
                <span>
                  {isGeneratingVideo 
                    ? 'Renderizando toma (1-2 min)...' 
                    : spendAuthorized 
                    ? `Ejecutar Render Toma ${selectedSceneIndex + 1}` 
                    : 'Esperando autorización de gasto'}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Lado derecho: Monitor de reproducción de vídeo */}
        <div className="lg:col-span-5 space-y-3">
          <span className="text-xs font-semibold text-neutral-200 uppercase tracking-wider block">
            Monitor de Emisión
          </span>

          <div
            className={`w-full rounded-md border-2 border-neutral-800 bg-neutral-950 overflow-hidden flex items-center justify-center relative shadow-inner ${
              aspectRatio === '9:16' ? 'aspect-[9/16] max-h-[460px] mx-auto' : 'aspect-video'
            }`}
          >
            {generatedVideoBase64 ? (
              <video
                src={`data:${generatedVideoMime || 'video/mp4'};base64,${generatedVideoBase64}`}
                controls
                autoPlay
                loop
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-6">
                <p className="text-xs font-medium text-neutral-300">Toma lista para producción</p>
                <p className="text-[11px] text-neutral-500 mt-1 max-w-xs leading-relaxed">
                  El paquete está compilado con el personaje maxDotAi, el plató CRT y el guion editorial. La generación solo se ejecuta con el runtime de Flow disponible; fuera de él, importa el MP4 generado manualmente.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};