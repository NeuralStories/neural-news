'use client';

/**
 * Guardado por pasos del Studio (NN-113.13).
 *
 * Antes eran **ocho** efectos `useEffect` dentro de `App.tsx`, uno por paso,
 * cada uno con su lista de dependencias. Aquí hay uno solo que recibe los
 * ocho payloads ya calculados y **sólo guarda los que han cambiado** de verdad
 * (`saveIfChanged`), igual que antes: sin esto, la hidratación escribiría en
 * eco y cada recarga generaría revisiones nuevas.
 */
import { useCallback, useEffect } from 'react';
import type { MutableRefObject } from 'react';

export interface OpcionesGuardado {
  /** `true` cuando la hidratación ha terminado: antes no se guarda nada. */
  hydrated: boolean;
  /** Guarda un paso (con control de concurrencia) en el servidor. */
  saveStep: (step: string, payload: Record<string, unknown>) => void;
  /** Instantáneas de lo ya guardado, para no escribir en eco. */
  instantaneas: MutableRefObject<Record<string, string>>;
  /** Payloads de los ocho pasos del Studio. */
  payloads: Record<string, Record<string, unknown>>;
}

export function useGuardadoPasos({
  hydrated,
  saveStep,
  instantaneas,
  payloads,
}: OpcionesGuardado): void {
  const saveIfChanged = useCallback(
    (step: string, payload: Record<string, unknown>) => {
      const json = JSON.stringify(payload);
      if (instantaneas.current[step] === json) return;
      instantaneas.current[step] = json;
      saveStep(step, payload);
    },
    [saveStep, instantaneas],
  );

  useEffect(() => {
    if (!hydrated) return;
    Object.entries(payloads).forEach(([step, payload]) => {
      saveIfChanged(step, payload);
    });
  }, [hydrated, payloads, saveIfChanged]);
}
