'use client';

/**
 * Paquete de producción: exportación e importación del contrato JSON del
 * Studio (NN-113.13). Extraído de `App.tsx`.
 */
import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { Flow } from '../flow/adapter';
import { errorMessage as mensajeDeError } from '../utils/errorMessage';
import type {
  ConfiguracionImportada,
  EditorialReferenceItem,
  NewsArticle,
  ProductionEpisodeBlock,
  StudioExportPackage,
  VisualReferenceItem,
} from '../types';

export interface OpcionesPaquete {
  articles: NewsArticle[];
  episodeBlocks: ProductionEpisodeBlock[];
  visualReferences: VisualReferenceItem[];
  editorialReferences: EditorialReferenceItem[];
  aspectRatio: '16:9' | '9:16';
  selectedBackgroundId: string;
  voiceSpeed: number;
  selectedMovementIds: string[];
  permanentCharacterMediaId?: string;
  permanentBackgroundMediaId?: string;
  setArticles: Dispatch<SetStateAction<NewsArticle[]>>;
  setEpisodeBlocks: Dispatch<SetStateAction<ProductionEpisodeBlock[]>>;
  setVisualReferences: Dispatch<SetStateAction<VisualReferenceItem[]>>;
  setEditorialReferences: Dispatch<SetStateAction<EditorialReferenceItem[]>>;
  setAspectRatio: (ratio: '16:9' | '9:16') => void;
  setVoiceSpeed: (speed: number) => void;
  setSheetMediaId: (mediaId: string) => void;
  setCustomBgMediaId: (mediaId: string | undefined) => void;
  setIsExporting: (exportando: boolean) => void;
  setErrorMessage: (mensaje: string | null) => void;
  setSuccessToast: (mensaje: string | null) => void;
}

export interface GestorPaquete {
  /** Construye el contrato de producción con el estado actual (sin efectos). */
  construirPaquete: () => StudioExportPackage;
  handleExportFullPackage: () => Promise<void>;
  handleImportConfigurationJson: (imported: ConfiguracionImportada) => void;
}

export function usePaqueteProduccion(opciones: OpcionesPaquete): GestorPaquete {
  const {
    articles,
    episodeBlocks,
    visualReferences,
    editorialReferences,
    aspectRatio,
    selectedBackgroundId,
    voiceSpeed,
    selectedMovementIds,
    permanentCharacterMediaId,
    permanentBackgroundMediaId,
    setArticles,
    setEpisodeBlocks,
    setVisualReferences,
    setEditorialReferences,
    setAspectRatio,
    setVoiceSpeed,
    setSheetMediaId,
    setCustomBgMediaId,
    setIsExporting,
    setErrorMessage,
    setSuccessToast,
  } = opciones;

  const construirPaquete = useCallback((): StudioExportPackage => {
    return {
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
        selectedBackgroundId,
        voiceSpeedMultiplier: voiceSpeed,
        selectedMovementIds,
        permanentCharacterMediaId,
        permanentBackgroundMediaId,
      },
    };
  }, [
    articles,
    episodeBlocks,
    visualReferences,
    editorialReferences,
    aspectRatio,
    selectedBackgroundId,
    voiceSpeed,
    selectedMovementIds,
    permanentCharacterMediaId,
    permanentBackgroundMediaId,
  ]);

  const handleExportFullPackage = useCallback(async () => {
    try {
      setIsExporting(true);
      setErrorMessage(null);

      const exportPkg = construirPaquete();

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
    } catch (err) {
      console.error(err);
      setErrorMessage(mensajeDeError(err) || 'Error al exportar el proyecto con Flow.download.');
    } finally {
      setIsExporting(false);
    }
  }, [
    construirPaquete,
    setIsExporting,
    setErrorMessage,
    setSuccessToast,
  ]);

  const handleImportConfigurationJson = useCallback(
    (imported: ConfiguracionImportada) => {
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
        const studioConfig = imported.studioConfig;
        if (studioConfig) {
          if (studioConfig.aspectRatio) setAspectRatio(studioConfig.aspectRatio);
          if (studioConfig.voiceSpeedMultiplier) setVoiceSpeed(studioConfig.voiceSpeedMultiplier);
          if (studioConfig.permanentCharacterMediaId) {
            setSheetMediaId(studioConfig.permanentCharacterMediaId);
          }
          if (studioConfig.permanentBackgroundMediaId) {
            setCustomBgMediaId(studioConfig.permanentBackgroundMediaId);
          }
        }
        setSuccessToast('Proyecto y redacción editorial restaurados correctamente.');
        setTimeout(() => setSuccessToast(null), 3500);
      } catch (err) {
        setErrorMessage(`Error en formato de importación: ${mensajeDeError(err) ?? 'error desconocido'}`);
      }
    },
    [
      setArticles,
      setEpisodeBlocks,
      setVisualReferences,
      setEditorialReferences,
      setAspectRatio,
      setVoiceSpeed,
      setSheetMediaId,
      setCustomBgMediaId,
      setErrorMessage,
      setSuccessToast,
    ],
  );

  return { construirPaquete, handleExportFullPackage, handleImportConfigurationJson };
}
