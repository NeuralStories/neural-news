'use client';

/**
 * Gestión editorial de noticias del Studio (NN-113.13).
 *
 * Extraído de `App.tsx`: alta, importación por lotes, edición, borrado,
 * traspaso a producción y bloques de escaleta. Aquí queda el **criterio de
 * negocio** (una noticia sin aprobación no puede ir a producción) y el resto
 * del componente queda con la presentación y el cableado.
 */
import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { projectApi } from './projectApi';
import { checkArticleDuplicate } from '../utils/newsDeduplication';
import type {
  NewsArticle,
  ProductionEpisodeBlock,
  StudioTab,
  VisualReferenceItem,
} from '../types';

export interface OpcionesNoticias {
  articles: NewsArticle[];
  setArticles: Dispatch<SetStateAction<NewsArticle[]>>;
  setEpisodeBlocks: Dispatch<SetStateAction<ProductionEpisodeBlock[]>>;
  setActiveArticleId: (id: string) => void;
  setScriptText: (texto: string) => void;
  setVisualReferences: Dispatch<SetStateAction<VisualReferenceItem[]>>;
  setCurrentTab: (tab: StudioTab) => void;
  setErrorMessage: (mensaje: string | null) => void;
  setSuccessToast: (mensaje: string | null) => void;
  projectId: number | null;
}

export interface GestorNoticias {
  handleAddArticle: (newArt: Omit<NewsArticle, 'id' | 'orderIndex'>) => void;
  handleImportBatchArticles: (batch: NewsArticle[]) => {
    importedCount: number;
    duplicateCount: number;
    duplicateDetails: string[];
  };
  handleUpdateArticle: (id: string, updates: Partial<NewsArticle>) => void;
  handleDeleteArticle: (id: string) => void;
  handleSelectArticleForProduction: (article: NewsArticle) => Promise<void>;
  handleAddEpisodeBlock: (title: string, notes?: string) => void;
}

export function useNoticiasStudio(opciones: OpcionesNoticias): GestorNoticias {
  const {
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
  } = opciones;

  const handleAddArticle = useCallback(
    (newArt: Omit<NewsArticle, 'id' | 'orderIndex'>) => {
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
    },
    [articles, setArticles, setErrorMessage, setSuccessToast],
  );

  const handleImportBatchArticles = useCallback(
    (batch: NewsArticle[]) => {
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
    },
    [articles, setArticles],
  );

  const handleUpdateArticle = useCallback((id: string, updates: Partial<NewsArticle>) => {
    setArticles((prev) => prev.map((a) => (a.id === id ? { ...a, ...updates } : a)));
  }, [setArticles]);

  const handleDeleteArticle = useCallback((id: string) => {
    setArticles((prev) => prev.filter((a) => a.id !== id));
  }, [setArticles]);

  const handleSelectArticleForProduction = useCallback(
    async (article: NewsArticle) => {
      if (article.approvalStatus !== 'aprobada') {
        setErrorMessage(
          `La noticia "${article.title}" no puede enviarse a producción: requiere aprobación previa.`,
        );
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
          }),
        );
      }
      setCurrentTab('guion');
      setSuccessToast('Noticia aprobada cargada en el analizador de escenas para producción.');
      setTimeout(() => setSuccessToast(null), 3000);
    },
    [projectId, setActiveArticleId, setCurrentTab, setErrorMessage, setScriptText, setSuccessToast, setVisualReferences],
  );

  const handleAddEpisodeBlock = useCallback(
    (title: string, notes?: string) => {
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
    },
    [setEpisodeBlocks, setSuccessToast],
  );

  return {
    handleAddArticle,
    handleImportBatchArticles,
    handleUpdateArticle,
    handleDeleteArticle,
    handleSelectArticleForProduction,
    handleAddEpisodeBlock,
  };
}
