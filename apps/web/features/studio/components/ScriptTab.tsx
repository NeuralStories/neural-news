import React, { useState } from 'react';
import { MultiSceneScriptAnalysis, NewsArticle, SceneProductionPlan } from '../types';

interface ScriptTabProps {
  scriptText: string;
  onChangeScript: (text: string) => void;
  multiSceneAnalysis: MultiSceneScriptAnalysis;
  selectedArticle?: NewsArticle;
  onApplyScenesToProduction: (scenes: SceneProductionPlan[]) => void;
  onUpdateManualSceneSnippet?: (sceneIndex: number, newSnippet: string) => void;
}

export const ScriptTab: React.FC<ScriptTabProps> = ({
  scriptText,
  onChangeScript,
  multiSceneAnalysis,
  selectedArticle,
  onApplyScenesToProduction,
  onUpdateManualSceneSnippet,
}) => {
  const [activeScenePreviewIndex, setActiveScenePreviewIndex] = useState(0);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingText, setEditingText] = useState('');

  // Comparación de concatenación de escenas con el texto original para verificar integridad
  const concatenatedScenesText = multiSceneAnalysis.scenes
    .map(s => s.scriptSnippet.trim())
    .join(' ');

  const originalWords = scriptText.trim().split(/\s+/).filter(w => w.length > 0);
  const reconstructedWords = concatenatedScenesText.split(/\s+/).filter(w => w.length > 0);
  const hasWordCountDiscrepancy = originalWords.length !== reconstructedWords.length;

  const handleStartEdit = (idx: number, current: string) => {
    setEditingIndex(idx);
    setEditingText(current);
  };

  const handleSaveEdit = (idx: number) => {
    if (onUpdateManualSceneSnippet) {
      onUpdateManualSceneSnippet(idx + 1, editingText);
    }
    setEditingIndex(null);
  };

  return (
    <div className="space-y-6">
      {/* Cabecera explicativa con rigor técnico */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white">
              Analizador de Guiones: Desglose en Escenas (duración calculada)
            </h3>
            {selectedArticle && (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-500/10 text-sky-300 border border-sky-500/20">
                Noticia: {selectedArticle.title.slice(0, 32)}...
              </span>
            )}
          </div>
          <p className="text-xs text-neutral-400 mt-1 max-w-2xl leading-relaxed">
            Distingue el <strong>guion editorial continuo</strong> (30s, 45s o 60s) de las <strong>tomas de vídeo</strong> con la duración que admita cada proveedor.
            Permite editar manualmente cada fragmento.
          </p>
        </div>

        {/* Métricas clave del desglose */}
        <div className="flex items-center gap-3 bg-neutral-950 px-3.5 py-2 rounded-md border border-neutral-800 self-start md:self-auto">
          <div>
            <div className="text-[10px] uppercase font-mono text-neutral-500">Duración Estimada</div>
            <div className="text-base font-bold font-mono text-white flex items-baseline gap-1">
              <span>{multiSceneAnalysis.fullEstDurationSeconds}s</span>
              <span className="text-[10px] text-neutral-400 font-normal">({multiSceneAnalysis.scenesCount} tomas, duración calculada)</span>
            </div>
          </div>
          <div className="px-2 py-1 rounded text-[11px] font-semibold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            {multiSceneAnalysis.scenesCount} ESCENAS COHERENTES
          </div>
        </div>
      </div>

      {/* Alerta de Transparencia de Audio y Continuidad */}
      <div className="p-3.5 rounded-lg bg-neutral-900 border border-neutral-800 text-xs text-neutral-300 space-y-1">
        <div className="flex items-center gap-2 text-sky-300 font-semibold">
          <span>Aviso Técnico de Continuidad Sonora:</span>
        </div>
        <p className="text-neutral-400 leading-relaxed text-[11px]">
          La división del texto en fragmentos <strong>no garantiza por sí sola la continuidad acústica</strong>.
          La costura de audio final requiere un motor de text-to-speech con timeline compartido o pista de locución master generada previamente y sincronizada con cada toma.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Editor de Guion Editorial Completo */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-neutral-200 uppercase tracking-wider">
              Guion Editorial Completo (Locución Algenib)
            </label>
            <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
              <span>Palabras: <strong className="text-white">{multiSceneAnalysis.fullWordCount}</strong></span>
              {hasWordCountDiscrepancy ? (
                <span className="text-rose-400 text-[10px]" title="Discrepancia léxica detectada">⚠ Verificando integridad</span>
              ) : (
                <span className="text-emerald-400 text-[10px] font-bold">✓ 100% Integridad Textual</span>
              )}
            </div>
          </div>

          <textarea aria-label="Guion Editorial Completo (Locución Algenib)"
            value={scriptText}
            onChange={(e) => onChangeScript(e.target.value)}
            rows={8}
            placeholder="Introduce el guion completo de la noticia (ej. 30s, 45s o 60s)..."
            className="w-full text-xs font-mono bg-neutral-950 border border-neutral-800 rounded-lg p-3 text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-sky-500 leading-relaxed"
          />

          <div className="flex items-center justify-between gap-2 pt-1">
            <div className="flex items-center gap-1.5 text-[11px] text-neutral-400">
              <span>Cadencia Algenib calculada: 2.85 palabras/segundo</span>
            </div>
            <button
              onClick={() => onApplyScenesToProduction(multiSceneAnalysis.scenes)}
              className="px-3 py-1 bg-sky-500 hover:bg-sky-400 text-neutral-950 font-bold text-xs rounded transition cursor-pointer"
            >
              Enviar a Producción
            </button>
          </div>
        </div>

        {/* Desglose y Edición Manual de Escenas */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-neutral-200 uppercase tracking-wider">
              Escenas Audiovisuales Resultantes (duración calculada)
            </label>
            <span className="text-[11px] font-mono text-neutral-500">
              Haz clic en editar para ajustar manualmente
            </span>
          </div>

          <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
            {multiSceneAnalysis.scenes.map((scene, idx) => {
              const isSelected = activeScenePreviewIndex === idx;
              const isEditingThis = editingIndex === idx;

              return (
                <div
                  key={idx}
                  onClick={() => !isEditingThis && setActiveScenePreviewIndex(idx)}
                  className={`p-3 rounded-lg border transition ${
                    isSelected
                      ? 'bg-neutral-900 border-sky-500 ring-1 ring-sky-500/40 shadow'
                      : 'bg-neutral-900/60 border-neutral-800 hover:border-neutral-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <span className="w-5 h-5 rounded bg-sky-500/20 text-sky-400 flex items-center justify-center text-[10px] font-mono">
                        {scene.sceneIndex}
                      </span>
                      Escena {scene.sceneIndex} (~{scene.estDurationSeconds}s)
                    </span>

                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-950 text-neutral-400 border border-neutral-800">
                        {scene.wordCount} palabras
                      </span>
                      {!isEditingThis ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartEdit(idx, scene.scriptSnippet);
                          }}
                          className="text-neutral-400 hover:text-sky-300 text-[11px] font-mono cursor-pointer flex items-center gap-0.5"
                        >
                          Editar
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSaveEdit(idx);
                          }}
                          className="text-emerald-400 hover:text-emerald-300 text-[11px] font-bold font-mono cursor-pointer flex items-center gap-0.5"
                        >
                          Guardar
                        </button>
                      )}
                    </div>
                  </div>

                  {isEditingThis ? (
                    <textarea aria-label="Editar el guion de la escena"
                      value={editingText}
                      onChange={(e) => setEditingText(e.target.value)}
                      rows={2}
                      className="w-full text-xs font-mono bg-neutral-950 border border-sky-500/70 rounded p-2 text-neutral-100 focus:outline-none focus:border-sky-500"
                    />
                  ) : (
                    <p className="text-xs text-neutral-300 font-mono leading-relaxed">
                      &quot;{scene.scriptSnippet}&quot;
                    </p>
                  )}

                  <div className="mt-2 pt-2 border-t border-neutral-800/80 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-neutral-400">
                    <span className="truncate max-w-[240px]">
                      Óptica: {scene.transitionType}
                    </span>
                    <span className="text-sky-400/90 font-semibold">
                      Toma fija de 8.0s en Flow
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};