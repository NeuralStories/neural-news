/**
 * Sustituto simulado del módulo virtual `flow-sdk` del entorno de Google Flow.
 *
 * El código recuperado de Studio llama a Flow.media.select, Flow.generate.image,
 * Flow.generate.video y Flow.download. En este entorno local:
 *  - la selección/generación de medios se desactiva con un mensaje claro
 *    (no hay proveedor de pago conectado; ver RIESGOS.md R06);
 *  - Flow.download se implementa con descarga real del navegador, útil para
 *    exportar el paquete de producción sin proveedores.
 */
export interface FlowDownloadRequest {
  base64: string;
  mimeType: string;
  filename: string;
}

export interface FlowMedia {
  mediaId: string;
  base64: string;
  mimeType: string;
  name?: string;
}

export interface FlowImageResult {
  mediaId: string;
  base64: string;
  mimeType: string;
}

export interface FlowVideoResult {
  base64: string;
  mimeType: string;
}

const EXTERNAL_DISABLED =
  'La generación con proveedores externos está desactivada en este entorno local. ' +
  'Conecta un proveedor autorizado (Fase 5) o trabaja con materiales simulados.';

function rejectDisabled(action: string): Promise<never> {
  return Promise.reject(new Error(`${action}: ${EXTERNAL_DISABLED}`));
}

export const Flow = {
  media: {
    select(_options?: { filter?: string }): Promise<FlowMedia> {
      return rejectDisabled('Selección de medios de la galería');
    },
  },
  generate: {
    image(_options: Record<string, unknown>): Promise<FlowImageResult> {
      return rejectDisabled('Generación de imagen');
    },
    video(_options: Record<string, unknown>): Promise<FlowVideoResult> {
      return rejectDisabled('Generación de vídeo');
    },
  },
  async download(request: FlowDownloadRequest): Promise<void> {
    const binary = atob(request.base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: request.mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = request.filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },
};
