import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Flow, flowRuntime } from './flow/adapter';
import { useStudioProject } from './lib/useStudioProject';
import { projectApi } from './lib/projectApi';
import { WORDS_PER_SECOND } from './utils/scriptAnalyzer';
import {
  StudioTab,
  MasterSheetState,
  BackgroundPreset,
  CameraMovement,
  VisualReferenceItem,
  EditorialReferenceItem,
  ApprovalStatus,
  NewsArticle,
  ProductionEpisodeBlock,
  StudioExportPackage,
  SceneProductionPlan,
} from './types';
import {
  MAXDOTAI_CANONICAL,
  BACKGROUND_PRESETS,
  ALGENIB_VOICE_CONFIG,
  CAMERA_MOVEMENTS_CATALOG,
  INITIAL_VISUAL_REFERENCES,
  INITIAL_EDITORIAL_REFERENCES,
  INITIAL_NEWS_ARTICLES,
  INITIAL_EPISODE_BLOCKS,
} from './constants';
import { splitScriptIntoScenes } from './utils/scriptAnalyzer';
import { checkArticleDuplicate } from './utils/newsDeduplication';
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

export default function App({ projectId }: { projectId: number | null }) {
  const [currentTab, setCurrentTab] = useState<StudioTab>('noticias');

  // Persistencia real (F1): el estado vive en la base de datos vía API; sin localStorage.
  const { project, loading: projectLoading, loadError: projectLoadError, saveStates, saveStep, reload } =
    useStudioProject(projectId);
  const [hydrated, setHydrated] = useState(false);
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
  // Los valores objetivo se calculan una sola vez y alimentan tanto el estado
  // como la instantánea de guardado (evita escrituras en eco).
  useEffect(() => {
    if (!project) {
      setHydrated(false);
      return;
    }
    const snap = savedSnapshotsRef.current;
    const noticias = (project.steps['noticias']?.payload ?? {}) as {
      articles?: NewsArticle[];
      episodeBlocks?: ProductionEpisodeBlock[];
      activeArticleId?: string;
    };
    const nextArticles =
      Array.isArray(noticias.articles) && noticias.articles.length > 0
        ? noticias.articles
        : articles;
    const nextBlocks =
      Array.isArray(noticias.episodeBlocks) && noticias.episodeBlocks.length > 0
        ? noticias.episodeBlocks
        : episodeBlocks;
    let nextActiveId =
      typeof noticias.activeArticleId === 'string' ? noticias.activeArticleId : activeArticleId;
    if (typeof noticias.activeArticleId !== 'string' && project.story_id) {
      // R-BUG-1: la noticia vinculada al proyecto es la activa sin pasos extra
      const linked = nextArticles.find((a) => a.metadata?.externalId?.endsWith(`:${project.story_id}`));
      if (linked) nextActiveId = linked.id;
    }
    const personaje = (project.steps['personaje']?.payload ?? {}) as { sheetState?: MasterSheetState };
    const nextSheet = personaje.sheetState ?? sheetState;
    const fondo = (project.steps['fondo']?.payload ?? {}) as {
      selectedBackgroundId?: string;
      aspectRatio?: '16:9' | '9:16';
      customBgMediaId?: string;
    };
    const nextBackground =
      (typeof fondo.selectedBackgroundId === 'string'
        ? BACKGROUND_PRESETS.find((b) => b.id === fondo.selectedBackgroundId)
        : undefined) ?? selectedBackground;
    const nextRatio =
      fondo.aspectRatio === '16:9' || fondo.aspectRatio === '9:16' ? fondo.aspectRatio : aspectRatio;
    const nextCustomBg =
      typeof fondo.customBgMediaId === 'string' ? fondo.customBgMediaId : customBgMediaId;
    const guion = (project.steps['guion']?.payload ?? {}) as { scriptText?: string };
    const nextScript = typeof guion.scriptText === 'string' ? guion.scriptText : scriptText;
    const voz = (project.steps['voz']?.payload ?? {}) as { voiceSpeed?: number };
    const nextSpeed = typeof voz.voiceSpeed === 'number' ? voz.voiceSpeed : voiceSpeed;
    const movimiento = (project.steps['movimiento']?.payload ?? {}) as { selectedMovementIds?: string[] };
    const nextSelected = Array.isArray(movimiento.selectedMovementIds)
      ? new Set<string>(movimiento.selectedMovementIds)
      : null;
    const nextMovements =
      nextSelected === null
        ? movements
        : movements.map((m) => ({ ...m, selected: nextSelected.has(m.id) }));
    const referencias = (project.steps['referencias']?.payload ?? {}) as {
      visualReferences?: VisualReferenceItem[];
      editorialReferences?: EditorialReferenceItem[];
    };
    const nextVisual =
      Array.isArray(referencias.visualReferences) && referencias.visualReferences.length > 0
        ? referencias.visualReferences
        : visualReferences;
    const nextEditorial =
      Array.isArray(referencias.editorialReferences) && referencias.editorialReferences.length > 0
        ? referencias.editorialReferences
        : editorialReferences;
    const resultado = (project.steps['resultado']?.payload ?? {}) as { selectedSceneIndex?: number };
    const nextResultSceneIndex =
      typeof resultado.selectedSceneIndex === 'number' && resultado.selectedSceneIndex >= 0
        ? resultado.selectedSceneIndex
        : resultSceneIndex;

    setArticles(nextArticles);
    setEpisodeBlocks(nextBlocks);
    setActiveArticleId(nextActiveId);
    setSheetState(nextSheet);
    setSelectedBackground(nextBackground);
    setAspectRatio(nextRatio);
    setCustomBgMediaId(nextCustomBg);
    setScriptText(nextScript);
    setVoiceSpeed(nextSpeed);
    setMovements(nextMovements);
    setVisualReferences(nextVisual);
    setEditorialReferences(nextEditorial);
    setResultSceneIndex(nextResultSceneIndex);

    snap['noticias'] = JSON.stringify({ articles: nextArticles, episodeBlocks: nextBlocks, activeArticleId: nextActiveId });
    snap['personaje'] = JSON.stringify({ sheetState: nextSheet });
    snap['fondo'] = JSON.stringify({ selectedBackgroundId: nextBackground.id, aspectRatio: nextRatio, customBgMediaId: nextCustomBg });
    snap['guion'] = JSON.stringify({ scriptText: nextScript });
    snap['voz'] = JSON.stringify({ voiceSpeed: nextSpeed });
    snap['movimiento'] = JSON.stringify({ selectedMovementIds: nextMovements.filter((m) => m.selected).map((m) => m.id) });
    snap['referencias'] = JSON.stringify({ visualReferences: nextVisual, editorialReferences: nextEditorial });
    snap['resultado'] = JSON.stringify({ selectedSceneIndex: nextResultSceneIndex });
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  /** Guarda solo si el payload cambió de verdad (evita revisiones en eco tras hidratar). */
  const saveIfChanged = useCallback(
    (step: string, payload: Record<string, unknown>) => {
      const json = JSON.stringify(payload);
      if (savedSnapshotsRef.current[step] === json) return;
      savedSnapshotsRef.current[step] = json;
      saveStep(step, payload);
    },
    [saveStep],
  );

  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('noticias', { articles, episodeBlocks, activeArticleId });
  }, [hydrated, articles, episodeBlocks, activeArticleId, saveIfChanged]);
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('personaje', { sheetState });
  }, [hydrated, sheetState, saveIfChanged]);
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('fondo', { selectedBackgroundId: selectedBackground.id, aspectRatio, customBgMediaId });
  }, [hydrated, selectedBackground, aspectRatio, customBgMediaId, saveIfChanged]);
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('guion', { scriptText });
  }, [hydrated, scriptText, saveIfChanged]);
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('voz', { voiceSpeed });
  }, [hydrated, voiceSpeed, saveIfChanged]);
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('movimiento', { selectedMovementIds: movements.filter((m) => m.selected).map((m) => m.id) });
  }, [hydrated, movements, saveIfChanged]);
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('referencias', { visualReferences, editorialReferences });
  }, [hydrated, visualReferences, editorialReferences, saveIfChanged]);
  // Octavo paso: «resultado». Antes solo se persistían siete de los ocho
  // (hallazgo B3): el estado del paso Resultado se perdía al recargar.
  useEffect(() => {
    if (!hydrated) return;
    saveIfChanged('resultado', { selectedSceneIndex: resultSceneIndex });
  }, [hydrated, resultSceneIndex, saveIfChanged]);

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

  // -----------------------------------------------------------------
  // GESTIÓN EDITORIAL DE NOTICIAS
  // -----------------------------------------------------------------
  const handleAddArticle = useCallback((newArt: Omit<NewsArticle, 'id' | 'orderIndex'>) => {
    const dupeCheck = checkArticleDuplicate(newArt, articles);
    if (dupeCheck.isDuplicate) {
      setErrorMessage(`Noticia duplicada detectada: ${dupeCheck.details}`);
      return;
    }

    const created: NewsArticle = {
      ...newArt,
      id: `news-${Date.now()}`,
      orderIndex: articles.length + 1,
    };
    setArticles((prev) => [created, ...prev]);
    setSuccessToast(`Noticia "${created.title.slice(0, 30)}..." añadida a la redacción.`);
    setTimeout(() => setSuccessToast(null), 3000);
  }, [articles]);

  const handleImportBatchArticles = useCallback((batch: NewsArticle[]) => {
    let imported = 0;
    let duplicates = 0;
    const duplicateDetails: string[] = [];

    const toAdd: NewsArticle[] = [];
    const currentList = [...articles];

    batch.forEach((art, idx) => {
      const dupeCheck = checkArticleDuplicate(art, [...currentList, ...toAdd]);
      if (dupeCheck.isDuplicate) {
        duplicates++;
        duplicateDetails.push(`"${art.title.slice(0, 35)}..." (${dupeCheck.details})`);
      } else {
        toAdd.push({
          ...art,
          id: art.id || `batch-art-${Date.now()}-${idx}`,
          orderIndex: currentList.length + toAdd.length + 1,
        });
        imported++;
      }
    });

    if (toAdd.length > 0) {
      setArticles((prev) => [...toAdd, ...prev]);
    }
    return { importedCount: imported, duplicateCount: duplicates, duplicateDetails };
  }, [articles]);

  const handleUpdateArticle = useCallback((id: string, updates: Partial<NewsArticle>) => {
    setArticles((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...updates } : a))
    );
  }, []);

  const handleDeleteArticle = useCallback((id: string) => {
    setArticles((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const handleSelectArticleForProduction = useCallback(async (article: NewsArticle) => {
    if (article.approvalStatus !== 'aprobada') {
      setErrorMessage(`La noticia "${article.title}" no puede enviarse a producción: requiere aprobación previa.`);
      return;
    }
    setActiveArticleId(article.id);
    if (projectId && article.metadata?.externalId?.startsWith('handoff:')) {
      // R-BUG-1: la pieza importada queda activa en el proyecto (traspaso → producción)
      const storyId = Number(article.metadata.externalId.split(':').pop());
      if (Number.isFinite(storyId)) {
        try {
          await projectApi.linkStory(projectId, storyId);
        } catch {
          /* el enlace se reintenta al guardar el paso Noticias */
        }
      }
    }
    setScriptText(article.fullScript);
    if (article.visualReferenceIds && article.visualReferenceIds.length > 0) {
      setVisualReferences((prev) =>
        prev.map((r) => {
          if (article.visualReferenceIds?.includes(r.identifier) && r.status === 'aprobado') {
            return { ...r, selectedForPrompt: true };
          }
          return r;
        })
      );
    }
    setCurrentTab('guion');
    setSuccessToast(`Noticia aprobada cargada en el analizador de escenas para producción.`);
    setTimeout(() => setSuccessToast(null), 3000);
  }, []);

  const handleAddEpisodeBlock = useCallback((title: string, notes?: string) => {
    const newBlock: ProductionEpisodeBlock = {
      id: `block-${Date.now()}`,
      title,
      date: new Date().toISOString().split('T')[0],
      articleIds: [],
      permanentVisualRefIds: ['REF-CHAR-01', 'REF-BG-CRT-01'],
      notes,
    };
    setEpisodeBlocks((prev) => [...prev, newBlock]);
    setSuccessToast(`Bloque "${title}" creado en la escaleta.`);
    setTimeout(() => setSuccessToast(null), 3000);
  }, []);

  const handleAssignArticleToBlock = useCallback((articleId: string, blockTitle: string) => {
    setArticles((prev) =>
      prev.map((a) => (a.id === articleId ? { ...a, episodeBlock: blockTitle } : a))
    );
  }, []);

  // -----------------------------------------------------------------
  // REFERENCIAS
  // -----------------------------------------------------------------
  const handleToggleSelectVisualRef = useCallback((id: string) => {
    setVisualReferences((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        if (r.status !== 'aprobado') return r;
        return { ...r, selectedForPrompt: !r.selectedForPrompt };
      })
    );
  }, []);

  const handleUpdateVisualRefStatus = useCallback((id: string, status: ApprovalStatus) => {
    setVisualReferences((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        return {
          ...r,
          status,
          selectedForPrompt: status === 'aprobado' ? r.selectedForPrompt : false,
        };
      })
    );
  }, []);

  const handleTogglePermanentVisualRef = useCallback((id: string) => {
    setVisualReferences((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        return { ...r, isEpisodePermanent: !r.isEpisodePermanent };
      })
    );
  }, []);

  const handleAddVisualRef = useCallback((item: Omit<VisualReferenceItem, 'id' | 'createdAt' | 'refType'>) => {
    const newItem: VisualReferenceItem = {
      ...item,
      id: `ref-vis-${Date.now()}`,
      refType: 'audiovisual',
      createdAt: new Date().toISOString().split('T')[0],
    };
    setVisualReferences((prev) => [newItem, ...prev]);
    setSuccessToast(`Referencia [${newItem.identifier}] registrada.`);
    setTimeout(() => setSuccessToast(null), 3000);
  }, []);

  const handleDeleteVisualRef = useCallback((id: string) => {
    setVisualReferences((prev) => prev.filter((r) => r.id !== id));
  }, []);

  const handleAddEditorialRef = useCallback((item: Omit<EditorialReferenceItem, 'id' | 'createdAt' | 'refType'>) => {
    const newItem: EditorialReferenceItem = {
      ...item,
      id: `ed-ref-${Date.now()}`,
      refType: 'editorial',
      createdAt: new Date().toISOString().split('T')[0],
    };
    setEditorialReferences((prev) => [newItem, ...prev]);
    setSuccessToast(`Referencia editorial [${newItem.identifier}] añadida.`);
    setTimeout(() => setSuccessToast(null), 3000);
  }, []);

  const handleDeleteEditorialRef = useCallback((id: string) => {
    setEditorialReferences((prev) => prev.filter((e) => e.id !== id));
  }, []);

  // -----------------------------------------------------------------
  // SELECCIÓN Y GENERACIÓN DE HOJA MAESTRA
  // -----------------------------------------------------------------
  const handleSelectExistingSheet = async () => {
    try {
      setErrorMessage(null);
      const media = await Flow.media.select({ filter: 'image' });
      setSheetState({
        mediaId: media.mediaId,
        base64: media.base64,
        mimeType: media.mimeType,
        isApproved: true,
        notes: `Cargada desde galería: ${media.name || 'Hoja maxDotAi'}`,
      });
      setVisualReferences((prev) => {
        const exists = prev.some((r) => r.mediaId === media.mediaId);
        if (exists) return prev;
        return [
          {
            id: `ref-sheet-${Date.now()}`,
            refType: 'audiovisual',
            name: `Hoja Maestra - ${media.name || 'maxDotAi'}`,
            identifier: `REF-CHAR-${Math.floor(100 + Math.random() * 900)}`,
            category: 'personaje',
            imageUrl: `data:${media.mimeType};base64,${media.base64}`,
            mediaId: media.mediaId,
            description: 'Hoja maestra 16:9 oficial de tres paneles seleccionada de galería.',
            version: 'v1.0',
            status: 'aprobado',
            selectedForPrompt: true,
            isEpisodePermanent: true,
            tags: ['hoja_maestra', 'tres_paneles', 'aprobada'],
            createdAt: new Date().toISOString().split('T')[0],
          },
          ...prev,
        ];
      });
      setSuccessToast('Hoja maestra vinculada e integrada.');
      setTimeout(() => setSuccessToast(null), 3000);
    } catch (err) {
      console.error(err);
      setErrorMessage('No se completó la selección de la hoja aprobada.');
    }
  };

  const handleGenerateSheet = async (prompt: string) => {
    try {
      setErrorMessage(null);
      setIsGeneratingSheet(true);
      const result = await Flow.generate.image({
        prompt,
        modelDisplayName: '🍌 Nano Banana Pro',
        aspectRatio: '16:9',
      });
      setSheetState({
        mediaId: result.mediaId,
        base64: result.base64,
        mimeType: result.mimeType,
        isApproved: true,
        notes: 'Generada con Nano Banana Pro (16:9)',
      });
      setVisualReferences((prev) => [
        {
          id: `ref-gen-${Date.now()}`,
          refType: 'audiovisual',
          name: 'Hoja Maestra Generada Nano Banana Pro',
          identifier: `REF-CHAR-GEN`,
          category: 'personaje',
          imageUrl: `data:${result.mimeType};base64,${result.base64}`,
          mediaId: result.mediaId,
          description: 'Hoja maestra canónica 16:9 de tres paneles generada.',
          version: 'v1.0',
          status: 'aprobado',
          selectedForPrompt: true,
          isEpisodePermanent: true,
          tags: ['nano_banana_pro', '16_9', 'turnaround'],
          createdAt: new Date().toISOString().split('T')[0],
        },
        ...prev,
      ]);
      setSuccessToast('Hoja generada, auto-guardada en galería e incorporada.');
      setTimeout(() => setSuccessToast(null), 3500);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(err.message || 'Error al generar la hoja maestra.');
    } finally {
      setIsGeneratingSheet(false);
    }
  };

  const handleSelectCustomBg = async () => {
    try {
      const media = await Flow.media.select({ filter: 'image' });
      setCustomBgMediaId(media.mediaId);
      setVisualReferences((prev) => [
        {
          id: `ref-bg-${Date.now()}`,
          refType: 'audiovisual',
          name: `Fondo Galería - ${media.name || 'Plató CRT'}`,
          identifier: `REF-BG-${Math.floor(100 + Math.random() * 900)}`,
          category: 'fondo',
          imageUrl: `data:${media.mimeType};base64,${media.base64}`,
          mediaId: media.mediaId,
          description: 'Fondo de escenario seleccionado de la galería.',
          version: 'v1.0',
          status: 'aprobado',
          selectedForPrompt: true,
          isEpisodePermanent: true,
          tags: ['fondo', 'galeria_flow'],
          createdAt: new Date().toISOString().split('T')[0],
        },
        ...prev,
      ]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleMovement = useCallback((id: string) => {
    setMovements((prev) =>
      prev.map((m) => (m.id === id ? { ...m, selected: !m.selected } : m))
    );
  }, []);

  // Exportación del Contrato JSON de producción editorial (neural.news v2.0)
  const handleExportFullPackage = async () => {
    try {
      setIsExporting(true);
      setErrorMessage(null);

      const exportPkg: StudioExportPackage = {
        formatVersion: '2.0',
        exportedAt: new Date().toISOString(),
        studio: 'NeuralStories News (@maxDotAi)',
        contract: 'neural.news-studio-v2',
        articles,
        episodeBlocks,
        visualReferences,
        editorialReferences,
        studioConfig: {
          aspectRatio,
          selectedBackgroundId: selectedBackground.id,
          voiceSpeedMultiplier: voiceSpeed,
          selectedMovementIds: movements.filter((m) => m.selected).map((m) => m.id),
          permanentCharacterMediaId: sheetState.mediaId,
          permanentBackgroundMediaId: customBgMediaId,
        },
      };

      const jsonString = JSON.stringify(exportPkg, null, 2);
      const bytes = new TextEncoder().encode(jsonString);
      const base64 = btoa(Array.from(bytes, (b) => String.fromCharCode(b)).join(''));

      await Flow.download({
        base64,
        mimeType: 'application/json',
        filename: `neural_news_production_package_${Date.now()}.json`,
      });

      setSuccessToast('Paquete de producción neural.news exportado exitosamente.');
      setTimeout(() => setSuccessToast(null), 3000);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(err.message || 'Error al exportar el proyecto con Flow.download.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleImportConfigurationJson = useCallback((imported: any) => {
    try {
      if (Array.isArray(imported.articles)) {
        setArticles(imported.articles);
      }
      if (Array.isArray(imported.episodeBlocks)) {
        setEpisodeBlocks(imported.episodeBlocks);
      }
      if (Array.isArray(imported.visualReferences)) {
        setVisualReferences(imported.visualReferences);
      }
      if (Array.isArray(imported.editorialReferences)) {
        setEditorialReferences(imported.editorialReferences);
      }
      if (imported.studioConfig) {
        if (imported.studioConfig.aspectRatio) setAspectRatio(imported.studioConfig.aspectRatio);
        if (imported.studioConfig.voiceSpeedMultiplier) setVoiceSpeed(imported.studioConfig.voiceSpeedMultiplier);
        if (imported.studioConfig.permanentCharacterMediaId) {
          setSheetState(prev => ({ ...prev, mediaId: imported.studioConfig.permanentCharacterMediaId, isApproved: true }));
        }
        if (imported.studioConfig.permanentBackgroundMediaId) {
          setCustomBgMediaId(imported.studioConfig.permanentBackgroundMediaId);
        }
      }
      setSuccessToast('Proyecto y redacción editorial restaurados correctamente.');
      setTimeout(() => setSuccessToast(null), 3500);
    } catch (err: any) {
      setErrorMessage(`Error en formato de importación: ${err.message}`);
    }
  }, []);

  const finalPrompt = useMemo(() => {
    const sceneDuration =
      multiSceneAnalysis.scenes[0]?.estDurationSeconds ??
      Number((scriptText.trim().split(/\s+/).filter(Boolean).length / WORDS_PER_SECOND).toFixed(1));
    if (multiSceneAnalysis.scenes.length > 0) {
      return multiSceneAnalysis.scenes[0].compiledPrompt;
    }

    const selectedMoves = movements
      .filter((m) => m.selected)
      .map((m) => m.promptInstruction)
      .join('. ');

    const framing =
      aspectRatio === '9:16'
        ? 'Vertical 9:16 broadcast framing, tight chest-up close framing.'
        : 'Cinematic 16:9 television broadcast framing, tight chest-up close framing.';

    return (
      `Cinematic AI news broadcast segment of ${sceneDuration} seconds (calculated from word count) for NeuralStories News featuring anchor maxDotAi. ` +
      `${framing} ` +
      `Anchor character identity strictly preserved: contemporary black rectangular glasses, short neat dark hair, groomed short beard, tailored dark navy tech blazer. ` +
      `Setting: ${selectedBackground.promptDescriptor} ` +
      `Camera and visual dynamics: ${selectedMoves || 'Smooth locked-on camera, broadcast stability.'} ` +
      `Anchor speech delivery cadence: Spanish Algenib profile, crisp mouth articulation speaking the news line: "${scriptText.trim()}". ` +
      `Visual effects: purely optical visual RGB shift glitches, scanline flicker, photorealistic studio lighting, duration exactly ${sceneDuration} seconds, 4k ultra-sharp.`
    );
  }, [multiSceneAnalysis, movements, aspectRatio, selectedBackground, scriptText]);

  // Generación de vídeo con Omni 1.1 Flash
  const handleGenerateVideo = async (promptToUse?: string) => {
    try {
      setErrorMessage(null);
      setIsGeneratingVideo(true);

      const referenceMediaIds: string[] = [];
      if (sheetState.mediaId) referenceMediaIds.push(sheetState.mediaId);
      if (customBgMediaId && !referenceMediaIds.includes(customBgMediaId)) {
        referenceMediaIds.push(customBgMediaId);
      }

      visualReferences.forEach((r) => {
        if (r.mediaId && (r.isEpisodePermanent || r.selectedForPrompt)) {
          if (!referenceMediaIds.includes(r.mediaId)) {
            referenceMediaIds.push(r.mediaId);
          }
        }
      });

      const options: any = {
        prompt: promptToUse || finalPrompt,
        modelDisplayName: 'Omni 1.1 Flash',
        aspectRatio,
        durationSeconds: Math.max(2, Math.round(multiSceneAnalysis.scenes[0]?.estDurationSeconds ?? 8)),
        resolution: '720p',
      };

      if (referenceMediaIds.length > 0) {
        options.referenceImageMediaIds = referenceMediaIds;
      }

      const video = await Flow.generate.video(options);
      setVideoResult({
        base64: video.base64,
        mimeType: video.mimeType,
      });
      setCurrentTab('resultado');
      setSuccessToast('Toma generada con éxito en Omni 1.1 Flash.');
      setTimeout(() => setSuccessToast(null), 3000);
    } catch (err: any) {
      console.error(err);
      setErrorMessage(err.message || 'Error al generar la toma en Omni 1.1 Flash.');
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  return (
    <div className="min-h-full bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-sky-500 selection:text-neutral-950">
      <TopNavigation
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
        hasApprovedSheet={Boolean(sheetState.mediaId && sheetState.isApproved)}
        selectedReferencesCount={activeAssignedVisualRefIds.length}
        approvedNewsCount={articles.filter((a) => a.approvalStatus === 'aprobada').length}
        embedded={embedded}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-4">
        {projectId && projectLoading && (
          <div className="p-3 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs">
            Cargando proyecto desde la base de datos…
          </div>
        )}
        {projectLoadError && (
          <div className="p-3 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs">
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
                Guardado ✓ (persistente tras recargar)
              </span>
            ) : (
              <span className="px-2 py-1 rounded bg-neutral-900 border border-neutral-800 text-neutral-400">
                Estado sincronizado con el servidor
              </span>
            )}
          </div>
        )}
        {successToast && (
          <div className="p-3 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2">
              <span>{successToast}</span>
            </div>
            <button onClick={() => setSuccessToast(null)} className="text-emerald-400 hover:text-white cursor-pointer">
              </button>
          </div>
        )}

        {errorMessage && (
          <div className="p-3.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white cursor-pointer">
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
            editorialReferences={editorialReferences}
            onAddArticle={handleAddArticle}
            onImportBatchArticles={handleImportBatchArticles}
            onUpdateArticle={handleUpdateArticle}
            onDeleteArticle={handleDeleteArticle}
            onSelectArticleForProduction={handleSelectArticleForProduction}
            activeProductionArticleId={activeArticleId}
            onAddEpisodeBlock={handleAddEpisodeBlock}
            onAssignArticleToBlock={handleAssignArticleToBlock}
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
            onUpdateVisualRefStatus={handleUpdateVisualRefStatus}
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
            onCopyPrompt={async () => {
              await navigator.clipboard.writeText(finalPrompt);
            }}
            onGenerateVideo={handleGenerateVideo}
            isGeneratingVideo={isGeneratingVideo}
            generatedVideoBase64={videoResult?.base64}
            generatedVideoMime={videoResult?.mimeType}
            sheetState={sheetState}
            selectedBackground={selectedBackground}
            aspectRatio={aspectRatio}
            voiceConfig={{ ...ALGENIB_VOICE_CONFIG, speedMultiplier: voiceSpeed }}
            activeMovements={movements.filter((m) => m.selected)}
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

    </div>
  );
}