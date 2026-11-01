'use client';

/**
 * Adaptador de runtime de Flow (NN-107, decisión D3): único punto de contacto
 * con el runtime propietario. Ningún componente importa `flow-sdk`.
 *
 * - `FlowHostedAdapter`: delega en `window.Flow` cuando la app corre dentro del
 *   editor de Google Flow (sonda de capacidad).
 * - `FlowManualAdapter` (por defecto fuera del editor): la descarga de archivos
 *   se resuelve de forma nativa en el navegador; la selección de galería y la
 *   generación devuelven `FlowUnavailableError` (estado BLOCKED con paquete
 *   manual). Nunca simula generación ni conexión con Flow.
 */

export interface FlowMedia {
  mediaId: string;
  base64: string;
  mimeType: string;
  name?: string;
}

export interface FlowImageResult extends FlowMedia {}

export interface FlowVideoResult {
  base64: string;
  mimeType: string;
}

export interface FlowDownloadRequest {
  base64: string;
  mimeType: string;
  filename: string;
}

export class FlowUnavailableError extends Error {
  readonly blocked = true;
  constructor(action: string) {
    super(
      `BLOCKED — ${action}: esta operación requiere el runtime de Google Flow, ` +
        'que no está disponible fuera de su editor. Prepara el paquete manual ' +
        '(FlowManualPackage), genera la toma en Flow e impórtala en Resultado.',
    );
    this.name = 'FlowUnavailableError';
  }
}

interface FlowHost {
  media: { select(options?: { filter?: string }): Promise<FlowMedia> };
  generate: {
    image(options: Record<string, unknown>): Promise<FlowImageResult>;
    video(options: Record<string, unknown>): Promise<FlowVideoResult>;
  };
  download(request: FlowDownloadRequest): Promise<void>;
}

function detectHostedFlow(): FlowHost | null {
  if (typeof window === 'undefined') return null;
  const candidate = (window as unknown as { Flow?: FlowHost }).Flow;
  if (
    candidate &&
    candidate.media &&
    typeof candidate.media.select === 'function' &&
    candidate.generate &&
    typeof candidate.generate.video === 'function'
  ) {
    return candidate;
  }
  return null;
}

/** Descarga nativa de navegador: misma operación que Flow.download, sin runtime. */
async function nativeDownload(request: FlowDownloadRequest): Promise<void> {
  const binary = atob(request.base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: request.mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = request.filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

const manual: FlowHost = {
  media: {
    async select(options?: { filter?: string }): Promise<FlowMedia> {
      throw new FlowUnavailableError(`Selección de medios de la galería (${options?.filter ?? '*'})`);
    },
  },
  generate: {
    async image(): Promise<FlowImageResult> {
      throw new FlowUnavailableError('Generación de imágenes');
    },
    async video(): Promise<FlowVideoResult> {
      throw new FlowUnavailableError('Generación de vídeo');
    },
  },
  download: nativeDownload,
};

const runtime: FlowHost = detectHostedFlow() ?? manual;

export const flowRuntime = {
  /** `true` solo dentro del editor de Flow; fuera, toda generación queda BLOCKED. */
  hosted: runtime !== manual,
  media: runtime.media,
  generate: runtime.generate,
  download: runtime.download,
};

/** Superficie compatible con el `Flow` del código original recuperado: los
 * componentes cambian solo la línea de import. */
export const Flow = flowRuntime;
