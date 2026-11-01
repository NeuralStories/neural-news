"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

export type JobPollInfo = { status: string; error: string | null };

const TERMINALES = ["DONE", "FAILED", "UNKNOWN", "RETRYABLE_FAILED"];

/**
 * Seguimiento de trabajos en curso.
 *
 * Dos correcciones sobre el comportamiento anterior (hallazgo B21):
 *  1. `poll` **espera** a que el trabajo termina. Antes devolvía la promesa
 *     enseguida (solo programaba la primera comprobación), así que
 *     `await poll(...)` no esperaba nada y la página refrescaba con el trabajo
 *     todavía en curso.
 *  2. Cada trabajo lleva su propio temporizador. Antes había UN solo `timer`
 *     compartido: dos sondeos simultáneos se pisaban y el sondeo viejo
 *     terminaba **`onDone()` tarde**, machacando el texto que el editor
 *     acababa de escribir (el botón «Guardar borrador» se volvía a deshabilitar
 *     y la edición se perdía en silencio).
 */
export function useJobPolling() {
  const [waiting, setWaiting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<Record<number, ReturnType<typeof setTimeout>>>({});

  const stop = useCallback(() => {
    Object.values(timers.current).forEach((t) => clearTimeout(t));
    timers.current = {};
    setWaiting(null);
  }, []);

  const poll = useCallback(
    (jobId: number, onDone?: (info: JobPollInfo) => void): Promise<JobPollInfo> =>
      new Promise<JobPollInfo>((resolve) => {
        setWaiting(jobId);
        setError(null);
        const finish = (info: JobPollInfo) => {
          delete timers.current[jobId];
          setWaiting((w) => (w === jobId ? null : w));
          resolve(info);
        };
        const check = async () => {
          try {
            const job = await api.getJob(jobId);
            if (TERMINALES.includes(job.status)) {
              if (job.status === "FAILED") {
                setError(job.error || "El trabajo ha terminado con error");
              }
              if (job.status === "RETRYABLE_FAILED") {
                setError(
                  job.error || "El trabajo se ha quedado a medias; se reintentará automáticamente",
                );
              }
              const info: JobPollInfo = { status: job.status, error: job.error ?? null };
              onDone?.(info);
              finish(info);
              return;
            }
            timers.current[jobId] = setTimeout(check, 800);
          } catch (e) {
            setError((e as Error).message);
            finish({ status: "ERROR", error: (e as Error).message });
          }
        };
        timers.current[jobId] = setTimeout(check, 400);
      }),
    [],
  );

  useEffect(
    () => () => {
      Object.values(timers.current).forEach((t) => clearTimeout(t));
    },
    [],
  );

  return { waiting, error, poll, setError, stop };
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Madrid" }).format(date);
}
