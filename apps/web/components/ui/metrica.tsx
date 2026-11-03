/**
 * Lectura de telemetría: rótulo, valor y pista. El valor va en monoespaciado
 * con cifras tabulares (columnas de números que no bailan al actualizarse).
 */
import { memo } from "react";

export type TonoMetrica = "neutro" | "ok" | "warn" | "crit";

const TONO_VALOR: Record<TonoMetrica, string> = {
  neutro: "",
  ok: "metrica-valor-ok",
  warn: "metrica-valor-warn",
  crit: "metrica-valor-crit",
};

export type PropsMetrica = {
  etiqueta: string;
  /** Valor ya formateado (la cifra se muestra tal cual, en tabular). */
  valor: string;
  /** Sufijo de la unidad (€, %, s…) o pista corta debajo. */
  sufijo?: string;
  /** Segunda línea: contexto (comparativa, periodo, desglose). */
  pista?: string;
  tono?: TonoMetrica;
};

function MetricaImpl({ etiqueta, valor, sufijo, pista, tono = "neutro" }: PropsMetrica) {
  return (
    <div className="metrica">
      <span className="metrica-label">{etiqueta}</span>
      <span className={`metrica-valor ${TONO_VALOR[tono]}`}>
        {valor}
        {sufijo ? <span className="ml-1 text-sm text-ink-3">{sufijo}</span> : null}
      </span>
      {pista ? <span className="metrica-pista">{pista}</span> : null}
    </div>
  );
}

/**
 * Hoja memoizada: la consola se refresca cada 15 s y las cifras deben repintarse
 * sólo cuando su valor cambia, no cuando cambia cualquier otro bloque.
 */
export const Metrica = memo(MetricaImpl);
