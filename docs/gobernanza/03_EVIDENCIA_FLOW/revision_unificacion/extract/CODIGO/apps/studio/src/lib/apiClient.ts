/**
 * Cliente de la API editorial (apps/api) para Studio.
 *
 * Sesión: el backend expone un acceso rápido de demostración (POST /api/v1/auth/demo)
 * que deja una cookie HttpOnly; todas las llamadas viajan con credenciales.
 * Por defecto se usa la misma origen (Vite hace de proxy de /api hacia el API
 * local en 8000); con VITE_API_URL puede apuntarse a otra base.
 */
const API_URL: string = (import.meta.env?.VITE_API_URL as string | undefined) ?? '';

export class ApiNotReachableError extends Error {}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

async function call(path: string, init: RequestInit = {}): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
      ...init,
    });
  } catch {
    throw new ApiNotReachableError(
      'No se pudo conectar con el motor editorial. Arranca la API local (neuralnews-api) e inténtalo de nuevo.'
    );
  }
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body?.detail ?? body);
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json();
}

/**
 * Sesión: primero se consulta la sesión existente. Sólo si no hay ninguna y el
 * backend está en modo DEMO se inicia una sesión demo. Nunca se sustituye una
 * sesión administrativa válida por una demo.
 */
let sessionChecked: 'unknown' | 'ok' | 'demo' | 'none' = 'unknown';

async function ensureSession(): Promise<void> {
  if (sessionChecked === 'ok' || sessionChecked === 'demo') return;
  try {
    const me = await call('/api/v1/auth/me');
    const info = me as { actor_id?: string; is_demo?: boolean };
    sessionChecked = info?.is_demo ? 'demo' : 'ok';
    return;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      // Sin sesión: se intenta la entrada rápida demo (sólo existe en modo demo).
      await call('/api/v1/auth/demo', { method: 'POST' });
      sessionChecked = 'demo';
      return;
    }
    throw err;
  }
}

/** Estado de la sesión actual para la interfaz. */
export async function sessionState(): Promise<'admin' | 'demo' | 'none'> {
  try {
    const me = await call('/api/v1/auth/me');
    const info = me as { is_demo?: boolean };
    sessionChecked = info?.is_demo ? 'demo' : 'ok';
    return info?.is_demo ? 'demo' : 'admin';
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      sessionChecked = 'none';
      return 'none';
    }
    throw err;
  }
}

export interface RenderJobInfo {
  job_id: number;
  created: boolean;
  fingerprint: string;
  message: string;
}

export interface RenderSummary {
  render_id: number;
  job_id: number;
  project_id: string;
  output_format: string;
  duration_s: number;
  scene_count: number;
  sha256: string;
  created_at: string;
}

/** Encola la composición del plan y devuelve el trabajo asociado. */
export async function requestRender(plan: unknown): Promise<RenderJobInfo> {
  await ensureSession();
  return call('/api/v1/av/render', { method: 'POST', body: JSON.stringify(plan) }) as Promise<RenderJobInfo>;
}

export async function getJob(jobId: number): Promise<{ status: string; progress?: string; error?: string }> {
  return call(`/api/v1/jobs/${jobId}`) as Promise<{ status: string; progress?: string; error?: string }>;
}

export async function listRenders(projectId: string): Promise<{ total: number; items: RenderSummary[] }> {
  await ensureSession();
  return call(`/api/v1/av/renders?project_id=${encodeURIComponent(projectId)}`) as Promise<{
    total: number;
    items: RenderSummary[];
  }>;
}

/** Trae el traspaso production_handoff.v1 de una noticia directamente del motor editorial. */
export async function fetchStoryHandoff(storyId: number): Promise<Record<string, unknown>> {
  await ensureSession();
  return call(`/api/v1/stories/${storyId}/handoff`) as Promise<Record<string, unknown>>;
}

/** Descarga el vídeo compuesto como blob local (para guardar con «Guardar como»). */
export async function downloadRender(renderId: number, filename: string): Promise<void> {
  await ensureSession();
  const response = await fetch(`${API_URL}/api/v1/av/renders/${renderId}`, { credentials: 'include' });
  if (!response.ok) throw new ApiError(`No se pudo descargar el vídeo (error ${response.status}).`, response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function pollJobUntilSettled(
  jobId: number,
  { intervalMs = 2000, timeoutMs = 300000, onTick }: {
    intervalMs?: number;
    timeoutMs?: number;
    onTick?: (status: string) => void;
  } = {}
): Promise<{ status: string; progress?: string; error?: string }> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const job = await getJob(jobId);
    onTick?.(job.status);
    if (job.status === 'DONE' || job.status === 'FAILED') return job;
    if (Date.now() > deadline) {
      throw new ApiError('La composición está tardando demasiado; revisa el estado del trabajo más tarde.', 408);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export { API_URL };
