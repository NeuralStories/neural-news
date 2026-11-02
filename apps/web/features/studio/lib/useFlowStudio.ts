'use client';

/**
 * Integración con Flow (galería de medios, generación de imagen y de vídeo)
 * dentro del Studio. Extraído de `App.tsx` (NN-113.13).
 *
 * Cuando Flow no está disponible, la operación falla **diciéndolo**: nunca se
 * simula un resultado. El error real va al log y el mensaje a la interfaz.
 */
import { useCallback } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { Flow } from '../flow/adapter';
import { errorMessage as mensajeDeError } from '../utils/errorMessage';
import type {
  CameraMovement,
  MasterSheetState,
  MultiSceneScriptAnalysis,
  VisualReferenceItem,
} from '../types';

export interface OpcionesFlowStudio {
  setSheetState: Dispatch<SetStateAction<MasterSheetState>>;
  setIsGeneratingSheet: (generando: boolean) => void;
  setIsGeneratingVideo: (generando: boolean) => void;
  setVideoResult: (resultado: { base64?: string; mimeType?: string } | null) => void;
  setVisualReferences: Dispatch<SetStateAction<VisualReferenceItem[]>>;
  setCustomBgMediaId: (mediaId: string | undefined) => void;
  setMovements: React.Dispatch<React.SetStateAction<CameraMovement[]>>;
  setCurrentTab: (tab: 'resultado') => void;
  setErrorMessage: (mensaje: string | null) => void;
  setSuccessToast: (mensaje: string | null) => void;
  /** Estado necesario para generar la toma. */
  sheetMediaId?: string;
  customBgMediaId?: string;
  visualReferences: VisualReferenceItem[];
  aspectRatio: '16:9' | '9:16';
  multiSceneAnalysis: MultiSceneScriptAnalysis;
  /** Prompt final calculado: se usa si la toma se genera sin prompt explícito. */
  finalPrompt: string;
}

export interface GestorFlow {
  handleSelectExistingSheet: () => Promise<void>;
  handleGenerateSheet: (prompt: string) => Promise<void>;
  handleSelectCustomBg: () => Promise<void>;
  handleGenerateVideo: (promptToUse?: string) => Promise<void>;
  handleToggleMovement: (id: string) => void;
}

export function useFlowStudio(opciones: OpcionesFlowStudio): GestorFlow {
  const {
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
    sheetMediaId,
    customBgMediaId,
    visualReferences,
    aspectRatio,
    multiSceneAnalysis,
    finalPrompt,
  } = opciones;

  const handleSelectExistingSheet = useCallback(async () => {
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
  }, [setErrorMessage, setSheetState, setSuccessToast, setVisualReferences]);

  const handleGenerateSheet = useCallback(
    async (prompt: string) => {
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
            identifier: 'REF-CHAR-GEN',
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
      } catch (err) {
        console.error(err);
        setErrorMessage(mensajeDeError(err) || 'Error al generar la hoja maestra.');
      } finally {
        setIsGeneratingSheet(false);
      }
    },
    [setErrorMessage, setIsGeneratingSheet, setSheetState, setSuccessToast, setVisualReferences],
  );

  const handleSelectCustomBg = useCallback(async () => {
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
  }, [setCustomBgMediaId, setVisualReferences]);

  const handleToggleMovement = useCallback(
    (id: string) => {
      setMovements((prev) => prev.map((m) => (m.id === id ? { ...m, selected: !m.selected } : m)));
    },
    [setMovements],
  );

  const handleGenerateVideo = useCallback(
    async (promptToUse?: string) => {
      try {
        setErrorMessage(null);
        setIsGeneratingVideo(true);

        const referenceMediaIds: string[] = [];
        if (sheetMediaId) referenceMediaIds.push(sheetMediaId);
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

        const options: {
          prompt: string;
          modelDisplayName: string;
          aspectRatio: '16:9' | '9:16';
          durationSeconds: number;
          resolution: string;
          referenceImageMediaIds?: string[];
        } = {
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
      } catch (err) {
        console.error(err);
        setErrorMessage(mensajeDeError(err) || 'Error al generar la toma en Omni 1.1 Flash.');
      } finally {
        setIsGeneratingVideo(false);
      }
    },
    [
      sheetMediaId,
      customBgMediaId,
      visualReferences,
      aspectRatio,
      multiSceneAnalysis,
      finalPrompt,
      setErrorMessage,
      setIsGeneratingVideo,
      setVideoResult,
      setCurrentTab,
      setSuccessToast,
    ],
  );

  return {
    handleSelectExistingSheet,
    handleGenerateSheet,
    handleSelectCustomBg,
    handleGenerateVideo,
    handleToggleMovement,
  };
}
