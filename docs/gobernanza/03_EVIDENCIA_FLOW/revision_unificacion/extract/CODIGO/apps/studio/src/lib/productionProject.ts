/**
 * Proyecto de producción audiovisual por noticia (T405-T411).
 *
 * Convierte una noticia (título + guion aprobado) y un perfil audiovisual en un
 * plan reproducible: escenas editables de ~8 s, biblioteca de prompts por tipo
 * de escena, planificación de encuadres y transiciones, versiones guardadas y
 * verificación de consistencia. Todo local: no genera imagen, vídeo ni voz.
 */
import { splitScriptIntoScenes } from '../studio/utils/scriptAnalyzer.ts';
import type { AudiovisualProfile } from '../data/avProfiles';
import { studioPresetForFormat } from '../data/avProfiles.ts';

export type SceneType = 'apertura' | 'desarrollo' | 'cierre';
export type TransitionType = 'corte_directo' | 'rgb_glitch_flash' | 'whip_pan' | 'push_zoom';

export interface ProductionScene {
  sceneIndex: number;
  sceneType: SceneType;
  /** Texto del guion que se locuta en la escena (editable). */
  scriptSnippet: string;
  /** Prompt de imagen para la escena (editable). */
  imagePrompt: string;
  framing: string;
  movement: string;
  transition: TransitionType;
  estDurationSeconds: number;
  referenceIds: string[];
}

export interface ProductionProject {
  projectId: string;
  storyRef: { storyId: string; title: string; revision: number | null };
  profileId: string;
  profileVersion: string;
  outputFormat: '9:16' | '16:9';
  studioPresetId: string;
  voice: { profile: string; locale: string; speedMultiplier: number; speedNote: string };
  createdAt: string;
  /** Versión interna del plan; sube con cada edición guardada. */
  planVersion: number;
  scenes: ProductionScene[];
  /** Avisos de consistencia calculados al crear o editar (no bloquean editar). */
  warnings: string[];
}

export interface ArticleLike {
  id: string;
  title: string;
  fullScript: string;
  metadata?: { externalId?: string };
}

const WORDS_PER_SECOND = 2.85; // mismo ritmo que utils/scriptAnalyzer.ts

/** Biblioteca de prompts por tipo de escena (T407). Determinista y editable. */
export const SCENE_PROMPT_TEMPLATES: Record<SceneType, (ctx: PromptContext) => string> = {
  apertura: (ctx) =>
    `Plano cercano desde el pecho de ${ctx.characterName} (${ctx.characterHandle}) en el plató CRT, ${ctx.studioDescriptor}. ` +
    `Entrada dinámica de cámara: ${ctx.movement}. Presenta el titular con energía de presentador de noticias: «${ctx.snippet}». ` +
    `Glitch sutil de RGB y scanlines solo en imagen, voz continua e ininterrumpida. ${ctx.formatInstruction}. Sin marcas ni logotipos reales.`,
  desarrollo: (ctx) =>
    `Plano cercano desde el pecho de ${ctx.characterName} señalando hacia la pantalla CRT lateral, ${ctx.studioDescriptor}. ` +
    `Cámara: ${ctx.movement}. Narra el dato con ritmo dinámico: «${ctx.snippet}». ` +
    `Glitch analógico breve de transición al final de la toma, sin cortar el audio. ${ctx.formatInstruction}.`,
  cierre: (ctx) =>
    `Plano cercano desde el pecho de ${ctx.characterName} con gesto de cierre y mirada a cámara, ${ctx.studioDescriptor}. ` +
    `Cámara: ${ctx.movement}. Despedida con dictación clara: «${ctx.snippet}». ` +
    `Flash de glitch RGB al corte final; la locución no se interrumpe. ${ctx.formatInstruction}.`,
};

export interface PromptContext {
  characterName: string;
  characterHandle: string;
  studioDescriptor: string;
  movement: string;
  snippet: string;
  formatInstruction: string;
}

const MOVEMENT_BY_TYPE: Record<SceneType, string> = {
  apertura: 'lateral_slide_in',
  desarrollo: 'subtle_dolly',
  cierre: 'chest_punch_zoom',
};

