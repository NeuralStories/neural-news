export interface SourceFileMetadata {
  path: string;
  category: 'core' | 'types' | 'constants' | 'component' | 'util';
  description: string;
}

export const REAL_SOURCE_METADATA: Record<string, SourceFileMetadata> = {
  "types.ts": {
    category: 'types',
    description: 'Definiciones de modelos editoriales, escenas de 8s, referencias y contratos de producción'
  },
  "constants.ts": {
    category: 'constants',
    description: 'Presets canónicos de NeuralDotAI, plató CRT, voz Algenib y catálogo de movimientos'
  },
  "utils/scriptAnalyzer.ts": {
    category: 'util',
    description: 'Algoritmo de segmentación de guion continuo en tomas canónicas de 8 segundos a 2.85 pal/s'
  },
  "utils/newsDeduplication.ts": {
    category: 'util',
    description: 'Motor multidimensional de detección de duplicados (IDs, URLs normalizadas, similitud Jaccard)'
  },
  "components/TopNavigation.tsx": {
    category: 'component',
    description: 'Barra de navegación principal con las 8 pestañas y botón directo de descarga de código'
  },
  "components/NewsEditorialTab.tsx": {
    category: 'component',
    description: 'Pestaña 1: Redacción editorial, ingestión por lotes y validación de fuentes'
  },
  "components/CharacterSheetTab.tsx": {
    category: 'component',
    description: 'Pestaña 2: Hoja de personaje maestra de 3 paneles y generador Nano Banana Pro'
  },
  "components/BackgroundTab.tsx": {
    category: 'component',
    description: 'Pestaña 3: Configuración de plató CRT original y selector 16:9 / 9:16'
  },
  "components/ScriptTab.tsx": {
    category: 'component',
    description: 'Pestaña 4: Desglose léxico y edición de tomas de 8s con verificación de integridad'
  },
  "components/VoiceTab.tsx": {
    category: 'component',
    description: 'Pestaña 5: Configuración de voz Algenib (+18% velocidad) y directrices de modulación'
  },
  "components/MovementTab.tsx": {
    category: 'component',
    description: 'Pestaña 6: Movimientos ópticos y cinematográficos de 8 segundos'
  },
  "components/ReferencesTab.tsx": {
    category: 'component',
    description: 'Pestaña 7: Biblioteca dual de referencias audiovisuales vs editoriales'
  },
  "components/ResultTab.tsx": {
    category: 'component',
    description: 'Pestaña 8: Paquete de producción audiovisual, compilación de prompts y render Omni 1.1 Flash'
  },
  "components/HelpModal.tsx": {
    category: 'component',
    description: 'Manual de usuario y especificación formal del contrato de integración neural.news'
  },
  "components/BackupModal.tsx": {
    category: 'component',
    description: 'Centro de mantenimiento, verificación de integridad SHA-256 y descarga JSON'
  },
  "App.tsx": {
    category: 'core',
    description: 'Componente raíz del estudio con orquestación de estado y persistencia'
  }
};

/**
 * Calcula el hash SHA-256 hexadecimal de una cadena UTF-8 en el navegador.
 */
export async function computeSha256(content: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(content);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}