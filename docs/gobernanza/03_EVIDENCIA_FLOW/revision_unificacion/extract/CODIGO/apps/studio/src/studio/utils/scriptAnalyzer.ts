import type { NewsScriptAnalysis, MultiSceneScriptAnalysis, SceneProductionPlan } from '../types';

/**
 * Ritmo de locución Algenib (+18% sobre estándar):
 * ~2.85 palabras por segundo (171 palabras por minuto).
 * Toma canónica del generador de vídeo: ~8.0 segundos => ~20-24 palabras por escena.
 */
export const WORDS_PER_SECOND = 2.85;
export const CANONICAL_SCENE_SECONDS = 8.0;

/**
 * Análisis individual para tomas de 8 segundos estrictos.
 */
export function analyzeScriptFor8Seconds(text: string): NewsScriptAnalysis {
  const clean = text.trim();
  if (!clean) {
    return {
      wordCount: 0,
      estDurationSeconds: 0,
      isValid8s: false,
      paceRating: 'muy_rapido',
      feedback: 'Introduce el texto de la entradilla o noticia.'
    };
  }

  const words = clean.split(/\s+/).filter(w => w.length > 0);
  const wordCount = words.length;
  const estSeconds = Number((wordCount / WORDS_PER_SECOND).toFixed(1));

  let paceRating: NewsScriptAnalysis['paceRating'] = 'optimo';
  let feedback = '';
  let isValid8s = false;

  if (wordCount < 12) {
    paceRating = 'lento';
    isValid8s = true;
    feedback = `Texto breve (${wordCount} palabras, ~${estSeconds}s). Deja espacio para pausas dramáticas de cámara.`;
  } else if (wordCount >= 12 && wordCount <= 25) {
    paceRating = 'optimo';
    isValid8s = true;
    feedback = `Perfecto para 8 segundos (${wordCount} palabras, ~${estSeconds}s). Encaja con la cadencia de Algenib (+18%).`;
  } else if (wordCount > 25 && wordCount <= 28) {
    paceRating = 'muy_rapido';
    isValid8s = true;
    feedback = `Al límite (${wordCount} palabras, ~${estSeconds}s). Requerirá locución sumamente rápida para no cortar la toma.`;
  } else {
    paceRating = 'excesivo';
    isValid8s = false;
    feedback = `Demasiado largo para una sola toma de 8s (${wordCount} palabras, ~${estSeconds}s). Divídelo en varias escenas o reduce unas ${wordCount - 24} palabras.`;
  }

  return {
    wordCount,
    estDurationSeconds: estSeconds,
    isValid8s,
    paceRating,
    feedback
  };
}

/**
 * Divide un guion editorial completo respetando estrictamente:
 * 1. La secuencia completa de palabras originales en orden sin omisiones ni adiciones.
 * 2. Unidades de sentido y cláusulas naturales (. ! ? ; ,).
 * 3. Segmentación en tomas de ~8 segundos (~20-25 palabras).
 */
