'use client';

/**
 * Cliente de la API de proyectos (NN-107 F1) para el Studio integrado.
 * Misma origen (`/api/v1/...`, proxada por next.config.ts): una sola cookie,
 * una sola base de datos, ninguna redacción paralela.
 */

export interface ProjectStepState {
  revision: number;
  payload: Record<string, unknown>;
}

export interface ProjectSummary {
  id: number;
  name: string;
  story_id: number | null;
  ratio: '9:16' | '16:9';
  status: string;
  step_revisions: Record<string, number>;
  story?: { id: number; title: string; status: string };
  created_at: string;
  updated_at: string;
}

export interface ProjectFull extends ProjectSummary {
  steps: Record<string, ProjectStepState>;
  beats: Array<Record<string, unknown>>;
  shots: Array<Record<string, unknown>>;
  takes: Array<{
    id: number;
    shot_id: number | null;
    take_number: number;
    status: string;
    imported_media: Record<string, unknown> | null;
    prompt_versions: number;
  }>;
}

export class ProjectConflict extends Error {
  readonly currentRevision: number;
  constructor(currentRevision: number) {
    super('Revisión obsoleta: el proyecto cambió en el servidor.');
    this.name = 'ProjectConflict';
    this.currentRevision = currentRevision;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: init?.body && !(init.body instanceof FormData)
      ? { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
      : init?.headers,
    ...init,
  });
  if (response.status === 409) {
    const detail = (await response.json().catch(() => null))?.detail;
    throw new ProjectConflict(Number(detail?.current_revision ?? 0));
  }
  if (!response.ok) {
    const detail = (await response.json().catch(() => null))?.detail;
    const message =
      typeof detail === 'string' ? detail : detail?.message ?? `Error ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const projectApi = {
  list: () => call<{ total: number; items: ProjectSummary[] }>('/api/v1/projects'),
  get: (id: number) => call<ProjectFull>(`/api/v1/projects/${id}`),
  create: (body: { name: string; ratio: '9:16' | '16:9'; story_id?: number | null; target_duration_s?: number | null }) =>
    call<ProjectSummary>('/api/v1/projects', { method: 'POST', body: JSON.stringify(body) }),
  saveStep: (id: number, step: string, payload: Record<string, unknown>, expectedRevision: number) =>
    call<{ step: string; revision: number; story_id: number | null }>(
      `/api/v1/projects/${id}/studio/${step}`,
      { method: 'PUT', body: JSON.stringify({ payload, expected_revision: expectedRevision }) },
    ),
  linkStory: (id: number, storyId: number) =>
    call<ProjectSummary>(`/api/v1/projects/${id}/link-story`, {
      method: 'POST',
      body: JSON.stringify({ story_id: storyId }),
    }),
  listStories: () =>
    call<{ total: number; items: Array<{ id: number; title: string; status: string }> }>(
      '/api/v1/stories?limit=100',
    ),
  createTake: (id: number, shotId: number | null, takeNumber: number) =>
    call<{ id: number; status: string }>(`/api/v1/projects/${id}/takes`, {
      method: 'POST',
      body: JSON.stringify({ shot_id: shotId, take_number: takeNumber }),
    }),
  uploadTakeMedia: (id: number, takeId: number, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return call<{ take_id: number; status: string; media: Record<string, unknown>; probe_job_id?: number }>(
      `/api/v1/projects/${id}/takes/${takeId}/media`,
      { method: 'POST', body: form },
    );
  },
  approveTake: (id: number, takeId: number, status: 'APROBADA' | 'RECHAZADA') =>
    call<{ take_id: number; status: string }>(`/api/v1/projects/${id}/takes/${takeId}/approval`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),
  savePrompt: (
    id: number,
    body: {
      take_id: number | null;
      prompt_en: string;
      explanation_es?: string;
      constraints?: string[];
      attachments_manifest?: Array<Record<string, unknown>>;
      checklist?: Record<string, unknown>;
    },
  ) =>
    call<{ prompt_id: number; version: number; content_hash: string; take_status: string | null }>(
      `/api/v1/projects/${id}/prompts`,
      { method: 'POST', body: JSON.stringify(body) },
    ),
  importTakeMediaFile: (id: number, takeId: number, file: File) =>
    projectApi.uploadTakeMedia(id, takeId, file),
  directorPlan: (id: number, providerMaxClipS = 8) =>
    call<{
      beats: Array<Record<string, unknown>>;
      shots: Array<Record<string, unknown>>;
      total_seconds: number;
      provider_max_clip_s: number;
      note: string;
    }>(`/api/v1/projects/${id}/director/plan`, {
      method: "POST",
      body: JSON.stringify({ provider_max_clip_s: providerMaxClipS }),
    }),
  flowPackage: (id: number, takeId: number) =>
    call<Record<string, unknown>>(`/api/v1/projects/${id}/takes/${takeId}/flow-package`),
};
