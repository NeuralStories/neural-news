'use client';

/**
 * Persistencia del Studio contra la API (NN-107 F2): el estado del proyecto
 * vive en PostgreSQL vía /api/v1/projects; `localStorage` queda prohibido como
 * fuente de verdad. Cada paso se guarda con control de concurrencia (CAS): si
 * el servidor devuelve 409, se recarga el estado del servidor y se avisa.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { ProjectConflict, ProjectFull, projectApi } from './projectApi';

export type StepSaveState = 'idle' | 'saving' | 'saved' | 'conflict' | 'error';

const SAVE_DEBOUNCE_MS = 700;

export function useStudioProject(projectId: number | null) {
  const [project, setProject] = useState<ProjectFull | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(projectId));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveStates, setSaveStates] = useState<Record<string, StepSaveState>>({});
  const revisionsRef = useRef<Record<string, number>>({});
  const timersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const inflightRef = useRef<Record<string, Promise<unknown>>>({});

  const applyProject = useCallback((full: ProjectFull) => {
    setProject(full);
    revisionsRef.current = { ...full.step_revisions };
  }, []);

  const reload = useCallback(async () => {
    if (!projectId) return;
    try {
      const full = await projectApi.get(projectId);
      applyProject(full);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'No se pudo cargar el proyecto');
    } finally {
      setLoading(false);
    }
  }, [projectId, applyProject]);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    void reload();
  }, [projectId, reload]);

  const flushStep = useCallback(
    async (step: string, payload: Record<string, unknown>) => {
      if (!projectId) return;
      const expected = revisionsRef.current[step] ?? 0;
      const job = (async () => {
        try {
          const result = await projectApi.saveStep(projectId, step, payload, expected);
          revisionsRef.current = { ...revisionsRef.current, [step]: result.revision };
          setSaveStates((prev) => ({ ...prev, [step]: 'saved' }));
        } catch (err) {
          if (err instanceof ProjectConflict) {
            revisionsRef.current = { ...revisionsRef.current, [step]: err.currentRevision };
            setSaveStates((prev) => ({ ...prev, [step]: 'conflict' }));
            await reload();
          } else {
            setSaveStates((prev) => ({ ...prev, [step]: 'error' }));
          }
        }
      })();
      inflightRef.current[step] = job;
      await job;
      delete inflightRef.current[step];
    },
    [projectId, reload],
  );

  /** Guardado diferido por paso: los cambios encolan y el último gana. */
  const saveStep = useCallback(
    (step: string, payload: Record<string, unknown>) => {
      if (!projectId) return;
      setSaveStates((prev) => (prev[step] === 'saving' ? prev : { ...prev, [step]: 'saving' }));
      const timers = timersRef.current;
      if (timers[step]) clearTimeout(timers[step]);
      timers[step] = setTimeout(() => {
        void flushStep(step, payload);
      }, SAVE_DEBOUNCE_MS);
    },
    [projectId, flushStep],
  );

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      Object.values(timers).forEach((t) => clearTimeout(t));
    };
  }, []);

  return { project, loading, loadError, saveStates, saveStep, reload };
}