export function splitScriptIntoScenes(
  fullScript: string,
  assignedVisualRefIds: string[] = ['REF-CHAR-01', 'REF-BG-CRT-01'],
  aspectRatio: '16:9' | '9:16' = '16:9'
): MultiSceneScriptAnalysis {
  const clean = fullScript.trim();
  if (!clean) {
    return {
      fullWordCount: 0,
      fullEstDurationSeconds: 0,
      targetDurationSeconds: 0,
      scenesCount: 0,
      scenes: [],
      paceRating: 'optimo',
      feedback: 'El guion está vacío.'
    };
  }

  const allWords = clean.split(/\s+/).filter(w => w.length > 0);
  const fullWordCount = allWords.length;
  const fullEstDurationSeconds = Number((fullWordCount / WORDS_PER_SECOND).toFixed(1));

  // Descomposición en unidades gramaticales conservando todos los caracteres
  // Buscamos signos de puntuación como puntos de fractura preferentes
  const tokenClauses: string[] = [];
  const clauseRegex = /[^.!?;\n]+(?:[.!?;\n]+|$)/g;
  let match: RegExpExecArray | null;
  while ((match = clauseRegex.exec(clean)) !== null) {
    const clauseText = match[0].trim();
    if (clauseText.length > 0) {
      tokenClauses.push(clauseText);
    }
  }

  if (tokenClauses.length === 0) {
    tokenClauses.push(clean);
  }

  const sceneChunks: string[] = [];
  let currentWords: string[] = [];

  for (const clause of tokenClauses) {
    const clauseWords = clause.split(/\s+/).filter(w => w.length > 0);

    // Si una cláusula individual es extremadamente larga (> 26 palabras), la dividimos por comas o límites seguros
    if (clauseWords.length > 26) {
      const subParts = clause.split(/(?<=[,])\s+/);
      for (const part of subParts) {
        const pWords = part.trim().split(/\s+/).filter(w => w.length > 0);
        if (pWords.length === 0) continue;

        if (currentWords.length + pWords.length <= 25) {
          currentWords.push(...pWords);
        } else {
          if (currentWords.length > 0) {
            sceneChunks.push(currentWords.join(' '));
            currentWords = [];
          }
          currentWords.push(...pWords);
        }
      }
      continue;
    }

    // Comprobar si cabe en el bloque de 8s (~18 a 25 palabras)
    if (currentWords.length + clauseWords.length <= 25) {
      currentWords.push(...clauseWords);
    } else {
      if (currentWords.length >= 12) {
        sceneChunks.push(currentWords.join(' '));
        currentWords = [...clauseWords];
      } else {
        // Si el buffer era menor a 12 palabras, permitimos agrupar hasta 28 palabras para evitar fragmentos huérfanos
        currentWords.push(...clauseWords);
        sceneChunks.push(currentWords.join(' '));
        currentWords = [];
      }
    }
  }

  if (currentWords.length > 0) {
    sceneChunks.push(currentWords.join(' '));
  }

  // Si quedó una última escena residual minúscula (< 7 palabras) y hay más de una, unirla con la anterior
  if (sceneChunks.length > 1) {
    const lastWordCount = sceneChunks[sceneChunks.length - 1].split(/\s+/).filter(w => w.length > 0).length;
    if (lastWordCount < 7) {
      const secondLast = sceneChunks[sceneChunks.length - 2];
      sceneChunks[sceneChunks.length - 2] = `${secondLast} ${sceneChunks[sceneChunks.length - 1]}`;
      sceneChunks.pop();
    }
  }

  const framings = [
    'Medium closeup shot strictly from chest-up, anchor center lock, high visual stability.',
    'Dynamic 15-degree off-axis broadcast framing, teleprompter eye-line alignment.',
    'Punchy snap-zoom moving smoothly toward eye-level teleprompter framing.',
    'Frontal anchor chest framing with active CRT monitor reflections.'
  ];

  const movements = [
    'Smooth lateral camera whip-in from left to center lock-on, anchor steady.',
    'Continuous subtle slow push-in dolly shot toward speaker face for 8 seconds.',
    'Tight chest-up close framing, instant snap-zoom toward anchor chest.',
    'Dynamic perspective shift snapping from off-axis to dead-center anchor posture.'
  ];

  const transitions: SceneProductionPlan['transitionType'][] = [
    'corte_directo',
    'rgb_glitch_flash',
    'push_zoom',
    'whip_pan'
  ];

  const scenes: SceneProductionPlan[] = sceneChunks.map((snippet, idx) => {
    const sWords = snippet.split(/\s+/).filter(w => w.length > 0).length;
    const estSec = Number((sWords / WORDS_PER_SECOND).toFixed(1));
    const framing = framings[idx % framings.length];
    const movement = movements[idx % movements.length];
    const transition = transitions[idx % transitions.length];

    const refsTag = assignedVisualRefIds.length > 0 
      ? `Canonical References Locked: [${assignedVisualRefIds.join(', ')}]. `
      : '';

    const compiledPrompt = 
      `Scene ${idx + 1} of news broadcast. Cinematic 8-second AI news segment for NeuralStories News featuring anchor NeuralDotAI (@neuraldotai). ` +
      `${aspectRatio === '9:16' ? 'Vertical 9:16' : 'Cinematic 16:9'} broadcast framing, ${framing} ` +
      `Anchor character identity strictly preserved: contemporary black rectangular glasses, short neat dark hair, groomed short beard, tailored dark navy tech blazer. ` +
      `${refsTag}` +
      `Setting: Vintage physical CRT monitor wall backdrop, glowing amber and cyan scanlines. ` +
      `Camera motion: ${movement} ` +
      `Anchor speech delivery cadence: Spanish Algenib profile (+18% cadence), continuous crisp delivery speaking the exact phrase: "${snippet}". ` +
      `Visual dynamics: purely optical RGB scanline glitch transition (${transition}), photorealistic broadcast studio lighting, exactly 8 seconds duration, 4k ultra-sharp.`;

    return {
      sceneIndex: idx + 1,
      scriptSnippet: snippet,
      wordCount: sWords,
      estDurationSeconds: estSec,
      recommendedFraming: framing,
      movementInstruction: movement,
      transitionType: transition,
      visualReferenceIds: assignedVisualRefIds,
      compiledPrompt
    };
  });

  const targetDurationSeconds = Math.max(8, scenes.length * 8);

  return {
    fullWordCount,
    fullEstDurationSeconds,
    targetDurationSeconds,
    scenesCount: scenes.length,
    scenes,
    paceRating: 'optimo',
    feedback: `Guion desglosado en ${scenes.length} tomas de ~8s respetando cláusulas gramaticales y vocabulario íntegro.`
  };
}