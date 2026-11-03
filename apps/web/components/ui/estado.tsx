/**
 * Estado semántico: punto + etiqueta. Es la pieza que más se repite en las
 * superficies operativas (salud de dependencias, estado de un trabajo, estado
 * de un proveedor), así que vive en el sistema y no en línea.
 *
 * Los tonos son **funcionales**, no decorativos:
 *   ok    → activo / nominal
 *   warn  → degradado / aviso
 *   crit  → fallo / crítico
 *   info  → en curso / telemetría
 *   idle  → inactivo / sin dato
 */
import { memo } from "react";

export type TonoEstado = "ok" | "warn" | "crit" | "info" | "idle";

/**
 * Dos clases por tono: una para el **texto** del estado y otra para el
 * **punto**. Van separadas porque el punto es un elemento de 8 px dentro de la
 * fila: si el color de fondo se aplicara al contenedor, la fila entera se
 * pintaría del color del estado.
 */
const TEXTO: Record<TonoEstado, string> = {
  ok: "estado-ok",
  warn: "estado-warn",
  crit: "estado-crit",
  info: "estado-info",
  idle: "estado-idle",
};

const PUNTO: Record<TonoEstado, string> = {
  ok: "estado-punto-ok",
  warn: "estado-punto-warn",
  crit: "estado-punto-crit",
  info: "estado-punto-info",
  idle: "estado-punto-idle",
};

export type PropsEstado = {
  tono: TonoEstado;
  etiqueta: string;
  /** Detalle opcional (texto corto, no un párrafo). */
  detalle?: string;
  /** `punto` para una celda-table compacta; `completo` para una fila. */
  variante?: "punto" | "completo";
};

function EstadoImpl({ tono, etiqueta, detalle, variante = "completo" }: PropsEstado) {
  return (
    <span className={`estado ${TEXTO[tono]}`} title={detalle ?? etiqueta} data-tono={tono}>
      <span className={`estado-punto ${PUNTO[tono]}`} aria-hidden="true" />
      <span className="truncate">{etiqueta}</span>
      {variante === "completo" && detalle ? (
        <span className="truncate text-ink-3 normal-case tracking-normal">
          {detalle}
        </span>
      ) : null}
    </span>
  );
}

/**
 * Memoizado: el refresco automático de la consola re-renderiza la página cada
 * 15 s y los estados no deben repintarse si no cambian.
 */
export const Estado = memo(EstadoImpl);
