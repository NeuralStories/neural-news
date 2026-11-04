/**
 * Panel de la rejilla operativa: borde de 1px, cabecera con micro-rótulo
 * monoespaciado y cuerpo. El contenido puede ir con o sin relleno (flush), que
 * es lo que necesitan las tablas densas.
 */
import type { ReactNode } from "react";

export type PropsPanel = {
  titulo: string;
  /** Contexto de la cabecera (conteos, ventana temporal, estado). */
  meta?: ReactNode;
  /** Acciones a la derecha (filtros, botones). */
  acciones?: ReactNode;
  /** `flush` = sin relleno (tabla), `pad` = con relleno (listas). */
  relleno?: "flush" | "pad";
  children: ReactNode;
};

export function Panel({ titulo, meta, acciones, relleno = "pad", children }: PropsPanel) {
  return (
    <section className="ops-panel min-w-0">
      <header className="ops-panel-head">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <h2 className="ops-panel-title">{titulo}</h2>
          {meta ? <span className="ops-panel-meta truncate">{meta}</span> : null}
        </div>
        {/*
          Las acciones **envuelven**: en pantallas estrechas una fila de filtros
          que no envuelve desborda el documento entero (412 px de desborde en
          el viewport de 390 px que comprueba el E2E de móvil).
        */}
        {acciones ? (
          <div className="flex flex-wrap items-center justify-end gap-1.5">{acciones}</div>
        ) : null}
      </header>
      <div className={relleno === "flush" ? "ops-panel-body-flush" : "ops-panel-body"}>{children}</div>
    </section>
  );
}
