"use client";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  if (response.status === 401) {
    const error = new Error("Sesión no iniciada");
    (error as Error & { status?: number }).status = 401;
    throw error;
  }
  if (!response.ok) {
    let detail = "Ha ocurrido un error inesperado";
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : data.detail?.message || JSON.stringify(data.detail ?? data);
    } catch {
      /* respuesta sin JSON */
    }
    const error = new Error(detail);
    (error as Error & { status?: number }).status = response.status;
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<import("./types").Me>("/v1/auth/me"),
  demoLogin: () => request<import("./types").Me>("/v1/auth/demo", { method: "POST" }),
  logout: () => request<{ ok: boolean }>("/v1/auth/logout", { method: "POST" }),

  addSource: (payload: Record<string, unknown>, idempotencyKey?: string) =>
    request<{ source: import("./types").SourceListItem; job_id: number | null; created: boolean; message: string | null }>(
      "/v1/sources",
      { method: "POST", body: JSON.stringify(payload), headers: { "Content-Type": "application/json", ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}) } },
    ),
  listSources: (query = "") => request<{ total: number; items: import("./types").SourceListItem[] }>(`/v1/sources${query}`),
  getSource: (id: number) => request<import("./types").SourceDetail>(`/v1/sources/${id}`),
  processSource: (id: number) => request<{ job_id: number; created: boolean }>(`/v1/sources/${id}/process`, { method: "POST", body: JSON.stringify({}) }),
  analyzeVideo: (id: number) => request<{ job_id: number; created: boolean }>(`/v1/sources/${id}/analyze`, { method: "POST" }),
  addTranscript: (id: number, transcript: string) =>
    request<{ ok: boolean }>(`/v1/sources/${id}/transcript`, { method: "POST", body: JSON.stringify({ transcript }) }),

  listStories: (query = "") =>
    request<import("./types").StoryListResponse>(`/v1/stories${query ? `?${query}` : ""}`),
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
  getHandoff: (id: number) => request<Record<string, unknown>>(`/v1/stories/${id}/handoff`),

  createBatch: (payload: { name: string; target_size: number; story_ids: number[] }) =>
    request<{ id: number }>("/v1/batches", { method: "POST", body: JSON.stringify(payload) }),
  listBatches: () => request<{ items: { id: number; name: string; target_size: number; status: string; created_at: string }[] }>("/v1/batches"),
  getBatch: (id: number) => request<import("./types").BatchDetail>(`/v1/batches/${id}`),
  reorderBatch: (id: number, storyIds: number[]) =>
    request<{ ok: boolean }>(`/v1/batches/${id}/order`, { method: "PATCH", body: JSON.stringify({ story_ids: storyIds }) }),
  updateBatchBudget: (id: number, limitEur: number | null) =>
    request<import("./types").BatchBudgetSummary>(`/v1/batches/${id}/budget`, {
      method: "PUT",
      body: JSON.stringify({ limit_eur: limitEur }),
    }),
  exportBatch: (id: number) => request<{ job_id: number }>(`/v1/batches/${id}/export`, { method: "POST" }),

  getJob: (id: number) => request<import("./types").JobInfo>(`/v1/jobs/${id}`),
  listJobs: () => request<{ items: import("./types").JobInfo[] }>("/v1/jobs"),

  providerStatus: () =>
    request<{ demo_mode: boolean; paid_services_enabled: boolean; providers: import("./types").ProviderStatus[] }>("/v1/provider-status"),
  usage: () => request<import("./types").UsageInfo>("/v1/usage"),
  updateBudget: (payload: { paid_services_enabled?: boolean; daily_limit_eur?: number }) =>
    request<Record<string, unknown>>("/v1/config/budget", { method: "PUT", body: JSON.stringify(payload) }),
  getScoreWeights: () => request<Record<string, number>>("/v1/settings/score-weights"),
  updateScoreWeights: (payload: Record<string, number>) =>
    request<Record<string, number>>("/v1/settings/score-weights", { method: "PUT", body: JSON.stringify(payload) }),
};
