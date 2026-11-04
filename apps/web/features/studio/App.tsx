/**
 * Studio de NeuralStories News (NN-113.13).
 *
 * Este componente es **presentación y cableado**: la lógica de negocio vive en
 * hooks con nombre propio dentro de `features/studio/lib/`:
 *
 *   - `useHidratacionStudio` — el estado guardado en el servidor manda en la primera carga;
 *   - `useGuardadoPasos`     — guardado por pasos, sin escrituras en eco;
 *   - `useNoticiasStudio`    — redacción editorial (alta, importación, traspaso a producción);
 *   - `useReferenciasStudio` — referencias audiovisuales y editoriales;
 *   - `useFlowStudio`        — galería de Flow, generación de hoja y de toma;
 *   - `usePaqueteProduccion` — exportación/importación del contrato JSON;
 *   - `usePromptFinal`       — prompt de la toma.
 *
 * Antes este fichero tenía 900 líneas y mezclaba las siete cosas.
 */
import React, { useCallback, useMemo, useRef, useState } from 'react';
import { flowRuntime } from './flow/adapter';
import { IconoCruce } from '@/components/ui/icono';
import { useStudioProject } from './lib/useStudioProject';
import { useHidratacionStudio } from './lib/useHidratacionStudio';
import { useGuardadoPasos } from './lib/useGuardadoPasos';
import { useNoticiasStudio } from './lib/useNoticiasStudio';
import { useReferenciasStudio } from './lib/useReferenciasStudio';
import { useFlowStudio } from './lib/useFlowStudio';
import { usePaqueteProduccion } from './lib/usePaqueteProduccion';
import { usePromptFinal } from './lib/usePromptFinal';
import {
  MasterSheetState,
  BackgroundPreset,
  CameraMovement,
  VisualReferenceItem,
  EditorialReferenceItem,
  NewsArticle,
  ProductionEpisodeBlock,
  StudioTab,
} from './types';
import {
  BACKGROUND_PRESETS,
  ALGENIB_VOICE_CONFIG,
  CAMERA_MOVEMENTS_CATALOG,
  INITIAL_VISUAL_REFERENCES,
  INITIAL_EDITORIAL_REFERENCES,
  INITIAL_NEWS_ARTICLES,
  INITIAL_EPISODE_BLOCKS,
} from './constants';
import { splitScriptIntoScenes } from './utils/scriptAnalyzer';
import { ProductionVertical } from './components/ProductionVertical';
import { DossierPanel } from './components/DossierPanel';
import { TopNavigation } from './components/TopNavigation';
import { NewsEditorialTab } from './components/NewsEditorialTab';
import { CharacterSheetTab } from './components/CharacterSheetTab';
import { BackgroundTab } from './components/BackgroundTab';
import { ScriptTab } from './components/ScriptTab';
import { VoiceTab } from './components/VoiceTab';
import { MovementTab } from './components/MovementTab';
import { ReferencesTab } from './components/ReferencesTab';
import { ResultTab } from './components/ResultTab';
import { BackupModal } from './components/BackupModal';

