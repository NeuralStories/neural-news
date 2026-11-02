"use client";

/**
 * Estudio Flow nativo en neural.news (NN-107 F2) — sin iframe.
 * Una sola navegación, un solo sistema editorial: el Studio carga y guarda su
 * estado en PostgreSQL vía /api/v1/projects. Deep-links compatibles:
 * /estudio?project=<id>[&story=<id>][&revision=<n>]
 */
import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import StudioApp from "@/features/studio/App";
import { ProjectSummary, projectApi } from "@/features/studio/lib/projectApi";

function Launcher() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [stories, setStories] = useState<Array<{ id: number; title: string; status: string }>>([]);
  const [name, setName] = useState("Nuevo proyecto de producción");
  const [ratio, setRatio] = useState<"9:16" | "16:9">("9:16");
  const [storyId, setStoryId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    projectApi
      .list()
      .then((res) => setProjects(res.items))
      .catch((err: Error) => setError(err.message));
    projectApi
      .listStories()
      .then((res) => setStories(res.items))
      .catch(() => setStories([]));
  }, []);

  const create = useCallback(async () => {
    setCreating(true);
    setError(null);
    try {
      const project = await projectApi.create({
        name,
        ratio,
        story_id: storyId ? Number(storyId) : null,
      });
      router.replace(`/estudio?project=${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el proyecto");
    } finally {
      setCreating(false);
    }
  }, [name, ratio, storyId, router]);

  const openDeepLink = useCallback(
    async (project: ProjectSummary) => {
      const storyParam = searchParams.get("story");
      if (storyParam && Number(storyParam) !== project.story_id) {
        try {
          await projectApi.linkStory(project.id, Number(storyParam));
        } catch {
          /* el enlace se reintenta desde el paso Noticias */
        }
      }
      router.replace(`/estudio?project=${project.id}${storyParam ? `&story=${storyParam}` : ""}`);
    },
    [router, searchParams],
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6 py-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-100">Estudio Flow</h1>
        <p className="mt-1 text-sm text-neutral-400">
          Las ocho etapas creativas de Flow, integradas en neural.news con persistencia real en la
          base de datos. Fuera del editor de Flow, la generación queda BLOCKED y se trabaja con el
          paquete manual.
        </p>
      </div>

      <section className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 space-y-3">
        <h2 className="text-sm font-semibold text-neutral-200">Crear proyecto</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-neutral-400 space-y-1 block">
            Nombre
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100"
            />
          </label>
          <label className="text-xs text-neutral-400 space-y-1 block">
            Proporción (se fija en la creación)
            <select aria-label="Proporción (se fija en la creación)"
              value={ratio}
              onChange={(e) => setRatio(e.target.value as "9:16" | "16:9")}
              className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100"
            >
              <option value="9:16">9:16 — Short/Reel</option>
              <option value="16:9">16:9 — Informativo</option>
            </select>
          </label>
          <label className="text-xs text-neutral-400 space-y-1 block sm:col-span-2">
            Noticia del motor editorial (opcional; queda activa desde el inicio)
            <select aria-label="Noticia del motor editorial (opcional; queda activa desde el inicio)"
              value={storyId}
              onChange={(e) => setStoryId(e.target.value)}
              className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm text-neutral-100"
            >
              <option value="">— Sin noticia vinculada —</option>
              {stories.map((s) => (
                <option key={s.id} value={s.id}>
                  #{s.id} · {s.title.slice(0, 80)} ({s.status})
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          onClick={create}
          disabled={creating || !name.trim()}
          className="rounded-md bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
        >
          {creating ? "Creando…" : "Crear y abrir el Studio"}
        </button>
      </section>

      <section className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 space-y-3">
        <h2 className="text-sm font-semibold text-neutral-200">Proyectos existentes</h2>
        {projects === null && <p className="text-xs text-neutral-500">Cargando…</p>}
        {projects?.length === 0 && (
          <p className="text-xs text-neutral-500">Todavía no hay proyectos creados.</p>
        )}
        <ul className="divide-y divide-neutral-800">
          {projects?.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm text-neutral-200">
                  #{p.id} · {p.name}
                </p>
                <p className="text-[11px] text-neutral-500">
                  {p.ratio} · {p.status}
                  {p.story ? ` · noticia #${p.story.id} activa` : " · sin noticia"}
                </p>
              </div>
              <button
                onClick={() => openDeepLink(p)}
                className="shrink-0 rounded-md border border-neutral-700 px-3 py-1.5 text-xs text-neutral-200 hover:bg-neutral-800"
              >
                Abrir
              </button>
            </li>
          ))}
        </ul>
      </section>

      {error && (
        <p className="rounded-md border border-rose-900 bg-rose-950/60 p-3 text-xs text-rose-200">
          {error}
        </p>
      )}
    </div>
  );
}

function EstudioContent() {
  const searchParams = useSearchParams();
  const projectParam = searchParams.get("project");
  const projectId = projectParam ? Number(projectParam) : null;

  if (!projectId || !Number.isFinite(projectId)) {
    return <Launcher />;
  }
  return <StudioApp projectId={projectId} />;
}

export default function EstudioPage() {
  return (
    <div className="studio-root">
      <Suspense fallback={<p className="p-6 text-sm text-neutral-500">Cargando el Studio…</p>}>
        <EstudioContent />
      </Suspense>
    </div>
  );
}
