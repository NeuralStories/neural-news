"use client";

import { request } from "./http";

export const api = {
  me: () => request<import("./types").Me>("/v1/auth/me"),
  demoLogin: () => request<import("./types").Me>("/v1/auth/demo", { method: "POST" }),
  logout: () => request<{ ok: boolean }>("/v1/auth/logout", { method: "POST" }),

  addSource: (payload: Record<string, unknown>, idempotencyKey?: string) =>
    request<{ source: import("./types").SourceListItem; job_id: number | null; created: boolean; message: string | null }>(
      "/v1/sources",
      { method: "POST", body: payload, idempotencyKey },
    ),
  listSources: (query = "") => request<{ total: number; items: import("./types").SourceListItem[] }>(`/v1/sources${query}`),
  getSource: (id: number) => request<import("./types").SourceDetail>(`/v1/sources/${id}`),
  processSource: (id: number) => request<{ job_id: number; created: boolean }>(`/v1/sources/${id}/process`, { method: "POST", body: JSON.stringify({}) }),
  analyzeVideo: (id: number) => request<{ job_id: number; created: boolean }>(`/v1/sources/${id}/analyze`, { method: "POST" }),
  transcribeSource: (id: number) =>
    request<{ job_id: number; created: boolean; status: string; message: string }>(
      `/v1/sources/${id}/transcribe`, { method: "POST", body: JSON.stringify({}) },
    ),
  getTranscript: (id: number) =>
    request<{ found: boolean; message?: string; content_type?: string; is_verbatim?: boolean; provider?: string; text?: string; segments?: Array<{ start_ms: number | null; end_ms: number | null; text: string; sequence: number }> }>(
      `/v1/sources/${id}/transcript`,
    ),
  addTranscript: (id: number, transcript: string) =>
    request<{ ok: boolean }>(`/v1/sources/${id}/transcript`, { method: "POST", body: JSON.stringify({ transcript }) }),

  listStories: (query = "") => request<{ total: number; items: import("./types").StoryListItem[] }>(`/v1/stories${query}`),
  getStory: (id: number) => request<import("./types").StoryDetail>(`/v1/stories/${id}`),
  research: (id: number) => request<{ job_id: number }>(`/v1/stories/${id}/research`, { method: "POST" }),
  draft: (id: number) => request<{ job_id: number }>(`/v1/stories/${id}/draft`, { method: "POST" }),
  saveScript: (id: number, content: string, expectedVersion: number) =>
    request<{ script_version: { id: number; version: number } }>(`/v1/stories/${id}/script`, {
      method: "PATCH",
      body: JSON.stringify({ content, expected_version: expectedVersion }),
    }),
  approve: (id: number, scriptVersionId: number) =>
    request<{ ok: boolean }>(`/v1/stories/${id}/approve`, { method: "POST", body: JSON.stringify({ script_version_id: scriptVersionId }) }),
  reject: (id: number, reason: string) =>
    request<{ ok: boolean }>(`/v1/stories/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  getStoryboard: (id: number) => request<import("./types").Storyboard>(`/v1/stories/${id}/storyboard`),

  createBatch: (payload: { name: string; target_size: number; story_ids: number[] }) =>
    request<{ id: number }>("/v1/batches", { method: "POST", body: JSON.stringify(payload) }),
  listBatches: () => request<{ items: { id: number; name: string; target_size: number; status: string; created_at: string }[] }>("/v1/batches"),
  getBatch: (id: number) => request<import("./types").BatchDetail>(`/v1/batches/${id}`),
  reorderBatch: (id: number, storyIds: number[]) =>
    request<{ ok: boolean }>(`/v1/batches/${id}/order`, { method: "PATCH", body: JSON.stringify({ story_ids: storyIds }) }),
  exportBatch: (id: number) => request<{ job_id: number }>(`/v1/batches/${id}/export`, { method: "POST" }),

  getJob: (id: number) => request<import("./types").JobInfo>(`/v1/jobs/${id}`),
  // Las lecturas de la consola aceptan `signal`: el ciclo nuevo aborta al
  // anterior en vuelo para que una respuesta lenta nunca pise a una fresca.
  // `consulta` lleva la paginación y los filtros del servidor (F-6): la
  // respuesta incluye el `total` real, no el recorte de la página.
  listJobs: (consulta = "", opciones?: { signal?: AbortSignal }) =>
    request<{ items: import("./types").JobInfo[]; total: number; limit: number; offset: number }>(
      `/v1/jobs${consulta}`,
      opciones,
    ),

  providerStatus: (opciones?: { signal?: AbortSignal }) =>
    request<{ demo_mode: boolean; paid_services_enabled: boolean; providers: import("./types").ProviderStatus[] }>("/v1/provider-status", opciones),
  metrics: (opciones?: { signal?: AbortSignal }) =>
    request<import("./types").RespuestaMetricas>("/v1/metrics", opciones),
  health: (opciones?: { signal?: AbortSignal }) =>
    request<import("./types").EstadoSalud>("/v1/health", opciones),
  usage: (opciones?: { signal?: AbortSignal }) =>
    request<import("./types").UsageInfo>("/v1/usage", opciones),
  updateBudget: (payload: { paid_services_enabled?: boolean; daily_limit_eur?: number }) =>
    request<Record<string, unknown>>("/v1/config/budget", { method: "PUT", body: JSON.stringify(payload) }),
  getScoreWeights: () => request<Record<string, number>>("/v1/settings/score-weights"),
  updateScoreWeights: (payload: Record<string, number>) =>
    request<Record<string, number>>("/v1/settings/score-weights", { method: "PUT", body: JSON.stringify(payload) }),
};