const TRANSITION_BY_TYPE: Record<SceneType, TransitionType> = {
  apertura: 'whip_pan',
  desarrollo: 'corte_directo',
  cierre: 'rgb_glitch_flash',
};

function sceneTypeFor(index: number, total: number): SceneType {
  if (index === 1) return 'apertura';
  if (index === total) return 'cierre';
  return 'desarrollo';
}

function movementInstruction(profile: AudiovisualProfile, movementId: string): string {
  const movement = profile.movements.find((m) => m.id === movementId) ?? profile.movements[0];
  return movement ? movement.promptInstruction : 'Cámara estable, plano fijo.';
}

function formatInstruction(outputFormat: '9:16' | '16:9'): string {
  return outputFormat === '9:16'
    ? 'Composición vertical 9:16 con el presentador centrado'
    : 'Composición horizontal 16:9 de emisión clásica';
}

/** Proyecto determinista: mismos datos de entrada → mismo plan (salvo fechas). */
export function createProductionProject(
  article: ArticleLike,
  profile: AudiovisualProfile,
  options: { outputFormat?: '9:16' | '16:9' } = {}
): ProductionProject {
  const outputFormat = options.outputFormat ?? '9:16';
  const preset = studioPresetForFormat(profile, outputFormat);
  const analysis = splitScriptIntoScenes(article.fullScript, [], outputFormat);
  const scenes: ProductionScene[] = analysis.scenes.map((scene) => {
    const sceneType = sceneTypeFor(scene.sceneIndex, analysis.scenes.length);
    const movementId = MOVEMENT_BY_TYPE[sceneType];
    const ctx: PromptContext = {
      characterName: profile.character.displayName,
      characterHandle: profile.character.handle,
      studioDescriptor: preset.promptDescriptor,
      movement: movementInstruction(profile, movementId),
      snippet: scene.scriptSnippet,
      formatInstruction: formatInstruction(outputFormat),
    };
    return {
      sceneIndex: scene.sceneIndex,
      sceneType,
      scriptSnippet: scene.scriptSnippet,
      imagePrompt: SCENE_PROMPT_TEMPLATES[sceneType](ctx),
      framing: profile.studio.framingRule,
      movement: movementId,
      transition: TRANSITION_BY_TYPE[sceneType],
      estDurationSeconds: scene.estDurationSeconds,
      referenceIds: [],
    };
  });

  return {
    projectId: `proj-${article.id}-${outputFormat.replace(':', 'x')}`,
    storyRef: {
      storyId: article.id,
      title: article.title,
      revision: parseRevision(article.metadata?.externalId),
    },
    profileId: profile.profileId,
    profileVersion: profile.version,
    outputFormat,
    studioPresetId: preset.id,
    voice: {
      profile: profile.voice.profile,
      locale: profile.voice.locale,
      speedMultiplier: profile.voice.speedMultiplier,
      speedNote: profile.voice.speedNote,
    },
    createdAt: new Date().toISOString(),
    planVersion: 1,
    scenes,
    warnings: checkConsistency(
      {
        projectId: '',
        storyRef: { storyId: article.id, title: article.title, revision: null },
        profileId: profile.profileId,
        profileVersion: profile.version,
        outputFormat,
        studioPresetId: preset.id,
        voice: {
          profile: profile.voice.profile,
          locale: profile.voice.locale,
          speedMultiplier: profile.voice.speedMultiplier,
          speedNote: profile.voice.speedNote,
        },
        createdAt: '',
        planVersion: 1,
        scenes,
        warnings: [],
      },
      profile
    ).warnings,
  };
}

function parseRevision(_externalId?: string): number | null {
  // externalId puede traer "handoff:<handoff_id>:<story_id>"; la revisión no viaja
  // en el artículo de Studio, así que se deja nula si no es derivable.
  return null;
}

