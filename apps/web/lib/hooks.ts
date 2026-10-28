"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

export function useJobPolling() {
  const [waiting, setWaiting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    setWaiting(null);
  }, []);

  const poll = useCallback(
    async (jobId: number, onDone?: (info: { status: string; error: string | null }) => void) => {
      setWaiting(jobId);
      setError(null);
      const check = async () => {
        try {
          const job = await api.getJob(jobId);
          if (["DONE", "FAILED", "UNKNOWN"].includes(job.status)) {
            setWaiting(null);
            if (job.status === "FAILED") setError(job.error || "El trabajo ha terminado con error");
            onDone?.({ status: job.status, error: job.error ?? null });
            return;
          }
          timer.current = setTimeout(check, 800);
        } catch (e) {
          setWaiting(null);
          setError((e as Error).message);
        }
      };
      timer.current = setTimeout(check, 400);
    },
    [],
  );

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  return { waiting, error, poll, setError, setError_clear: () => setError(null), stop };
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Madrid" }).format(date);
}
