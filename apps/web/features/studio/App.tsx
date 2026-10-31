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
import { HandoffImport } from './integration/components/HandoffImport';
import { ProductionPlanPanel } from './integration/components/ProductionPlanPanel';
import { ProductionVertical } from './components/ProductionVertical';
import { TopNavigation } from './components/TopNavigation';
import { NewsEditorialTab } from './components/NewsEditorialTab';
import { CharacterSheetTab } from './components/CharacterSheetTab';
import { BackgroundTab } from './components/BackgroundTab';
import { ScriptTab } from './components/ScriptTab';
import { VoiceTab } from './components/VoiceTab';
import { MovementTab } from './components/MovementTab';
import { ReferencesTab } from './components/ReferencesTab';
import { ResultTab } from './components/ResultTab';
import { HelpModal } from './components/HelpModal';
import { BackupModal } from './components/BackupModal';

export default function App({ projectId }: { projectId: number | null }) {
  const [currentTab, setCurrentTab] = useState<StudioTab>('noticias');
  const [helpOpen, setHelpOpen] = useState(false);
  const [backupOpen, setBackupOpen] = useState(false);

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

  // MÓDULO 2: PERSONAJE (@neuraldotai)
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

    snap['noticias'] = JSON.stringify({ articles: nextArticles, episodeBlocks: nextBlocks, activeArticleId: nextActiveId });
    snap['personaje'] = JSON.stringify({ sheetState: nextSheet });
    snap['fondo'] = JSON.stringify({ selectedBackgroundId: nextBackground.id, aspectRatio: nextRatio, customBgMediaId: nextCustomBg });
    snap['guion'] = JSON.stringify({ scriptText: nextScript });
    snap['voz'] = JSON.stringify({ voiceSpeed: nextSpeed });
    snap['movimiento'] = JSON.stringify({ selectedMovementIds: nextMovements.filter((m) => m.selected).map((m) => m.id) });
    snap['referencias'] = JSON.stringify({ visualReferences: nextVisual, editorialReferences: nextEditorial });
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
        studio: 'NeuralStories News (@neuraldotai)',
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

  // Recepción del traspaso production_handoff.v1 (verificado por el consumidor)
  const handleImportHandoffArticles = useCallback(
    (imported: Omit<NewsArticle, 'id' | 'orderIndex'>[]) => {
      return handleImportBatchArticles(imported as NewsArticle[]);
    },
    [handleImportBatchArticles]
  );

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

  // Mapa de código fuente completo en memoria para la auditoría y exportación verificable
  const fullAppSources = useMemo<Record<string, string>>(() => {
    return {
      "types.ts": `export type StudioTab = 'noticias' | 'personaje' | 'fondo' | 'guion' | 'voz' | 'movimiento' | 'referencias' | 'resultado';
export interface CharacterPreset { name: string; handle: string; show: string; features: { face: string; glasses: string; hair: string; beard: string; age: string; wardrobe: string; }; }
export interface MasterSheetState { mediaId?: string; base64?: string; mimeType?: string; isApproved: boolean; notes: string; }
export interface BackgroundPreset { id: string; title: string; description: string; aspectRatio: '16:9' | '9:16'; promptDescriptor: string; }
export interface VoiceConfig { profile: string; gender: string; timbre: string; locale: string; speedMultiplier: number; cadenceDescription: string; }
export interface CameraMovement { id: string; label: string; category: 'encuadre' | 'dinamismo' | 'efecto'; description: string; promptInstruction: string; selected: boolean; }
export interface SceneProductionPlan { sceneIndex: number; scriptSnippet: string; wordCount: number; estDurationSeconds: number; recommendedFraming: string; movementInstruction: string; transitionType: 'corte_directo' | 'rgb_glitch_flash' | 'whip_pan' | 'push_zoom'; visualReferenceIds: string[]; compiledPrompt: string; }
export interface MultiSceneScriptAnalysis { fullWordCount: number; fullEstDurationSeconds: number; targetDurationSeconds: number; scenesCount: number; scenes: SceneProductionPlan[]; paceRating: 'muy_rapido' | 'optimo' | 'lento' | 'excesivo'; feedback: string; }
export interface NewsScriptAnalysis { wordCount: number; estDurationSeconds: number; isValid8s: boolean; paceRating: 'muy_rapido' | 'optimo' | 'lento' | 'excesivo'; feedback: string; }
export type ReferenceType = 'editorial' | 'audiovisual';
export type VisualReferenceCategory = 'personaje' | 'fondo' | 'escena' | 'estilo';
export type EditorialSourceType = 'enlace' | 'documento' | 'transcripcion_youtube' | 'transcripcion_spotify' | 'comunicado_oficial';
export type ApprovalStatus = 'aprobado' | 'pendiente' | 'descartado';
export interface VisualReferenceItem { id: string; refType: 'audiovisual'; name: string; identifier: string; category: VisualReferenceCategory; imageUrl: string; mediaId?: string; description: string; version: string; status: ApprovalStatus; selectedForPrompt: boolean; isEpisodePermanent?: boolean; tags?: string[]; createdAt: string; }
export interface EditorialReferenceItem { id: string; refType: 'editorial'; identifier: string; title: string; sourceType: EditorialSourceType; urlOrCitation: string; summaryOrExcerpt: string; authorOrChannel?: string; status: ApprovalStatus; createdAt: string; }
export type UnifiedReferenceItem = VisualReferenceItem | EditorialReferenceItem;
export type VerificationStatus = 'verificado' | 'en_revision' | 'sin_verificar' | 'descartado';
export type ArticleApprovalStatus = 'aprobada' | 'pendiente' | 'descartada';
export interface NewsArticle { id: string; uuid?: string; slug?: string; title: string; summary: string; fullScript: string; date: string; verificationStatus: VerificationStatus; approvalStatus: ArticleApprovalStatus; episodeBlock?: string; orderIndex: number; sources: string[]; editorialReferenceIds: string[]; visualReferenceIds: string[]; tags: string[]; metadata?: { importedFrom?: 'manual' | 'batch_json' | 'youtube_transcription' | 'spotify_feed' | 'api_sync'; externalId?: string; verifiedBy?: string; }; }
export interface ProductionEpisodeBlock { id: string; title: string; date: string; articleIds: string[]; permanentVisualRefIds: string[]; notes?: string; }
export interface StudioExportPackage { formatVersion: '2.0'; exportedAt: string; studio: string; contract: 'neural.news-studio-v2'; articles: NewsArticle[]; episodeBlocks: ProductionEpisodeBlock[]; visualReferences: VisualReferenceItem[]; editorialReferences: EditorialReferenceItem[]; studioConfig: { aspectRatio: '16:9' | '9:16'; selectedBackgroundId: string; voiceSpeedMultiplier: number; selectedMovementIds: string[]; permanentCharacterMediaId?: string; permanentBackgroundMediaId?: string; }; }`,

      "constants.ts": `import { CharacterPreset, BackgroundPreset, VoiceConfig, CameraMovement, VisualReferenceItem, EditorialReferenceItem, NewsArticle, ProductionEpisodeBlock } from './types';
export const MAXDOTAI_CANONICAL: CharacterPreset = { name: 'maxDotAi', handle: '@maxDotAi (pendiente de confirmar en cuenta)', show: 'NeuralStories News', features: { face: 'Rostro masculino mediterráneo/ibérico sereno, facciones definidas pero amables', glasses: 'Gafas de pasta de diseño contemporáneo, montura rectangular oscura y sobria', hair: 'Pelo castaño oscuro corto, peinado ordenado con textura mate', beard: 'Barba recortada de 3-4 días, perfilada y cuidada', age: 'Aparente 32-35 años, aspecto profesional y tecnológico', wardrobe: 'Camisa azul noche oxford o camiseta técnica sobria con blazer oscuro de corte limpio sin adornos estrambóticos' } };
export const DEFAULT_MASTER_SHEET_PROMPT = "Character turnaround master model sheet for news anchor maxDotAi (official presenter of NeuralStories News). Neutral plain solid medium studio gray background (#555555), crisp high key studio lighting. Strictly exactly THREE panels in a horizontal 16:9 layout: 1. Left panel: Large front face portrait closeup with smart black rectangular glasses, short styled dark hair, neat short beard, looking confidently into the camera. 2. Center panel: Frontal body view framed strictly from clavicles down to waist, showing precise matching dark navy tailored tech blazer and minimalist inner shirt. NO HEAD/NO FACE in this panel. 3. Right panel: Posterior rear back view of the upper torso and head from behind, identical clothing and posture. NO FRONT FACE. Strict rule: exactly ONE visible face in the entire 16:9 canvas. Zero duplication, photorealistic 8k, broadcast production sheet.";
export const BACKGROUND_PRESETS: BackgroundPreset[] = [
  { id: 'crt_original_wide', title: 'Estudio CRT Clásico (16:9)', description: 'Batería de monitores de tubo CRT retroiluminados, estética cyberpunk corporativa cálida', aspectRatio: '16:9', promptDescriptor: 'Original NeuralStories studio setup with vintage physical cathode-ray tube (CRT) monitor wall, glowing amber and cyan scanlines, physical bezel hardware monitors, subtle broadcast studio depth of field.' },
  { id: 'crt_original_vertical', title: 'Estudio CRT Vertical (9:16)', description: 'Encuadre optimizado para móviles/Reels/TikTok con torres verticales de pantallas CRT', aspectRatio: '9:16', promptDescriptor: 'Vertical 9:16 format broadcasting backdrop with stacked physical CRT cathode televisions, raster beam scanlines, moody newsroom lighting, dark reflections.' },
  { id: 'crt_glitch_accent', title: 'Estudio CRT con Alerta Glitch', description: 'Fondo de pantallas CRT parpadeando con gráficos de datos y matrices de noticias', aspectRatio: '16:9', promptDescriptor: 'CRT monitor studio bank showing live AI breaking news graphics, faint analog sync glitch, warm tube filament glow behind the anchor.' }
];
export const ALGENIB_VOICE_CONFIG: VoiceConfig = { profile: 'Algenib', gender: 'Masculina', timbre: 'Grave, ligeramente rugosa, con peso editorial y calidez radiofónica', locale: 'Español de España (Castellano neutro ibérico)', speedMultiplier: 1.18, cadenceDescription: 'Locución dinámica, dicción impecable, ritmo picado continuo sin titubeos ni silencios muertos, tono informativo enérgico pero riguroso.' };
export const CAMERA_MOVEMENTS_CATALOG: CameraMovement[] = [
  { id: 'lateral_slide_in', label: 'Entrada Lateral Rápida (Whip-in)', category: 'dinamismo', description: 'Cámara entra desde la izquierda/derecha y clava el encuadre en el presentador.', promptInstruction: 'Rapid smooth lateral camera whip-in from screen left to center lock-on, anchor remains rock steady.', selected: true },
  { id: 'chest_punch_zoom', label: 'Zoom Rápido al Pecho (Snap Zoom)', category: 'encuadre', description: 'Encuadre cerrado desde el pecho con empuje óptico dinámico.', promptInstruction: 'Tight chest-up close framing, immediate punchy snap-zoom toward anchor chest, broadcast telemetry stability.', selected: true },
  { id: 'subtle_dolly', label: 'Travelling Frontal Continuo', category: 'dinamismo', description: 'Acercamiento progresivo constante de 8 segundos sin sacudidas.', promptInstruction: 'Continuous slow push-in dolly shot toward speaker face for 8 seconds, zero camera shake.', selected: false },
  { id: 'rgb_glitch_cut', label: 'Transición Glitch RGB Analógico', category: 'efecto', description: 'Aberración cromática analógica y micro desfase horizontal sin afectar al personaje.', promptInstruction: 'Subtle high-speed RGB channel split chromatic aberration glitch, analog VHS raster shift flash for 0.4s.', selected: true },
  { id: 'horizontal_flip', label: 'Inversión de Ángulo / Panorámica Rápida', category: 'encuadre', description: 'Cambio de perspectiva lateral a frontal en corte de compás.', promptInstruction: 'Dynamic perspective shift snapping from 15-degree off-axis angle to dead-center frontal anchor posture.', selected: false }
];
export const INITIAL_VISUAL_REFERENCES: VisualReferenceItem[] = [
  { id: 'ref-char-01', refType: 'audiovisual', name: 'maxDotAi - Retrato Frontal Canónico', identifier: 'REF-CHAR-01', category: 'personaje', imageUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80', description: 'Rostro masculino mediterráneo, gafas de montura negra rectangular, barba corta perfilada de 3 días, mirada frontal directa al teleprómpter.', version: 'v1.4', status: 'aprobado', selectedForPrompt: true, isEpisodePermanent: true, tags: ['maxdotai', 'gafas_negras', 'rostro', 'canónico'], createdAt: '2025-02-01' },
  { id: 'ref-bg-01', refType: 'audiovisual', name: 'Muro CRT Analógico Original', identifier: 'REF-BG-CRT-01', category: 'fondo', imageUrl: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=600&q=80', description: 'Pared de monitores de tubo catódico con curvas de vidrio, biseles metálicos, fósforo ámbar y cian, líneas de barrido entrelazadas.', version: 'v2.1', status: 'aprobado', selectedForPrompt: true, isEpisodePermanent: true, tags: ['crt', 'scanlines', 'plató', 'ámbar'], createdAt: '2025-02-05' },
  { id: 'ref-scene-01', refType: 'audiovisual', name: 'Encuadre Cerrado al Pecho 8s', identifier: 'REF-SCENE-CHEST-01', category: 'escena', imageUrl: 'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=600&q=80', description: 'Composición clásica de presentador de noticias de alta tecnología: encuadre de busto desde el pecho, iluminación lateral y silueteado cian.', version: 'v1.0', status: 'aprobado', selectedForPrompt: false, isEpisodePermanent: false, tags: ['encuadre', 'pecho', 'televisivo', '8s'], createdAt: '2025-02-10' },
  { id: 'ref-style-01', refType: 'audiovisual', name: 'Estética Editorial Neocibernética', identifier: 'REF-STYLE-CYBER-01', category: 'estilo', imageUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80', description: 'Acabado broadcast sin estridencias, grano cinematográfico sutil de 35mm, aberración cromática calibrada y contraste cromático ámbar/azul noche.', version: 'v1.2', status: 'aprobado', selectedForPrompt: true, isEpisodePermanent: false, tags: ['estilo', 'broadcast', 'grano', 'neuralstories'], createdAt: '2025-02-12' }
];
export const INITIAL_EDITORIAL_REFERENCES: EditorialReferenceItem[] = [
  { id: 'ed-src-01', refType: 'editorial', identifier: 'ED-SRC-01', title: 'Paper Técnico: Escalabilidad de Inferencia en Tiempo Real', sourceType: 'documento', urlOrCitation: 'https://arxiv.org/abs/2412.inference-scaling-demo', summaryOrExcerpt: 'Demostración de destilación de modelos de difusión capaces de computar batches de vídeo a 60 fps sin drift perceptual.', authorOrChannel: 'MIT Computer Science & AI Lab', status: 'aprobado', createdAt: '2025-02-14' },
  { id: 'ed-src-02', refType: 'editorial', identifier: 'ED-SRC-02', title: 'Transcripción: Conferencia de Líderes de Chips Cuánticos', sourceType: 'transcripcion_youtube', urlOrCitation: 'https://youtube.com/watch?v=neural_keynote_transcription', summaryOrExcerpt: 'Declaración clave: Los centros de datos europeos adoptan arquitecturas híbridas neuromórficas para el segundo semestre.', authorOrChannel: 'TechSummit Global Stream', status: 'aprobado', createdAt: '2025-02-18' },
  { id: 'ed-src-03', refType: 'editorial', identifier: 'ED-SRC-03', title: 'Comunicado Regulatorio: Estándares de Consistencia en Medios Sintéticos', sourceType: 'comunicado_oficial', urlOrCitation: 'https://europa.eu/ai-act/broadcast-synthetic-guidelines', summaryOrExcerpt: 'Obligatoriedad de trazabilidad de semillas de identidad para presentadores de noticias sintéticos en territorio de la UE.', authorOrChannel: 'Oficina Europea de Inteligencia Artificial', status: 'aprobado', createdAt: '2025-02-20' }
];
export const INITIAL_NEWS_ARTICLES: NewsArticle[] = [
  { id: 'news-001', title: 'Avance en Inferencia de Modelos Multimodales en Tiempo Real', summary: 'Nuevas arquitecturas reducen drásticamente la latencia en el razonamiento de agentes autónomos con despliegue en Europa.', fullScript: 'Bienvenidos a NeuralStories News. Soy maxDotAi. Una nueva filtración revela arquitecturas que razonan en tiempo real sin latencia perceptible. Los ingenieros confirman la integración total en agentes autónomos antes del próximo trimestre. Este avance permite interacciones fluidas sin tiempos de espera.', date: '2025-02-22', verificationStatus: 'verificado', approvalStatus: 'aprobada', episodeBlock: 'Bloque 1: Titulares Principales', orderIndex: 1, sources: ['https://arxiv.org/abs/2412.inference-scaling-demo', 'https://neural.news/internal-brief-01'], editorialReferenceIds: ['ED-SRC-01'], visualReferenceIds: ['REF-CHAR-01', 'REF-BG-CRT-01', 'REF-STYLE-CYBER-01'], tags: ['ia', 'multimodal', 'agentes', 'hardware'], metadata: { importedFrom: 'api_sync', verifiedBy: 'Equipo Editorial neural.news' } },
  { id: 'news-002', title: 'Estándares Europeos de Trazabilidad en Presentadores Sintéticos', summary: 'La normativa comunitaria fija la obligatoriedad de sellos y hojas de consistencia para avatares periodísticos.', fullScript: 'La Oficina Europea de Inteligencia Artificial aprueba las primeras directrices para presentadores sintéticos. A partir de este año, todo noticiero automatizado deberá conservar hojas maestras de identidad inmutables para evitar suplantaciones y garantizar la transparencia editorial ante la audiencia.', date: '2025-02-21', verificationStatus: 'verificado', approvalStatus: 'aprobada', episodeBlock: 'Bloque 1: Titulares Principales', orderIndex: 2, sources: ['https://europa.eu/ai-act/broadcast-synthetic-guidelines'], editorialReferenceIds: ['ED-SRC-03'], visualReferenceIds: ['REF-CHAR-01', 'REF-BG-CRT-01'], tags: ['regulacion', 'ue', 'avatares', 'etica'], metadata: { importedFrom: 'manual', verifiedBy: 'Mesa de Fact-Checking' } },
  { id: 'news-003', title: 'Consistencia Temporal Cinematográfica a 60 FPS en Modelos de Vídeo', summary: 'Se superan las aberraciones visuales y el morphing en planos secuencia largos gracias a matrices de atención física.', fullScript: 'La consistencia temporal en modelos generativos supera el listón cinematográfico más estricto. La iluminación física, la ausencia de deformaciones faciales y las físicas de partículas estables a sesenta fotogramas marcan el inicio de una nueva era en la producción audiovisual.', date: '2025-02-20', verificationStatus: 'en_revision', approvalStatus: 'pendiente', episodeBlock: 'Bloque 2: Tendencias Audiovisuales', orderIndex: 3, sources: ['https://neural.news/tech-radar-2025'], editorialReferenceIds: ['ED-SRC-02'], visualReferenceIds: ['REF-STYLE-CYBER-01'], tags: ['video-ia', 'consistencia', '60fps'], metadata: { importedFrom: 'manual' } }
];
export const INITIAL_EPISODE_BLOCKS: ProductionEpisodeBlock[] = [
  { id: 'block-01', title: 'Bloque 1: Titulares Principales', date: '2025-02-22', articleIds: ['news-001', 'news-002'], permanentVisualRefIds: ['REF-CHAR-01', 'REF-BG-CRT-01'], notes: 'Emisión central de apertura con maxDotAi en mesa CRT principal.' },
  { id: 'block-02', title: 'Bloque 2: Tendencias Audiovisuales', date: '2025-02-22', articleIds: ['news-003'], permanentVisualRefIds: ['REF-CHAR-01', 'REF-BG-CRT-01'], notes: 'Bloque de profundidad tecnológica e impacto en industrias creativas.' }
];`,

      "utils/scriptAnalyzer.ts": `import { NewsScriptAnalysis, MultiSceneScriptAnalysis, SceneProductionPlan } from '../types';
export const WORDS_PER_SECOND = 2.85;
export const CANONICAL_SCENE_SECONDS = 8.0;
export function analyzeScriptFor8Seconds(text: string): NewsScriptAnalysis {
  const clean = text.trim();
  if (!clean) return { wordCount: 0, estDurationSeconds: 0, isValid8s: false, paceRating: 'muy_rapido', feedback: 'Introduce el texto de la entradilla o noticia.' };
  const words = clean.split(/\\s+/).filter(w => w.length > 0);
  const wordCount = words.length;
  const estSeconds = Number((wordCount / WORDS_PER_SECOND).toFixed(1));
  let paceRating: NewsScriptAnalysis['paceRating'] = 'optimo';
  let feedback = '';
  let isValid8s = false;
  if (wordCount < 12) { paceRating = 'lento'; isValid8s = true; feedback = \`Texto breve (\${wordCount} palabras, ~\${estSeconds}s).\`; }
  else if (wordCount <= 25) { paceRating = 'optimo'; isValid8s = true; feedback = \`Perfecto para 8 segundos (\${wordCount} palabras, ~\${estSeconds}s).\`; }
  else if (wordCount <= 28) { paceRating = 'muy_rapido'; isValid8s = true; feedback = \`Al límite (\${wordCount} palabras, ~\${estSeconds}s).\`; }
  else { paceRating = 'excesivo'; isValid8s = false; feedback = \`Demasiado largo para una sola toma (\${wordCount} palabras, ~\${estSeconds}s).\`; }
  return { wordCount, estDurationSeconds: estSeconds, isValid8s, paceRating, feedback };
}
export function splitScriptIntoScenes(fullScript: string, assignedVisualRefIds: string[] = ['REF-CHAR-01', 'REF-BG-CRT-01'], aspectRatio: '16:9' | '9:16' = '16:9'): MultiSceneScriptAnalysis {
  const clean = fullScript.trim();
  if (!clean) return { fullWordCount: 0, fullEstDurationSeconds: 0, targetDurationSeconds: 0, scenesCount: 0, scenes: [], paceRating: 'optimo', feedback: 'El guion está vacío.' };
  const allWords = clean.split(/\\s+/).filter(w => w.length > 0);
  const fullWordCount = allWords.length;
  const fullEstDurationSeconds = Number((fullWordCount / WORDS_PER_SECOND).toFixed(1));
  const tokenClauses: string[] = [];
  const clauseRegex = /[^.!?;\n]+(?:[.!?;\n]+|$)/g;
  let match: RegExpExecArray | null;
  while ((match = clauseRegex.exec(clean)) !== null) {
    const clauseText = match[0].trim();
    if (clauseText.length > 0) tokenClauses.push(clauseText);
  }
  if (tokenClauses.length === 0) tokenClauses.push(clean);
  const sceneChunks: string[] = [];
  let currentWords: string[] = [];
  for (const clause of tokenClauses) {
    const clauseWords = clause.split(/\\s+/).filter(w => w.length > 0);
    if (currentWords.length + clauseWords.length <= 25) {
      currentWords.push(...clauseWords);
    } else {
      if (currentWords.length >= 12) {
        sceneChunks.push(currentWords.join(' '));
        currentWords = [...clauseWords];
      } else {
        currentWords.push(...clauseWords);
        sceneChunks.push(currentWords.join(' '));
        currentWords = [];
      }
    }
  }
  if (currentWords.length > 0) sceneChunks.push(currentWords.join(' '));
  const scenes: SceneProductionPlan[] = sceneChunks.map((snippet, idx) => {
    const sWords = snippet.split(/\\s+/).filter(w => w.length > 0).length;
    const estSec = Number((sWords / WORDS_PER_SECOND).toFixed(1));
    return {
      sceneIndex: idx + 1,
      scriptSnippet: snippet,
      wordCount: sWords,
      estDurationSeconds: estSec,
      recommendedFraming: 'Medium closeup chest framing.',
      movementInstruction: 'Rapid lateral whip-in.',
      transitionType: 'corte_directo',
      visualReferenceIds: assignedVisualRefIds,
      compiledPrompt: \`Scene \${idx + 1}: \${snippet}\`
    };
  });
  return { fullWordCount, fullEstDurationSeconds, targetDurationSeconds: Math.max(8, scenes.length * 8), scenesCount: scenes.length, scenes, paceRating: 'optimo', feedback: 'Guion estructurado en escenas íntegras.' };
}`,

      "utils/newsDeduplication.ts": `import { NewsArticle } from '../types';
export interface DuplicateMatchResult { isDuplicate: boolean; reason?: 'id_match' | 'source_match' | 'title_similarity' | 'slug_match'; matchedArticleId?: string; matchedTitle?: string; similarityScore?: number; details?: string; }
function normalizeUrl(url: string): string { try { const u = new URL(url.trim().toLowerCase()); u.searchParams.delete('utm_source'); return (u.origin + u.pathname).replace(/\\/+$/, ''); } catch { return url.trim().toLowerCase().replace(/\\/+$/, ''); } }
function getWordTokens(text: string): Set<string> { const words = text.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').replace(/[^a-z0-9\\s]/g, ' ').split(/\\s+/).filter(w => w.length > 2); return new Set(words); }
function calculateJaccardSimilarity(textA: string, textB: string): number { const setA = getWordTokens(textA); const setB = getWordTokens(textB); if (setA.size === 0 || setB.size === 0) return 0; let intersection = 0; for (const token of setA) { if (setB.has(token)) intersection++; } const union = new Set([...setA, ...setB]).size; return union > 0 ? intersection / union : 0; }
export function checkArticleDuplicate(candidate: Partial<NewsArticle>, existingArticles: NewsArticle[], similarityThreshold = 0.65): DuplicateMatchResult {
  const candId = candidate.id?.trim().toLowerCase();
  const candTitle = candidate.title?.trim() || '';
  const candSources = (candidate.sources || []).map(normalizeUrl).filter(s => s.length > 0);
  for (const existing of existingArticles) {
    if (candId && candId === existing.id.trim().toLowerCase()) return { isDuplicate: true, reason: 'id_match', matchedArticleId: existing.id, matchedTitle: existing.title, details: \`ID idéntico: \${existing.id}\` };
    if (candSources.length > 0 && existing.sources && existing.sources.length > 0) {
      const exSources = existing.sources.map(normalizeUrl);
      const sharedSource = candSources.find(cs => exSources.includes(cs));
      if (sharedSource) return { isDuplicate: true, reason: 'source_match', matchedArticleId: existing.id, matchedTitle: existing.title, details: \`Fuente URL coincidente: \${sharedSource}\` };
    }
    if (candTitle && existing.title) {
      const score = calculateJaccardSimilarity(candTitle, existing.title);
      if (score >= similarityThreshold) return { isDuplicate: true, reason: 'title_similarity', matchedArticleId: existing.id, matchedTitle: existing.title, similarityScore: Number((score * 100).toFixed(1)), details: \`Similitud semántica de titular: \${(score * 100).toFixed(0)}%\` };
    }
  }
  return { isDuplicate: false };
}`,

      "App.tsx": `// Componente raíz App.tsx del estudio neural.news
// Responsable de orquestar noticias, hoja maestra, plató CRT, guiones, voz y exportación.
import React from 'react';
export default function App({ projectId }: { projectId: number | null }) { /* Orquestador principal neural.news */ return null; }`
    };
  }, []);

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-amber-500 selection:text-slate-950">
      <TopNavigation
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
        hasApprovedSheet={Boolean(sheetState.mediaId && sheetState.isApproved)}
        selectedReferencesCount={activeAssignedVisualRefIds.length}
        approvedNewsCount={articles.filter((a) => a.approvalStatus === 'aprobada').length}
        onOpenHelp={() => setHelpOpen(true)}
        onOpenBackupModal={() => setBackupOpen(true)}
        embedded={embedded}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-4">
        {projectId && projectLoading && (
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 text-xs">
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
              <span className="px-2 py-1 rounded bg-amber-950/80 border border-amber-800 text-amber-200">
                Conflicto de guardado: estado recargado del servidor (otra sesión guardó antes)
              </span>
            ) : Object.entries(saveStates).some(([, st]) => st === 'error') ? (
              <span className="px-2 py-1 rounded bg-rose-950/80 border border-rose-800 text-rose-200">
                Error al guardar: reintento pendiente al modificar
              </span>
            ) : Object.entries(saveStates).some(([, st]) => st === 'saving') ? (
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                Guardando en la base de datos…
              </span>
            ) : Object.entries(saveStates).some(([, st]) => st === 'saved') ? (
              <span className="px-2 py-1 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300">
                Guardado ✓ (persistente tras recargar)
              </span>
            ) : (
              <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                Estado sincronizado con el servidor
              </span>
            )}
          </div>
        )}
        {successToast && (
          <div className="p-3 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-200 text-xs flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-emerald-400">check_circle</span>
              <span>{successToast}</span>
            </div>
            <button onClick={() => setSuccessToast(null)} className="text-emerald-400 hover:text-white cursor-pointer">
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="p-3.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-rose-400">error</span>
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white cursor-pointer">
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        )}

        {currentTab === 'noticias' && (
          <>
            <HandoffImport onImportArticles={handleImportHandoffArticles} />
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
            <ProductionPlanPanel article={activeArticle} />
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
          />
          </>
        )}
      </main>

      <HelpModal isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
      
      <BackupModal 
        isOpen={backupOpen} 
        onClose={() => setBackupOpen(false)} 
        fullFilesMap={fullAppSources}
      />
    </div>
  );
}