/** Edición de una escena (T406/T409): copia inmutable con planVersion + 1. */
export function applySceneEdit(
  project: ProductionProject,
  sceneIndex: number,
  edits: { scriptSnippet?: string; imagePrompt?: string }
): ProductionProject {
  const scenes = project.scenes.map((scene) =>
    scene.sceneIndex === sceneIndex
      ? {
          ...scene,
          scriptSnippet: edits.scriptSnippet?.trim() ? edits.scriptSnippet.trim() : scene.scriptSnippet,
          imagePrompt: edits.imagePrompt?.trim() ? edits.imagePrompt.trim() : scene.imagePrompt,
        }
      : scene
  );
  return { ...project, scenes, planVersion: project.planVersion + 1 };
}

/** Verificación de consistencia personaje/escenario/voz (T411). */
export function checkConsistency(
  project: ProductionProject,
  profile: AudiovisualProfile
): { ok: boolean; warnings: string[] } {
  const warnings: string[] = [];
  if (project.profileId !== profile.profileId) {
    warnings.push(`El proyecto usa el perfil ${project.profileId} pero se verifica contra ${profile.profileId}.`);
  }
  if (!project.voice.profile) warnings.push('El proyecto no tiene voz configurada.');
  if (project.scenes.length === 0) warnings.push('El plan no tiene escenas: revisa el guion de la noticia.');
  for (const scene of project.scenes) {
    if (!scene.scriptSnippet.trim()) {
      warnings.push(`La escena ${scene.sceneIndex} no tiene texto de locución.`);
    }
    if (!scene.imagePrompt.trim()) {
      warnings.push(`La escena ${scene.sceneIndex} no tiene prompt de imagen.`);
    }
    if (!profile.movements.some((m) => m.id === scene.movement)) {
      warnings.push(`La escena ${scene.sceneIndex} usa un movimiento fuera del catálogo del perfil.`);
    }
  }
  const totalSeconds = project.scenes.reduce((sum, s) => sum + s.estDurationSeconds, 0);
  if (totalSeconds > 120) {
    warnings.push(
      `El plan dura ~${Math.round(totalSeconds)} s; revisa si la noticia necesita dividirse en más tomas.`
    );
  }
  return { ok: warnings.length === 0, warnings };
}

/** Serialización reproducible del plan para guardar, versionar o descargar. */
export function exportProjectJson(project: ProductionProject): string {
  return JSON.stringify(project, null, 2);
}

// ---------------------------------------------------------------- versiones (T410)

const PROJECTS_KEY = 'nn-production-projects-v1';

export interface ProjectVersionRecord {
  planVersion: number;
  savedAt: string;
  project: ProductionProject;
}

export interface ProjectVersionStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function memoryStore(): ProjectVersionStore {
  const map = new Map<string, string>();
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => {
      map.set(key, value);
    },
  };
}

export const defaultStore: ProjectVersionStore =
  typeof localStorage !== 'undefined' ? localStorage : memoryStore();

function readAll(store: ProjectVersionStore): Record<string, ProjectVersionRecord[]> {
  try {
    const parsed = JSON.parse(store.getItem(PROJECTS_KEY) ?? '{}');
    return typeof parsed === 'object' && parsed !== null ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(all: Record<string, ProjectVersionRecord[]>, store: ProjectVersionStore): void {
  store.setItem(PROJECTS_KEY, JSON.stringify(all, null, 2));
}

export function saveProjectVersion(project: ProductionProject, store: ProjectVersionStore = defaultStore): ProjectVersionRecord[] {
  const all = readAll(store);
  const versions = all[project.projectId] ?? [];
  versions.push({ planVersion: project.planVersion, savedAt: new Date().toISOString(), project });
  all[project.projectId] = versions;
  writeAll(all, store);
  return versions;
}

export function loadProjectVersions(projectId: string, store: ProjectVersionStore = defaultStore): ProjectVersionRecord[] {
  return readAll(store)[projectId] ?? [];
}

export function totalEstimatedSeconds(project: ProductionProject): number {
  return Number(project.scenes.reduce((sum, s) => sum + s.estDurationSeconds, 0).toFixed(1));
}

export { WORDS_PER_SECOND };
