'use client';

/**
 * Hidratación del Studio (NN-113.13).
 *
 * Antes vivía dentro de `App.tsx` (900 líneas): el efecto que lee el proyecto
 * guardado en el servidor y lo convierte en estado del Studio ocupaba casi cien
 * líneas en medio del componente. Aquí queda aislado y con su propio tipo.
 *
 * La regla se mantiene intacta: **el estado guardado en el servidor manda en la
 * primera carga**; los valores objetivo sólo se usan como reserva cuando el
 * servidor no trae ese paso.
 */
import { useEffect, useState } from 'react';
import type { MutableRefObject } from 'react';
import { BACKGROUND_PRESETS } from '../constants';
import type {
  BackgroundPreset,
  CameraMovement,
  EditorialReferenceItem,
  MasterSheetState,
  NewsArticle,
  ProductionEpisodeBlock,
  VisualReferenceItem,
} from '../types';
import type { ProjectFull } from './projectApi';

/** Valores del Studio que se hidratan desde el proyecto guardado. */
export interface ValoresStudio {
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
}

export interface OpcionesHidratacion {
  project: ProjectFull | null;
  valores: ValoresStudio;
  /** Aplica los valores calculados (el App pasa los `setState`). */
  aplicar: (valores: ValoresStudio) => void;
  /** Instantáneas de lo guardado: sirven para no escribir en eco. */
  instantaneas: MutableRefObject<Record<string, string>>;
}

/**
 * Calcula el estado del Studio a partir del proyecto guardado y lo aplica.
 * Devuelve `true` cuando la hidratación ha terminado.
 */
export function useHidratacionStudio({
  project,
  valores,
  aplicar,
  instantaneas,
}: OpcionesHidratacion): boolean {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (!project) {
      setHydrated(false);
      return;
    }
    const snap = instantaneas.current;
    const noticias = (project.steps['noticias']?.payload ?? {}) as {
      articles?: NewsArticle[];
      episodeBlocks?: ProductionEpisodeBlock[];
      activeArticleId?: string;
    };
    const nextArticles =
      Array.isArray(noticias.articles) && noticias.articles.length > 0
        ? noticias.articles
        : valores.articles;
    const nextBlocks =
      Array.isArray(noticias.episodeBlocks) && noticias.episodeBlocks.length > 0
        ? noticias.episodeBlocks
        : valores.episodeBlocks;
    let nextActiveId =
      typeof noticias.activeArticleId === 'string' ? noticias.activeArticleId : valores.activeArticleId;
    if (typeof noticias.activeArticleId !== 'string' && project.story_id) {
      // R-BUG-1: la noticia vinculada al proyecto es la activa sin pasos extra
      const linked = nextArticles.find((a) => a.metadata?.externalId?.endsWith(`:${project.story_id}`));
      if (linked) nextActiveId = linked.id;
    }
    const personaje = (project.steps['personaje']?.payload ?? {}) as { sheetState?: MasterSheetState };
    const nextSheet = personaje.sheetState ?? valores.sheetState;
    const fondo = (project.steps['fondo']?.payload ?? {}) as {
      selectedBackgroundId?: string;
      aspectRatio?: '16:9' | '9:16';
      customBgMediaId?: string;
    };
    const nextBackground =
      (typeof fondo.selectedBackgroundId === 'string'
        ? BACKGROUND_PRESETS.find((b) => b.id === fondo.selectedBackgroundId)
        : undefined) ?? valores.selectedBackground;
    const nextRatio =
      fondo.aspectRatio === '16:9' || fondo.aspectRatio === '9:16' ? fondo.aspectRatio : valores.aspectRatio;
    const nextCustomBg =
      typeof fondo.customBgMediaId === 'string' ? fondo.customBgMediaId : valores.customBgMediaId;
    const guion = (project.steps['guion']?.payload ?? {}) as { scriptText?: string };
    const nextScript = typeof guion.scriptText === 'string' ? guion.scriptText : valores.scriptText;
    const voz = (project.steps['voz']?.payload ?? {}) as { voiceSpeed?: number };
    const nextSpeed = typeof voz.voiceSpeed === 'number' ? voz.voiceSpeed : valores.voiceSpeed;
    const movimiento = (project.steps['movimiento']?.payload ?? {}) as { selectedMovementIds?: string[] };
    const nextSelected = Array.isArray(movimiento.selectedMovementIds)
      ? new Set<string>(movimiento.selectedMovementIds)
      : null;
    const nextMovements =
      nextSelected === null
        ? valores.movements
        : valores.movements.map((m) => ({ ...m, selected: nextSelected.has(m.id) }));
    const referencias = (project.steps['referencias']?.payload ?? {}) as {
      visualReferences?: VisualReferenceItem[];
      editorialReferences?: EditorialReferenceItem[];
    };
    const nextVisual =
      Array.isArray(referencias.visualReferences) && referencias.visualReferences.length > 0
        ? referencias.visualReferences
        : valores.visualReferences;
    const nextEditorial =
      Array.isArray(referencias.editorialReferences) && referencias.editorialReferences.length > 0
        ? referencias.editorialReferences
        : valores.editorialReferences;
    const resultado = (project.steps['resultado']?.payload ?? {}) as { selectedSceneIndex?: number };
    const nextResultSceneIndex =
      typeof resultado.selectedSceneIndex === 'number' && resultado.selectedSceneIndex >= 0
        ? resultado.selectedSceneIndex
        : valores.resultSceneIndex;

    aplicar({
      articles: nextArticles,
      episodeBlocks: nextBlocks,
      activeArticleId: nextActiveId,
      sheetState: nextSheet,
      selectedBackground: nextBackground,
      aspectRatio: nextRatio,
      customBgMediaId: nextCustomBg,
      scriptText: nextScript,
      voiceSpeed: nextSpeed,
      movements: nextMovements,
      visualReferences: nextVisual,
      editorialReferences: nextEditorial,
      resultSceneIndex: nextResultSceneIndex,
    });

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

  return hydrated;
}
