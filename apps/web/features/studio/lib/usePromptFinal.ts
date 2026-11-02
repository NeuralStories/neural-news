'use client';

/**
 * Prompt final de la toma (NN-113.13): con escenas multi-escena se usa el
 * prompt compilado de la primera escena; sin ellas, se construye uno con la
 * duración estimada por número de palabras.
 */
import { useMemo } from 'react';
import { WORDS_PER_SECOND } from '../utils/scriptAnalyzer';
import type { BackgroundPreset, CameraMovement, MultiSceneScriptAnalysis } from '../types';

export interface OpcionesPromptFinal {
  scriptText: string;
  multiSceneAnalysis: MultiSceneScriptAnalysis;
  movements: CameraMovement[];
  aspectRatio: '16:9' | '9:16';
  selectedBackground: BackgroundPreset;
}

export function usePromptFinal({
  scriptText,
  multiSceneAnalysis,
  movements,
  aspectRatio,
  selectedBackground,
}: OpcionesPromptFinal): string {
  return useMemo(() => {
    const sceneDuration =
      multiSceneAnalysis.scenes[0]?.estDurationSeconds ??
      Number(
        (scriptText.trim().split(/\s+/).filter(Boolean).length / WORDS_PER_SECOND).toFixed(1),
      );
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
}
