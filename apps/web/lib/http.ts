"use client";

/**
 * Cliente HTTP único de la web (NN-113.4).
 *
 * Antes convivían **tres** formas de llamar a la API con **dos** modelos de
 * error distintos:
 *   - `lib/api.ts` (su propio `request`);
 *   - `features/studio/lib/projectApi.ts` (su propio `call`, con `ProjectConflict`);
 *   - `fetch` a mano en `ProductionVertical.tsx`.
 *
 * Ahora todo pasa por aquí: un solo cliente, un solo modelo de error
 * (`ApiError`) y un solo tratamiento de los 401.
 */

/** Error de API con el estado HTTP y el detalle del servidor. */
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  /** Detalle estructurado que devuelve el servidor (p. ej. `missing`). */
  readonly detail?: unknown;

  constructor(
    message: string,
    status: number,
    options: { code?: string; detail?: unknown } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = options.code;
    this.detail = options.detail;
  }

  /** ¿Es un conflicto de versión (edición optimista)? */
  get esConflicto(): boolean {
    return this.status === 409;
  }
}

/** Mensaje legible a partir de la respuesta del servidor. */
function mensajeDe(detail: unknown, porDefecto: string): string {
  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object") {
    const d = detail as { message?: unknown; detail?: unknown };
    if (typeof d.message === "string" && d.message) return d.message;
    if (typeof d.detail === "string" && d.detail) return d.detail;
  }
  return porDefecto;
}

export type Peticion = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown>;
  /** Cabecera `Idempotency-Key` (altamente opcional). */
  idempotencyKey?: string;
};

/**
 * Llama a la API y devuelve el JSON tipado.
 *
 * Lanza `ApiError` con el estado y el detalle del servidor. Un 401 significa
 * «sesión no iniciada» y se distingue por `status === 401`.
 */
export async function request<T>(path: string, init: Peticion = {}): Promise<T> {
  const { body, idempotencyKey, headers, ...resto } = init;
  const cabeceras = new Headers(headers);
  let cuerpo: BodyInit | undefined;
  if (body !== undefined) {
    if (body instanceof FormData || body instanceof Blob) {
      // El navegador pone su propio `Content-Type` (límite de archivo incluido).
      cuerpo = body;
    } else if (typeof body === "string") {
      // Un cuerpo de texto en esta API siempre es JSON.
      cabeceras.set("Content-Type", "application/json");
      cuerpo = body;
    } else {
      cabeceras.set("Content-Type", "application/json");
      cuerpo = JSON.stringify(body);
    }
  }
  if (idempotencyKey) cabeceras.set("Idempotency-Key", idempotencyKey);

  const url = path.startsWith("/api") ? path : `/api${path}`;
  const respuesta = await fetch(url, {
    credentials: "same-origin",
    ...resto,
    headers: cabeceras,
    body: cuerpo,
  });

  if (respuesta.status === 204) return undefined as T;

  const texto = await respuesta.text();
  let datos: unknown = undefined;
  if (texto) {
    try {
      datos = JSON.parse(texto);
    } catch {
      datos = texto;
    }
  }

  if (!respuesta.ok) {
    const detalle = (datos as { detail?: unknown } | undefined)?.detail ?? datos;
    throw new ApiError(mensajeDe(detalle, `Error ${respuesta.status}`), respuesta.status, {
      detail: detalle,
    });
  }

  return datos as T;
}

/** URL de un recurso de la API (para `fetch` directo a ficheros, p. ej. `<img>`). */
export function urlDeApi(path: string): string {
  return `/api${path}`;
}

/**
 * Clave de idempotencia **derivada del contenido** (NN-113.11).
 *
 * Antes la clave era `web-${Date.now()}-${random}`: cada pulsación creaba una
 * fuente distinta y la idempotencia del servidor **nunca se ejercía** desde la
 * interfaz. Con esta clave, el mismo contenido da siempre la misma clave y el
 * servidor devuelve la fuente existente en vez de duplicarla.
 */
export function idempotenciaDe(payload: Record<string, unknown>): string {
  const claves = Object.keys(payload).sort();
  const texto = JSON.stringify(payload, claves);
  // FNV-1a de 32 bits: barato, estable y suficiente para una clave de idempotencia.
  let hash = 2166136261;
  for (let i = 0; i < texto.length; i += 1) {
    hash ^= texto.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return `web-${(hash >>> 0).toString(36)}`;
}
