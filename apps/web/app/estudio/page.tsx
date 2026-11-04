"use client";

/**
 * Estudio Flow nativo en neural.news (NN-107 F2) — sin iframe.
 * Una sola navegación, un solo sistema editorial: el Studio carga y guarda su
 * estado en PostgreSQL vía /api/v1/projects. Deep-links compatibles:
 * /estudio?project=<id>[&story=<id>][&revision=<n>]
 *
 * El lanzador (sin proyecto abierto) usa el sistema visual: panel de alta y
 * tabla densa de proyectos con su estado.
 */
import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import StudioApp from "@/features/studio/App";
import { ProjectSummary, projectApi } from "@/features/studio/lib/projectApi";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna } from "@/components/ui/tabla";
import { EsqueletoTabla, Vacio } from "@/components/ui/estados";
import { IconoAlerta, IconoCaja, IconoFlecha, IconoRefrescar } from "@/components/ui/icono";

/** Estado del proyecto → tono del sistema. */
function tonoDeProyecto(status: string): TonoEstado {
  if (status === "DRAFT") return "idle";
  if (status === "IN_PROGRESS" || status === "ACTIVE") return "info";
  if (status === "DONE" || status === "EXPORTED") return "ok";
  if (status === "BLOCKED" || status === "FAILED") return "crit";
  return "idle";
}

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

  const refrescar = useCallback(async () => {
    try {
      const res = await projectApi.list();
      setProjects(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron leer los proyectos");
    }
  }, []);

  useEffect(() => {
    void refrescar();
    projectApi
      .listStories()
      .then((res) => setStories(res.items))
      .catch(() => setStories([]));
  }, [refrescar]);

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

  const columnas: Columna<ProjectSummary>[] = [
    {
      clave: "id",
      cabecera: "#",
      ancho: "4.5rem",
      numerica: true,
      render: (proyecto) => <span className="id">{proyecto.id}</span>,
    },
    {
      clave: "nombre",
      cabecera: "proyecto",
      render: (proyecto) => <span className="text-ink">{proyecto.name}</span>,
    },
    {
      clave: "estado",
      cabecera: "estado",
      ancho: "9rem",
      render: (proyecto) => (
        <Estado
          tono={tonoDeProyecto(proyecto.status)}
          etiqueta={proyecto.status}
          variante="punto"
        />
      ),
    },
    {
      clave: "ratio",
      cabecera: "ratio",
      ancho: "5rem",
      numerica: true,
      render: (proyecto) => <span className="num">{proyecto.ratio}</span>,
    },
    {
      clave: "noticia",
      cabecera: "noticia",
      ancho: "9rem",
      render: (proyecto) =>
        proyecto.story ? (
          <span className="text-ink-2 truncate" title={proyecto.story.title}>
            #{proyecto.story.id} · {proyecto.story.title}
          </span>
        ) : (
          <span className="id">sin noticia</span>
        ),
    },
    {
      clave: "acciones",
      cabecera: "",
      ancho: "6rem",
      numerica: true,
      render: (proyecto) => (
        <button type="button" className="filtro" onClick={() => void openDeepLink(proyecto)}>
          <IconoFlecha /> abrir
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <Panel titulo="Estudio Flow" meta="8 etapas creativas">
        <p className="max-w-3xl text-xs text-ink-2">
          Las ocho etapas creativas de Flow, integradas en neural.news con persistencia real en la
          base de datos. Fuera del editor de Flow, la generación queda BLOCKED y se trabaja con el
          paquete manual.
        </p>
      </Panel>

      {/* items-start: el panel de creación no debe estirarse hasta la altura
          de la tabla de proyectos (quedaba medio panel vacío debajo). */}
      <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <Panel titulo="Crear proyecto" meta="nombre, ratio y noticia">
          <form
            className="space-y-3"
            onSubmit={(evento) => {
              evento.preventDefault();
              void create();
            }}
          >
            <div>
              <label className="ops-panel-title" htmlFor="proyecto-nombre">
                Nombre
              </label>
              <input
                id="proyecto-nombre"
                className="input mt-1"
                value={name}
                onChange={(evento) => setName(evento.target.value)}
              />
            </div>
            <div>
              <label className="ops-panel-title" htmlFor="proyecto-ratio">
                Proporción (se fija en la creación)
              </label>
              <select
                id="proyecto-ratio"
                className="input mt-1"
                value={ratio}
                onChange={(evento) => setRatio(evento.target.value as "9:16" | "16:9")}
              >
                <option value="9:16">9:16 — Short/Reel</option>
                <option value="16:9">16:9 — Informativo</option>
              </select>
            </div>
            <div>
              <label className="ops-panel-title" htmlFor="proyecto-noticia">
                Noticia del motor editorial (opcional)
              </label>
              <select
                id="proyecto-noticia"
                className="input mt-1"
                value={storyId}
                onChange={(evento) => setStoryId(evento.target.value)}
              >
                <option value="">— sin noticia vinculada —</option>
                {stories.map((noticia) => (
                  <option key={noticia.id} value={noticia.id}>
                    #{noticia.id} · {noticia.title.slice(0, 80)} ({noticia.status})
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-sm-primary" disabled={creating || !name.trim()}>
              <IconoCaja /> {creating ? "Creando…" : "Crear y abrir el Studio"}
            </button>
          </form>
        </Panel>

        <Panel
          titulo="Proyectos"
          meta={projects ? `${projects.length}` : "…"}
          relleno="flush"
          acciones={
            <button type="button" className="btn-sm" onClick={() => void refrescar()}>
              <IconoRefrescar /> refrescar
            </button>
          }
        >
          {error ? (
            <div className="alerta-fila alerta-fila-err" role="alert">
              <IconoAlerta className="mt-0.5 shrink-0" />
              <p>{error}</p>
            </div>
          ) : null}
          {projects === null ? (
            <EsqueletoTabla filas={5} />
          ) : (
            <TablaOps
              columnas={columnas}
              filas={projects}
              claveFila={(proyecto) => String(proyecto.id)}
              vacio={
                <Vacio
                  titulo="Todavía no hay proyectos"
                  pista="Crea uno a la izquierda: el Studio guarda el estado de cada etapa en la base de datos."
                  icono={<IconoCaja />}
                />
              }
            />
          )}
          {projects && projects.length > 0 ? (
            <div className="grid grid-cols-3 gap-2 border-t border-line p-3">
              <Metrica etiqueta="proyectos" valor={String(projects.length)} />
              <Metrica
                etiqueta="con noticia"
                valor={String(projects.filter((proyecto) => proyecto.story).length)}
              />
              <Metrica
                etiqueta="9:16"
                valor={String(projects.filter((proyecto) => proyecto.ratio === "9:16").length)}
              />
            </div>
          ) : null}
        </Panel>
      </div>
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
      <Suspense
        fallback={
          <div className="ops-panel-body">
            <span className="esqueleto block h-3 w-48" />
            <span className="sr-only">Cargando el Studio…</span>
          </div>
        }
      >
        <EstudioContent />
      </Suspense>
    </div>
  );
}
