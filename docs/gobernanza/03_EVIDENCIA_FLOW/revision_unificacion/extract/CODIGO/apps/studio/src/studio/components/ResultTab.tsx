import React, { useState } from 'react';
import { 
  MasterSheetState, 
  BackgroundPreset, 
  VoiceConfig, 
  CameraMovement, 
  VisualReferenceItem, 
  MultiSceneScriptAnalysis, 
  SceneProductionPlan, 
  NewsArticle 
} from '../types';

interface ResultTabProps {
  finalPrompt: string;
  onCopyPrompt: () => Promise<void>;
  onGenerateVideo: (promptToUse?: string) => Promise<void>;
  isGeneratingVideo: boolean;
  generatedVideoBase64?: string;
  generatedVideoMime?: string;
  sheetState: MasterSheetState;
  selectedBackground: BackgroundPreset;
  aspectRatio: '16:9' | '9:16';
  voiceConfig: VoiceConfig;
  activeMovements: CameraMovement[];
  multiSceneAnalysis: MultiSceneScriptAnalysis;
  selectedReferences: VisualReferenceItem[];
  activeArticle?: NewsArticle;
  onExportProductionPackage: () => Promise<void>;
}

export const ResultTab: React.FC<ResultTabProps> = ({
  finalPrompt,
  onCopyPrompt,
  onGenerateVideo,
  isGeneratingVideo,
  generatedVideoBase64,
  generatedVideoMime,
  sheetState,
  selectedBackground,
  aspectRatio,
  voiceConfig,
  activeMovements,
  multiSceneAnalysis,
  selectedReferences,
  activeArticle,
  onExportProductionPackage,
}) => {
  const [copied, setCopied] = useState(false);
  const [selectedSceneIndex, setSelectedSceneIndex] = useState(0);
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
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
          <span className="text-[10px] uppercase font-mono text-slate-500 block">Noticia Editorial</span>
          <span className="text-xs font-semibold text-white flex items-center gap-1 mt-1 truncate" title={activeArticle?.title}>
            <span className="material-symbols-outlined text-[14px] text-amber-400">newspaper</span>
            {activeArticle ? activeArticle.title : 'Guion Manual'}
          </span>
        </div>
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
          <span className="text-[10px] uppercase font-mono text-slate-500 block">Escenario & Ratio</span>
          <span className="text-xs font-semibold text-white flex items-center gap-1 mt-1">
            <span className="material-symbols-outlined text-[14px] text-amber-400">tv</span>
            CRT {aspectRatio}
          </span>
        </div>
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
          <span className="text-[10px] uppercase font-mono text-slate-500 block">Voz Algenib</span>
          <span className="text-xs font-semibold text-white flex items-center gap-1 mt-1">
            <span className="material-symbols-outlined text-[14px] text-amber-400">mic</span>
            {voiceConfig.speedMultiplier.toFixed(2)}x (+18%)
          </span>
        </div>
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
          <span className="text-[10px] uppercase font-mono text-slate-500 block">Refs Canónicas</span>
          <span className="text-xs font-semibold text-amber-400 flex items-center gap-1 mt-1 font-mono">
            <span className="material-symbols-outlined text-[14px]">collections</span>
            {selectedReferences.length} activas
          </span>
        </div>
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 col-span-2 sm:col-span-1">
          <span className="text-[10px] uppercase font-mono text-slate-500 block">Escenas Generables</span>
          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1 mt-1 font-mono">
            <span className="material-symbols-outlined text-[14px]">movie</span>
            {multiSceneAnalysis.scenes.length || 1} tomas (8s c/u)
          </span>
        </div>
      </div>

      {/* Auditoría de Referencias Transmitidas a Google Flow */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2 mb-2">
          <span className="material-symbols-outlined text-[16px] text-amber-400">verified</span>
          Auditoría de Insumos para Omni 1.1 Flash (Google Flow)
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded bg-slate-950 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-emerald-300 font-mono text-[11px]">
                ✓ Referencias Visuales Reales (mediaId):
              </span>
              <span className="text-[10px] font-mono text-emerald-400">
                {mediaIdRefs.length + (sheetState.mediaId ? 1 : 0)} activas
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Transmitidas a <code>Flow.generate.video()</code> en <code>referenceImageMediaIds</code>.
            </p>
            <div className="space-y-1 pt-1 font-mono text-[10px]">
              {sheetState.mediaId ? (
                <div className="text-emerald-400">
                  • Hoja Maestra @neuraldotai: ID <code>{sheetState.mediaId}</code>
                </div>
              ) : (
                <div className="text-amber-400/90">
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

          <div className="p-3 rounded bg-slate-950 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-amber-300 font-mono text-[11px]">
                ⚠ Directivas Textuales en Prompt:
              </span>
              <span className="text-[10px] font-mono text-amber-400">
                {promptOnlyRefs.length} elementos
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              No cuentan con mediaId en la galería de Flow. Su estilo e identidad se garantizan mediante el descriptor textual detallado.
            </p>
            <div className="space-y-1 pt-1 font-mono text-[10px] text-slate-400">
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
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[16px] text-amber-400">view_carousel</span>
              Secuencia de Escenas del Noticiero ({multiSceneAnalysis.scenes.length} fragmentos de 8s)
            </span>
            <button
              onClick={onExportProductionPackage}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded text-xs font-mono border border-slate-700 transition cursor-pointer flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[14px]">archive</span>
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
                    ? 'bg-amber-500 text-slate-950 font-bold shadow'
                    : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-white'
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
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] text-amber-400">code</span>
                Prompt de Toma {selectedSceneIndex + 1} (8 Segundos)
              </span>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 transition cursor-pointer"
              >
                <span className="material-symbols-outlined text-[14px]">
                  {copied ? 'check' : 'content_copy'}
                </span>
                <span>{copied ? 'Copiado al portapapeles' : 'Copiar Prompt de Toma'}</span>
              </button>
            </div>

            <textarea
              readOnly
              value={promptToRender}
              rows={8}
              className="w-full text-xs font-mono bg-slate-950 border border-slate-800 rounded p-3 text-slate-200 leading-relaxed resize-none focus:outline-none"
            />

            {/* Control de Seguridad: Autorización de Gasto de Créditos */}
            <div className="p-3 rounded bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={spendAuthorized}
                  onChange={(e) => setSpendAuthorized(e.target.checked)}
                  className="accent-amber-500 w-4 h-4 rounded cursor-pointer"
                />
                <span className="font-semibold text-amber-300">
                  Autorizo explícitamente el consumo de créditos para renderizar esta toma de 8s
                </span>
              </label>

              <span className="text-[11px] font-mono text-slate-400">
                Consumo: <strong>12 créditos</strong> (8s 720p)
              </span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
              <span className="text-[11px] text-slate-400 font-mono">
                Modelo: <strong className="text-white">Omni 1.1 Flash</strong> (T2V / R2V 8s 720p)
              </span>
              <button
                disabled={isGeneratingVideo || !spendAuthorized}
                onClick={() => onGenerateVideo(promptToRender)}
                className={`px-4 py-2 rounded-md font-bold text-xs flex items-center gap-1.5 transition cursor-pointer shadow-lg ${
                  !spendAuthorized
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed opacity-60'
                    : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 shadow-amber-500/20'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">
                  {isGeneratingVideo ? 'sync' : 'movie'}
                </span>
                <span>
                  {isGeneratingVideo 
                    ? 'Renderizando toma (1-2 min)...' 
                    : spendAuthorized 
                    ? `Ejecutar Render Toma ${selectedSceneIndex + 1} (8s)` 
                    : 'Esperando autorización de gasto'}
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Lado derecho: Monitor de reproducción de vídeo */}
        <div className="lg:col-span-5 space-y-3">
          <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider block">
            Monitor de Emisión
          </span>

          <div
            className={`w-full rounded-lg border-2 border-slate-800 bg-slate-950 overflow-hidden flex items-center justify-center relative shadow-inner ${
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
                <span className="material-symbols-outlined text-[36px] text-slate-600 block mb-2">
                  videocam_off
                </span>
                <p className="text-xs font-medium text-slate-300">Toma de 8s lista para producción</p>
                <p className="text-[11px] text-slate-500 mt-1 max-w-xs leading-relaxed">
                  El paquete está compilado con el personaje @neuraldotai, el plató CRT y el guion editorial de 8s. Activa la autorización de gasto para lanzar la llamada a Omni 1.1 Flash.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};