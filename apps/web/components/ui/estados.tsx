/**
 * Estados de carga y vacío de la superficies operativa.
 *
 * El esqueleto tiene **la forma del contenido final**: la consola no salta al
 * montar (sin *layout shift*) y el operador ve desde el primer segundo qué
 * bloques van a aparecer.
 */
import type { ReactNode } from "react";

/** Bloque de carga con la forma de una métrica. */
export function EsqueletoMetrica() {
  return (
    <div className="metrica">
      <span className="esqueleto block h-2 w-16" />
      <span className="esqueleto mt-2 block h-5 w-12" />
      <span className="esqueleto mt-2 block h-2 w-20" />
    </div>
  );
}

/** Filas de carga con la forma de la tabla densa. */
export function EsqueletoTabla({ filas = 6 }: { filas?: number }) {
  return (
    <div className="ops-panel-body">
      <div className="flex flex-col gap-1.5" aria-hidden="true">
        {Array.from({ length: filas }).map((_, indice) => (
          <span key={indice} className="esqueleto block h-3 w-full" />
        ))}
      </div>
      <span className="sr-only">Cargando…</span>
    </div>
  );
}

/** Bloques de carga con la forma de un panel de la rejilla. */
export function EsqueletoPanel({ lineas = 3 }: { lineas?: number }) {
  return (
    <div className="ops-panel">
      <div className="ops-panel-head">
        <span className="esqueleto h-2 w-24" />
      </div>
      <div className="ops-panel-body">
        <div className="flex flex-col gap-1.5" aria-hidden="true">
          {Array.from({ length: lineas }).map((_, indice) => (
            <span key={indice} className="esqueleto block h-3 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

/** Estado vacío con pista operativa (qué hacer, no sólo «no hay datos»). */
export function Vacio({ titulo, pista, icono }: { titulo: string; pista?: string; icono?: ReactNode }) {
  return (
    <div className="vacio">
      {icono ? <span className="text-ink-3">{icono}</span> : null}
      <span className="text-ink-2">{titulo}</span>
      {pista ? <span className="max-w-sm text-ink-3">{pista}</span> : null}
    </div>
  );
}
