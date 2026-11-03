/**
 * Perfiles audiovisuales versionados de NeuralStories News (T400-T404).
 *
 * Componen el canon recuperado de `flow-recovery/source/constants.ts` en un
 * perfil registrable y trazable. Los identificadores son lógicos: ningún asset
 * ni URL de proveedor cruza la frontera editorial (ver AUDITORIA_CONTRATO.md).
 * Los recursos gráficos de ejemplo que trae el canon NO están licenciados
 * (RIESGOS.md R05/R07): se registran como referencia pendiente de derechos.
 */
import type { BackgroundPreset, CameraMovement, VoiceConfig } from '../studio/types';
import {
  ALGENIB_VOICE_CONFIG,
  BACKGROUND_PRESETS,
  CAMERA_MOVEMENTS_CATALOG,
  DEFAULT_MASTER_SHEET_PROMPT,
  NEURALDOTAI_CANONICAL,
} from '../studio/constants.ts';

export interface CharacterProfile {
  id: string;
  displayName: string;
  handle: string;
  show: string;
  features: { [k: string]: string };
  masterSheetPrompt: string;
  /** Procedencia del canon: código recuperado; sin assets licenciados todavía. */
  provenance: string;
  assetsLicensed: false;
}

export interface StudioProfile {
  id: string;
  presets: BackgroundPreset[];
  /** Encuadre dominante aprobado (plano cercano desde el pecho). */
  framingRule: string;
  /** Regla de glitches: a imagen y montaje, nunca rompiendo la voz. */
  glitchRule: string;
}

export interface VoiceProfile extends VoiceConfig {
  /** Indicación histórica de preferencia creativa; no es propiedad de ninguna API. */
  speedNote: string;
}

export interface AudiovisualProfile {
  profileId: string;
  version: string;
  createdAt: string;
  character: CharacterProfile;
  studio: StudioProfile;
  voice: VoiceProfile;
  movements: CameraMovement[];
  /** Limitaciones conocidas del perfil (trazabilidad y revisión humana). */
  limitations: string[];
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export const NEURALNEWS_CANON_PROFILE: AudiovisualProfile = {
  profileId: 'neuralnews-canon-v1',
  version: '1.0.0',
  createdAt: '2026-10-28',
  character: {
    id: 'neuraldotai',
    displayName: NEURALDOTAI_CANONICAL.name,
    handle: NEURALDOTAI_CANONICAL.handle,
    show: NEURALDOTAI_CANONICAL.show,
    features: clone(NEURALDOTAI_CANONICAL.features),
    masterSheetPrompt: DEFAULT_MASTER_SHEET_PROMPT,
    provenance: 'flow-recovery/source/constants.ts (canon recuperado; referencias pendientes de licencia)',
    assetsLicensed: false,
  },
  studio: {
    id: 'neuralnews-crt-studio',
    presets: clone(BACKGROUND_PRESETS),
    framingRule:
      'Predominio del plano cercano desde el pecho hacia arriba, encuadres dinámicos con estabilidad de emisión.',
    glitchRule:
      'Los glitches se aplican a imagen y montaje (RGB shift, scanlines); el audio de voz es continuo y sin interrupciones.',
  },
  voice: {
    ...clone(ALGENIB_VOICE_CONFIG),
    speedNote:
      'El multiplicador 1.18 es una preferencia creativa histórica, no una propiedad confirmada de ninguna API de síntesis.',
  },
  movements: clone(CAMERA_MOVEMENTS_CATALOG),
  limitations: [
    'Sin assets locales licenciados del personaje ni de la voz (R05/R07); pendiente de confirmación del propietario.',
    'Los presets CRT describen el plató aprobado como prompt; no hay imágenes locales verificadas.',
  ],
};

/** Registro de perfiles: el contrato de handoff referencia profileId, no assets. */
export function findProfile(profileId: string): AudiovisualProfile | undefined {
  if (profileId === NEURALNEWS_CANON_PROFILE.profileId) return NEURALNEWS_CANON_PROFILE;
  return undefined;
}

/** Fondo del estudio según el formato de salida (ids del canon en constants.ts). */
export function studioPresetForFormat(profile: AudiovisualProfile, outputFormat: '9:16' | '16:9'): BackgroundPreset {
  const wanted = outputFormat === '9:16' ? 'crt_original_vertical' : 'crt_original_wide';
  return profile.studio.presets.find((preset) => preset.id === wanted) ?? profile.studio.presets[0];
}
