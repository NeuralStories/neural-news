/**
 * Consumidor del contrato `production_handoff.v1` para NeuralStories Studio.
 *
 * Espejo en TypeScript del consumidor Python (`packages/contracts/consumer/`):
 * valida el documento contra el mismo JSON Schema (canon en
 * `packages/contracts/production_handoff.v1.schema.json`), recomputa el SHA-256
 * del guion aprobado y rechaza traspasos duplicados. No depende del motor
 * editorial y no eleva aprobaciones: el documento sólo puede provenir del
 * productor del backend, que ya verificó la aprobación en base de datos.
 *
 * El módulo no contiene imports de navegador: funciona también bajo Node
 * (las pruebas lo usan con inyección de almacenamiento en memoria).
 */
import Ajv2020, { type ValidateFunction } from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import type { NewsArticle } from '../../types';

export const SCHEMA_VERSION = 'production_handoff.v1';

export class HandoffValidationError extends Error {}
export class DuplicateHandoffError extends Error {}

export interface HandoffSource {
  title?: string | null;
  url?: string | null;
  accessed_at: string;
  provider?: string | null;
  external_id?: string | null;
  relevance?: string | null;
  published_at?: string | null;
}

export interface HandoffStory {
  story_id: string;
  revision: number;
  title: string;
  summary: string;
  language: string;
  approved_script: string;
  script_version_id: number;
  content_hash: string;
  sources: HandoffSource[];
  storyboard?: unknown[] | null;
  editorial_approval: { status: 'approved'; approved_by: string; approved_at: string };
}

export interface HandoffDocument {
  schema_version: string;
  handoff_id: string;
  created_at: string;
  mode: 'single' | 'batch';
  output_format: string;
  style_profile: Record<string, string>;
  stories: HandoffStory[];
}

export interface RegistryEntry {
  handoff_id: string;
  imported_at: string;
  mode: string;
  stories: { story_id: string; revision: number }[];
}

export interface RegistryStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function memoryStore(): RegistryStore {
  const map = new Map<string, string>();
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => {
      map.set(key, value);
    },
  };
}

const REGISTRY_KEY = 'nn-handoff-registry-v1';

/** Almacenamiento por defecto: localStorage en el navegador, memoria en Node. */
export const defaultStore: RegistryStore =
  typeof localStorage !== 'undefined'
    ? localStorage
    : /* navegador */ memoryStore();

export function loadRegistry(store: RegistryStore = defaultStore): RegistryEntry[] {
  const raw = store.getItem(REGISTRY_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed?.entries) ? parsed.entries : [];
  } catch {
    return [];
  }
}

export function saveRegistry(entries: RegistryEntry[], store: RegistryStore = defaultStore): void {
  store.setItem(REGISTRY_KEY, JSON.stringify({ entries }, null, 2));
}

function compileValidator(schema: object): ValidateFunction<HandoffDocument> {
  // Draft 2020-12 (el esquema canónico declara ese metaschema). strict:false
  // sólo silencia avisos de estilo de ajv; no cambia la validación.
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  return ajv.compile<HandoffDocument>(schema);
}

async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
}

async function verifyStoryIntegrity(story: HandoffStory): Promise<void> {
  const expected = await sha256Hex(story.approved_script);
  if (expected !== story.content_hash) {
    throw new HandoffValidationError(
      `La noticia ${story.story_id} (revisión ${story.revision}) llegó con el guion alterado: ` +
        'el hash de contenido no coincide. Se rechaza para no producir sobre un texto que ' +
        'editorial no aprobó.'
    );
  }
}

export interface ImportOptions {
  /** JSON Schema compilable (el canon vive en packages/contracts). */
  schema: object;
  store?: RegistryStore;
}

export interface ImportedHandoff {
  handoffId: string;
  mode: string;
  /** Noticias ya mapeadas al modelo de Studio (sin id ni orderIndex). */
  articles: Omit<NewsArticle, 'id' | 'orderIndex'>[];
}

function sourceLabel(source: HandoffSource): string {
  if (source.url) return source.url;
  if (source.external_id) return `${source.provider ?? 'fuente'}:${source.external_id}`;
  return `manual:${source.title ?? 'sin identificador'}`;
}

export function storyToArticle(story: HandoffStory, handoffId: string): Omit<NewsArticle, 'id' | 'orderIndex'> {
  return {
    title: story.title,
    summary: story.summary,
    fullScript: story.approved_script,
    date: new Date().toISOString().slice(0, 10),
    // R-BUG-3: la aprobación del guion no es verificación de afirmaciones;
    // el estado real vive en el motor editorial (claims) y llega como en_revision.
    verificationStatus: 'en_revision',
    approvalStatus: 'aprobada',
    sources: story.sources.map(sourceLabel),
    editorialReferenceIds: [],
    visualReferenceIds: [],
    tags: ['traspaso', `revision-${story.revision}`, story.language],
    metadata: {
      importedFrom: 'batch_json',
      externalId: `handoff:${handoffId}:${story.story_id}`,
      verifiedBy: story.editorial_approval.approved_by,
    },
  };
}

/**
 * Valida, verifica y acepta un traspaso. Devuelve las noticias listas para la
 * redacción de Studio. Lanza `HandoffValidationError` (contrato o integridad) y
 * `DuplicateHandoffError` (ya importado). El registro sólo se escribe si todo
 * el documento es válido.
 */
export async function importHandoff(
  document: unknown,
  options: ImportOptions
): Promise<ImportedHandoff> {
  if (
    typeof document !== 'object' ||
    document === null ||
    (document as { schema_version?: string }).schema_version !== SCHEMA_VERSION
  ) {
    throw new HandoffValidationError(`Este estudio sólo acepta documentos «${SCHEMA_VERSION}».`);
  }
  const validate = compileValidator(options.schema);
  if (!validate(document)) {
    const first = validate.errors?.[0];
    const location = first ? first.instancePath || '(raíz)' : '(raíz)';
    throw new HandoffValidationError(
      `El traspaso no cumple el contrato ${SCHEMA_VERSION} en «${location}»: ${first?.message ?? 'formato no válido'}`
    );
  }
  const doc = document as HandoffDocument;
  for (const story of doc.stories) {
    await verifyStoryIntegrity(story);
  }

  const store = options.store ?? defaultStore;
  const entries = loadRegistry(store);
  if (entries.some((entry) => entry.handoff_id === doc.handoff_id)) {
    throw new DuplicateHandoffError(
      `El traspaso ${doc.handoff_id} ya se había importado: no se vuelve a cargar.`
    );
  }
  for (const story of doc.stories) {
    const previous = entries.find((entry) =>
      entry.stories.some(
        (item) => item.story_id === story.story_id && item.revision === story.revision
      )
    );
    if (previous && previous.handoff_id !== doc.handoff_id) {
      throw new DuplicateHandoffError(
        `La noticia ${story.story_id} revisión ${story.revision} ya llegó en el traspaso ` +
          `${previous.handoff_id}: no se importa dos veces.`
      );
    }
  }

  entries.push({
    handoff_id: doc.handoff_id,
    imported_at: new Date().toISOString(),
    mode: doc.mode,
    stories: doc.stories.map((s) => ({ story_id: s.story_id, revision: s.revision })),
  });
  saveRegistry(entries, store);

  return {
    handoffId: doc.handoff_id,
    mode: doc.mode,
    articles: doc.stories.map((story) => storyToArticle(story, doc.handoff_id)),
  };
}
