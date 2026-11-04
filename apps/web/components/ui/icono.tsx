/**
 * Iconos del sistema: SVG en línea, 16 px por defecto, trazo de 1,75 y
 * `currentColor`. Sin dependencias (no hay `lucide-react` en el proyecto) y
 * sin peticiones a terceros: son geometría, no fuentes.
 *
 * Todos comparten el mismo `viewBox` de 24×24 y el mismo grosor de trazo, para
 * que convivan en una misma línea sin desajustes.
 */
import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement> & { tamano?: number };

function Base({ tamano = 16, children, ...resto }: Props) {
  return (
    <svg
      width={tamano}
      height={tamano}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...resto}
    >
      {children}
    </svg>
  );
}

export function IconoRefrescar(props: Props) {
  return (
    <Base {...props}>
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </Base>
  );
}

export function IconoAlerta(props: Props) {
  return (
    <Base {...props}>
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </Base>
  );
}

export function IconoCheck(props: Props) {
  return (
    <Base {...props}>
      <path d="M20 6 9 17l-5-5" />
    </Base>
  );
}

export function IconoCruce(props: Props) {
  return (
    <Base {...props}>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </Base>
  );
}

export function IconoSol(props: Props) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </Base>
  );
}

export function IconoLuna(props: Props) {
  return (
    <Base {...props}>
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </Base>
  );
}

export function IconoPulso(props: Props) {
  return (
    <Base {...props}>
      <path d="M3 12h4l3 8 4-16 3 8h4" />
    </Base>
  );
}

export function IconoReloj(props: Props) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </Base>
  );
}

export function IconoCaja(props: Props) {
  return (
    <Base {...props}>
      <path d="M21 8v8a2 2 0 0 1-1 1.73l-7 4a2 2 0 0 1-2 0l-7-4A2 2 0 0 1 3 16V8a2 2 0 0 1 1-1.73l7-4a2 2 0 0 1 2 0l7 4A2 2 0 0 1 21 8Z" />
      <path d="m3.3 7 8.7 5 8.7-5" />
      <path d="M12 22V12" />
    </Base>
  );
}

export function IconoFiltro(props: Props) {
  return (
    <Base {...props}>
      <path d="M3 4h18l-7 8v6l-4 2v-8Z" />
    </Base>
  );
}

export function IconoFlecha(props: Props) {
  return (
    <Base {...props}>
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </Base>
  );
}

export function IconoBuscar(props: Props) {
  return (
    <Base {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </Base>
  );
}

export function IconoCruz(props: Props) {
  return (
    <Base {...props}>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </Base>
  );
}

/**
 * Indicador de orden de columna: chevron de 10 px alineado con la cabecera.
 * Apagado (35 % de tinta) cuando esa columna no manda el orden; girado 180°
 * en descendente. Es un marcador, no un icono de acción: no lleva trazo 1,75.
 */
export function IconoOrden({
  dir,
  activo = false,
}: {
  dir: "asc" | "desc";
  activo?: boolean;
}) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={dir === "desc" ? "rotate-180" : undefined}
      style={{ opacity: activo ? 1 : 0.35 }}
    >
      <path d="m6 15 6-6 6 6" />
    </svg>
  );
}