export default function App({ projectId }: { projectId: number | null }) {
  const [currentTab, setCurrentTab] = useState<StudioTab>('noticias');

  // Persistencia real (F1): el estado vive en la base de datos vía API; sin localStorage.
  const { project, loading: projectLoading, loadError: projectLoadError, saveStates, saveStep, reload } =
    useStudioProject(projectId);
  const savedSnapshotsRef = useRef<Record<string, string>>({});
  /** Modo integrado en neural.news (?embed=1): el shell externo aporta identidad y navegación global. */
  const [embedded] = useState(() => {
    try {
      return new URLSearchParams(window.location.search).get('embed') === '1';
    } catch {
      return false;
    }
  });

  /** Cambio de pestaña; en modo integrado avisa al shell de neural.news. */
  const handleSelectTab = useCallback(
    (tab: StudioTab) => {
      setCurrentTab(tab);
      if (embedded) {
        try {
          window.parent?.postMessage({ type: 'nn-studio-tab', tab: String(tab) }, '*');
        } catch {
          /* sin contenedor */
        }
      }
    },
    [embedded],
  );

  // MÓDULO 1: SISTEMA EDITORIAL DE NOTICIAS (neural.news)
  const [articles, setArticles] = useState<NewsArticle[]>(INITIAL_NEWS_ARTICLES);
  const [episodeBlocks, setEpisodeBlocks] = useState<ProductionEpisodeBlock[]>(INITIAL_EPISODE_BLOCKS);
  const [activeArticleId, setActiveArticleId] = useState<string>(INITIAL_NEWS_ARTICLES[0].id);

  // MÓDULO 2: PERSONAJE (@maxDotAi)
  const [sheetState, setSheetState] = useState<MasterSheetState>({
    isApproved: true,
    notes: 'Hoja de tres paneles canónica para NeuralStories News',
  });
  const [isGeneratingSheet, setIsGeneratingSheet] = useState(false);

  // MÓDULO 3: ESCENARIO CRT
  const [selectedBackground, setSelectedBackground] = useState<BackgroundPreset>(BACKGROUND_PRESETS[0]);
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16'>('16:9');
  const [customBgMediaId, setCustomBgMediaId] = useState<string | undefined>(undefined);

  // MÓDULO 4: GUION EDITORIAL Y DESPIECE MULTI-ESCENA
  const [scriptText, setScriptText] = useState<string>(INITIAL_NEWS_ARTICLES[0].fullScript);

  // MÓDULO 5: VOZ ALGENIB
  const [voiceSpeed, setVoiceSpeed] = useState<number>(ALGENIB_VOICE_CONFIG.speedMultiplier);

  // MÓDULO 6: MOVIMIENTO Y DINAMISMO (8s)
  const [movements, setMovements] = useState<CameraMovement[]>(CAMERA_MOVEMENTS_CATALOG);

  // MÓDULO 7: BIBLIOTECA DE REFERENCIAS (AUDIOVISUALES vs EDITORIALES)
  const [visualReferences, setVisualReferences] = useState<VisualReferenceItem[]>(INITIAL_VISUAL_REFERENCES);
  const [editorialReferences, setEditorialReferences] = useState<EditorialReferenceItem[]>(INITIAL_EDITORIAL_REFERENCES);

  // MÓDULO 8: PRODUCCIÓN Y RENDERIZADO
  const [isExporting, setIsExporting] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoResult, setVideoResult] = useState<{ base64?: string; mimeType?: string } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  // Toma seleccionada en el paso Resultado: es el estado propio de ese paso y
  // se persiste con él (antes el paso «resultado» no se guardaba: hallazgo B3).
  const [resultSceneIndex, setResultSceneIndex] = useState(0);

  // Hidratación: el estado guardado en el servidor manda en la primera carga.
  const aplicarHidratacion = useCallback(
    (valores: {
      articles: NewsArticle[];
      episodeBlocks: ProductionEpisodeBlock[];
      activeArticleId: string;
      sheetState: MasterSheetState;
      selectedBackground: BackgroundPreset;
      aspectRatio: '16:9' | '9:16';
      customBgMediaId: string | undefined;
      scriptText: string;
      voiceSpeed: number;
      movements: CameraMovement[];
      visualReferences: VisualReferenceItem[];
      editorialReferences: EditorialReferenceItem[];
      resultSceneIndex: number;
    }) => {
      setArticles(valores.articles);
      setEpisodeBlocks(valores.episodeBlocks);
      setActiveArticleId(valores.activeArticleId);
      setSheetState(valores.sheetState);
      setSelectedBackground(valores.selectedBackground);
      setAspectRatio(valores.aspectRatio);
      setCustomBgMediaId(valores.customBgMediaId);
      setScriptText(valores.scriptText);
      setVoiceSpeed(valores.voiceSpeed);
      setMovements(valores.movements);
      setVisualReferences(valores.visualReferences);
      setEditorialReferences(valores.editorialReferences);
      setResultSceneIndex(valores.resultSceneIndex);
    },
    [],
  );

  const hydrated = useHidratacionStudio({
    project,
    valores: {
      articles,
      episodeBlocks,
      activeArticleId,
      sheetState,
      selectedBackground,
      aspectRatio,
      customBgMediaId,
      scriptText,
      voiceSpeed,
      movements,
      visualReferences,
      editorialReferences,
      resultSceneIndex,
    },
    aplicar: aplicarHidratacion,
    instantaneas: savedSnapshotsRef,
  });

  // Guardado por pasos: sólo se escribe lo que ha cambiado de verdad.
  const payloads = useMemo(
    () => ({
      noticias: { articles, episodeBlocks, activeArticleId },
      personaje: { sheetState },
      fondo: { selectedBackgroundId: selectedBackground.id, aspectRatio, customBgMediaId },
      guion: { scriptText },
      voz: { voiceSpeed },
      movimiento: { selectedMovementIds: movements.filter((m) => m.selected).map((m) => m.id) },
      referencias: { visualReferences, editorialReferences },
      resultado: { selectedSceneIndex: resultSceneIndex },
    }),
    [
      articles,
      episodeBlocks,
      activeArticleId,
      sheetState,
      selectedBackground,
      aspectRatio,
      customBgMediaId,
      scriptText,
      voiceSpeed,
      movements,
      visualReferences,
      editorialReferences,
      resultSceneIndex,
    ],
  );

  useGuardadoPasos({
    hydrated,
    saveStep,
    instantaneas: savedSnapshotsRef,
    payloads,
  });

  // Noticia activa actual
  const activeArticle = useMemo(() => {
    return articles.find((a) => a.id === activeArticleId);
  }, [articles, activeArticleId]);

  // Referencias visuales asignadas para prompts (incluye permanentes + seleccionadas)
  const activeAssignedVisualRefIds = useMemo(() => {
    const list = new Set<string>();
    visualReferences.forEach((r) => {
      if (r.status === 'aprobado' && (r.isEpisodePermanent || r.selectedForPrompt)) {
        list.add(r.identifier);
      }
    });
    return Array.from(list);
  }, [visualReferences]);

  // Analizador inteligente de guion multi-escena (~8s por escena)
  const multiSceneAnalysis = useMemo(() => {
    return splitScriptIntoScenes(scriptText, activeAssignedVisualRefIds, aspectRatio);
  }, [scriptText, activeAssignedVisualRefIds, aspectRatio]);

  const finalPrompt = usePromptFinal({
    scriptText,
    multiSceneAnalysis,
    movements,
    aspectRatio,
    selectedBackground,
  });

  const {
    handleAddArticle,
    handleImportBatchArticles,
    handleUpdateArticle,
    handleDeleteArticle,
    handleSelectArticleForProduction,
    handleAddEpisodeBlock,
  } = useNoticiasStudio({
    articles,
    setArticles,
    setEpisodeBlocks,
    setActiveArticleId,
    setScriptText,
    setVisualReferences,
    setCurrentTab,
    setErrorMessage,
    setSuccessToast,
    projectId,
  });

  const {
    handleToggleSelectVisualRef,
    handleTogglePermanentVisualRef,
    handleAddVisualRef,
    handleDeleteVisualRef,
    handleAddEditorialRef,
    handleDeleteEditorialRef,
  } = useReferenciasStudio({
    setVisualReferences,
    setEditorialReferences,
    setSuccessToast,
  });

  const {
    handleSelectExistingSheet,
    handleGenerateSheet,
    handleSelectCustomBg,
    handleGenerateVideo,
    handleToggleMovement,
  } = useFlowStudio({
    setSheetState,
    setIsGeneratingSheet,
    setIsGeneratingVideo,
    setVideoResult,
    setVisualReferences,
    setCustomBgMediaId,
    setMovements,
    setCurrentTab,
    setErrorMessage,
    setSuccessToast,
    sheetMediaId: sheetState.mediaId,
    customBgMediaId,
    visualReferences,
    aspectRatio,
    multiSceneAnalysis,
    finalPrompt,
  });

  const { construirPaquete, handleExportFullPackage, handleImportConfigurationJson } = usePaqueteProduccion({
    articles,
    episodeBlocks,
    visualReferences,
    editorialReferences,
    aspectRatio,
    selectedBackgroundId: selectedBackground.id,
    voiceSpeed,
    selectedMovementIds: movements.filter((m) => m.selected).map((m) => m.id),
    permanentCharacterMediaId: sheetState.mediaId,
    permanentBackgroundMediaId: customBgMediaId,
    setArticles,
    setEpisodeBlocks,
    setVisualReferences,
    setEditorialReferences,
    setAspectRatio,
    setVoiceSpeed,
    setSheetMediaId: (mediaId) => setSheetState((prev) => ({ ...prev, mediaId, isApproved: true })),
    setCustomBgMediaId,
    setIsExporting,
    setErrorMessage,
    setSuccessToast,
  });

  // Centro de mantenimiento (NN-113.15): auditoría de integridad y exportación.
  const [showMantenimiento, setShowMantenimiento] = useState(false);
  const paqueteMantenimiento = useMemo(() => construirPaquete(), [construirPaquete]);

  return (
    <div className="min-h-full bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-sky-500 selection:text-neutral-950">
      <TopNavigation
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
        hasApprovedSheet={Boolean(sheetState.mediaId && sheetState.isApproved)}
        selectedReferencesCount={activeAssignedVisualRefIds.length}
        approvedNewsCount={articles.filter((a) => a.approvalStatus === 'aprobada').length}
        embedded={embedded}
        onAbrirMantenimiento={() => setShowMantenimiento(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-4">
        {projectId && projectLoading && (
          <div className="card-compact text-neutral-300 text-xs">
            Cargando proyecto desde la base de datos…
          </div>
        )}
        {projectLoadError && (
          <div className="p-3 rounded-md bg-rose-950/80 border border-rose-800 text-rose-200 text-xs">
            No se pudo cargar el proyecto: {projectLoadError}
          </div>
        )}
        {projectId && !projectLoading && !projectLoadError && (
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
            {Object.entries(saveStates).some(([, st]) => st === 'conflict') ? (
              <span className="px-2 py-1 rounded bg-sky-950/80 border border-sky-800 text-sky-200">
                Conflicto de guardado: estado recargado del servidor (otra sesión guardó antes)
              </span>
            ) : Object.entries(saveStates).some(([, st]) => st === 'error') ? (
              <span className="px-2 py-1 rounded bg-rose-950/80 border border-rose-800 text-rose-200">
                Error al guardar: reintento pendiente al modificar
              </span>
            ) : Object.entries(saveStates).some(([, st]) => st === 'saving') ? (
              <span className="px-2 py-1 rounded bg-neutral-900 border border-neutral-800 text-neutral-300">
                Guardando en la base de datos…
              </span>
            ) : Object.entries(saveStates).some(([, st]) => st === 'saved') ? (
              <span className="px-2 py-1 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300">
                Guardado (persistente tras recargar)
              </span>
            ) : (
              <span className="px-2 py-1 rounded bg-neutral-900 border border-neutral-800 text-neutral-400">
                Estado sincronizado con el servidor
              </span>
            )}
          </div>
        )}
        {successToast && (
          <div className="p-3 rounded-md bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2">
              <span>{successToast}</span>
            </div>
            <button
              onClick={() => setSuccessToast(null)}
              aria-label="Cerrar el aviso"
              title="Cerrar"
              className="text-emerald-400 hover:text-ink cursor-pointer"
            >
              <IconoCruce />
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="p-3.5 rounded-md bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              aria-label="Cerrar el mensaje de error"
              title="Cerrar"
              className="text-rose-400 hover:text-ink cursor-pointer"
            >
              <IconoCruce />
            </button>
          </div>
        )}

        {currentTab === 'noticias' && (
          <>
            {projectId && <DossierPanel projectId={projectId} />}
            <NewsEditorialTab
            articles={articles}
            episodeBlocks={episodeBlocks}
            visualReferences={visualReferences}
            onAddArticle={handleAddArticle}
            onImportBatchArticles={handleImportBatchArticles}
            onUpdateArticle={handleUpdateArticle}
            onDeleteArticle={handleDeleteArticle}
            onSelectArticleForProduction={handleSelectArticleForProduction}
            activeProductionArticleId={activeArticleId}
            onAddEpisodeBlock={handleAddEpisodeBlock}
          />
          </>
        )}

        {currentTab === 'personaje' && (
          <CharacterSheetTab
            sheetState={sheetState}
            onUpdateSheet={(partial) => setSheetState((prev) => ({ ...prev, ...partial }))}
            onSelectExistingMedia={handleSelectExistingSheet}
            onGenerateSheet={handleGenerateSheet}
            isGenerating={isGeneratingSheet}
          />
        )}

        {currentTab === 'fondo' && (
          <BackgroundTab
            selectedPresetId={selectedBackground.id}
            onSelectPreset={setSelectedBackground}
            aspectRatio={aspectRatio}
            onChangeAspectRatio={setAspectRatio}
            customReferenceMediaId={customBgMediaId}
            onSelectCustomBackground={handleSelectCustomBg}
          />
        )}

        {currentTab === 'guion' && (
          <ScriptTab
            scriptText={scriptText}
            onChangeScript={setScriptText}
            multiSceneAnalysis={multiSceneAnalysis}
            selectedArticle={activeArticle}
            onApplyScenesToProduction={() => setCurrentTab('resultado')}
          />
        )}

        {currentTab === 'voz' && (
          <VoiceTab
            voiceConfig={{ ...ALGENIB_VOICE_CONFIG, speedMultiplier: voiceSpeed }}
            onUpdateSpeed={setVoiceSpeed}
          />
        )}

        {currentTab === 'movimiento' && (
          <MovementTab
            movements={movements}
            onToggleMovement={handleToggleMovement}
          />
        )}

        {currentTab === 'referencias' && (
          <ReferencesTab
            visualReferences={visualReferences}
            editorialReferences={editorialReferences}
            onToggleSelectVisualRef={handleToggleSelectVisualRef}
            onTogglePermanentVisualRef={handleTogglePermanentVisualRef}
            onAddVisualRef={handleAddVisualRef}
            onDeleteVisualRef={handleDeleteVisualRef}
            onAddEditorialRef={handleAddEditorialRef}
            onDeleteEditorialRef={handleDeleteEditorialRef}
            onExportConfiguration={handleExportFullPackage}
            onImportConfigurationJson={handleImportConfigurationJson}
            isExporting={isExporting}
          />
        )}

        {currentTab === 'resultado' && (
          <>
            {projectId && (
              <ProductionVertical
                projectId={projectId}
                shots={(project?.shots ?? []) as unknown[] as never}
                takes={(project?.takes ?? []) as unknown[] as never}
                onChanged={() => void reload()}
              />
            )}
            <ResultTab
            finalPrompt={finalPrompt}
            onGenerateVideo={handleGenerateVideo}
            isGeneratingVideo={isGeneratingVideo}
            generatedVideoBase64={videoResult?.base64}
            generatedVideoMime={videoResult?.mimeType}
            sheetState={sheetState}
            aspectRatio={aspectRatio}
            voiceConfig={{ ...ALGENIB_VOICE_CONFIG, speedMultiplier: voiceSpeed }}
            multiSceneAnalysis={multiSceneAnalysis}
            selectedReferences={visualReferences.filter(
              (r) => r.status === 'aprobado' && (r.isEpisodePermanent || r.selectedForPrompt)
            )}
            activeArticle={activeArticle}
            onExportProductionPackage={handleExportFullPackage}
            flowHosted={flowRuntime.hosted}
            selectedSceneIndex={resultSceneIndex}
            onSelectSceneIndex={setResultSceneIndex}
          />
          </>
        )}
      </main>

      {/* Centro de mantenimiento: auditoría de integridad y exportación (NN-113.15). */}
      <BackupModal
        isOpen={showMantenimiento}
        onClose={() => setShowMantenimiento(false)}
        paquete={paqueteMantenimiento}
      />

    </div>
  );
}
