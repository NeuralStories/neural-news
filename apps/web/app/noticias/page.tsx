"use client";

/**
 * Noticias: candidatas y aprobadas.
 *
 * Vista migrada al sistema visual (tokens semánticos + componentes propios).
 * Decisiones:
 * - **Tabla densa** (`TablaOps`): cabecera pegajosa, cifras tabulares y
 *   columnas secundarias ocultables por el usuario.
 * - **Filtros en la URL**: estado, orden, texto y página son *search params*,
 *   de modo que la vista es enlazable y el botón «atrás» del navegador
 *   deshace un filtro. Sin dependencias: `useSearchParams` + `router.replace`.
 * - **Carga / vacío / error** con la forma real del contenido: esqueleto
 *   (nunca un spinner), vacío con pista operativa y error con el código
 *   literal y un reintento.
 * - **El dato viejo no se tira**: si un refresco falla, la última lectura
 *   sigue en pantalla marcada como obsoleta.
 * - Cero dependencias nuevas: sólo Tailwind y `components/ui/`.
 */
import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { ESTADOS_NOTICIA, ETIQUETA_NOTICIA } from "@/lib/estados";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { StoryListItem } from "@/lib/types";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna } from "@/components/ui/tabla";
import { EsqueletoMetrica, EsqueletoTabla, Vacio } from "@/components/ui/estados";
import { IconoAlerta, IconoCruce, IconoFlecha, IconoRefrescar } from "@/components/ui/icono";

/** Filas por página (la tabla es densa: 20 caben en dos pantallas). */
const TAMANO_PAGINA = 20;

/**
 * Tono semántico de cada estado de noticia. Los acentos son funcionales:
 * `ok` = aprobado, `info` = en curso, `warn` = requiere revisión,
 * `idle` = sin trabajo en marcha (candidata o descartada).
 */
const TONO_POR_ESTADO: Record<string, TonoEstado> = {
  CANDIDATE: "idle",
  RESEARCHING: "info",
  REVIEW_REQUIRED: "warn",
  SCRIPT_DRAFT: "info",
  APPROVED: "ok",
  REJECTED: "idle",
};

const ORDENES = [
  { clave: "recientes", etiqueta: "recientes" },
  { clave: "antiguos", etiqueta: "antiguos" },
  { clave: "puntuacion", etiqueta: "puntuación" },
  { clave: "titulo", etiqueta: "título" },
] as const;

/** Columnas ocultables (las secundarias: no son el camino principal). */
const COLUMNAS_SECUNDARIAS = [
  { clave: "origen", etiqueta: "origen" },
  { clave: "verificacion", etiqueta: "verif." },
  { clave: "duplicados", etiqueta: "dupl." },
] as const;

/** Error de API con su código literal (HTTP 4xx/5xx) para poder diagnosticarlo. */
function codigoDeError(fallo: unknown): string {
  const error = fallo as Error & { status?: number };
  const codigo = typeof error.status === "number" ? `HTTP ${error.status}` : "sin código";
  return `${codigo} · ${error.message}`;
}

function NoticiasVista() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [datos, setDatos] = useState<StoryListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [ultimaLectura, setUltimaLectura] = useState<string | null>(null);
  const [ocultas, setOcultas] = useState<string[]>([]);
  const { waiting, error: errorTrabajo, poll } = useJobPolling();

  // --- Estado de los filtros: vive en la URL -------------------------------
  const estadoFiltro = searchParams.get("estado") ?? "todos";
  const orden = searchParams.get("orden") ?? "recientes";
  const paginaPedida = Number(searchParams.get("pagina") ?? "1");
  const pagina = Number.isFinite(paginaPedida) && paginaPedida > 0 ? paginaPedida : 1;

  // El texto se refleja en la URL, pero el campo mantiene su propio estado
  // para no pelearse con la escritura (y con el teclado) mientras navega.
  const [texto, setTexto] = useState(() => searchParams.get("q") ?? "");
  useEffect(() => {
    const q = searchParams.get("q") ?? "";
    setTexto((prev) => (prev === q ? prev : q));
  }, [searchParams]);

  /**
   * Escribe un cambio de filtro en la URL. `router.replace` (y no `push`)
   * porque un filtro no es un paso hacia atrás: es el mismo sitio con otra
   * vista.
   */
  const aplicar = useCallback(
    (cambios: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [clave, valor] of Object.entries(cambios)) {
        if (valor === null || valor === "") params.delete(clave);
        else params.set(clave, valor);
      }
      const query = params.toString();
      router.replace(query ? `/noticias?${query}` : "/noticias", { scroll: false });
    },
    [router, searchParams],
  );

  const refresh = useCallback(async () => {
    setCargando(true);
    try {
      const data = await api.listStories();
      setDatos(data.items);
      setUltimaLectura(new Date().toISOString());
      setError(null);
    } catch (fallo) {
      setError(codigoDeError(fallo));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const act = async (story: StoryListItem, kind: "research" | "draft") => {
    try {
      const res = kind === "research" ? await api.research(story.id) : await api.draft(story.id);
      await poll(res.job_id, refresh);
      await refresh();
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  // --- Derivados ------------------------------------------------------------
  const filtradas = useMemo(() => {
    const base = datos ?? [];
    const q = texto.trim().toLowerCase();
    const lista = base.filter((s) => {
      if (estadoFiltro !== "todos" && s.status !== estadoFiltro) return false;
      if (q) {
        const coincide =
          s.title.toLowerCase().includes(q) || s.status_label.toLowerCase().includes(q);
        if (!coincide) return false;
      }
      return true;
    });
    return [...lista].sort((a, b) => {
      if (orden === "antiguos") return a.created_at.localeCompare(b.created_at);
      if (orden === "titulo") return a.title.localeCompare(b.title, "es");
      if (orden === "puntuacion") {
        const sa = a.editorial_score ?? -1;
        const sb = b.editorial_score ?? -1;
        if (sa !== sb) return sb - sa;
      }
      return b.created_at.localeCompare(a.created_at);
    });
  }, [datos, estadoFiltro, orden, texto]);

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / TAMANO_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const visibles = filtradas.slice(
    (paginaActual - 1) * TAMANO_PAGINA,
    paginaActual * TAMANO_PAGINA,
  );

  const situacion = useMemo(() => {
    const base = datos ?? [];
    const cuenta = (estado: string) => base.filter((s) => s.status === estado).length;
    return {
      total: base.length,
      aprobadas: cuenta("APPROVED"),
      enCurso: cuenta("RESEARCHING") + cuenta("SCRIPT_DRAFT"),
      paraRevisar: cuenta("REVIEW_REQUIRED"),
      descartadas: cuenta("REJECTED"),
      sinVerificar: base.reduce((suma, s) => suma + (s.unverified_claims ?? 0), 0),
      sinAfirmaciones: base.filter((s) => !s.claim_count).length,
      conDuplicados: base.filter((s) => (s.possible_duplicates?.length ?? 0) > 0),
    };
  }, [datos]);

  const columnas: Columna<StoryListItem>[] = [
    {
      clave: "id",
      cabecera: "#",
      ancho: "3.75rem",
      numerica: true,
      render: (s) => <span className="id">{s.id}</span>,
    },
    {
      clave: "tema",
      cabecera: "Tema",
      // Ancho mínimo: sin él la columna larga se estrangula y el título se
      // parte en ocho líneas (la tabla se desplaza en horizontal, que es lo
      // propio de una tabla densa).
      ancho: "22rem",
      render: (s) => (
        <div className="min-w-0">
          <Link href={`/noticias/${s.id}`} className="font-medium text-ink hover:text-info">
            {s.title}
          </Link>
          {s.is_opinion ? <span className="badge-warn ml-2">Opinión</span> : null}
          {s.unverified_claims ? (
            <span className="badge-warn ml-2" title="Afirmaciones sin respaldo suficiente">
              {s.unverified_claims} sin verificar
            </span>
          ) : null}
          {s.summary ? (
            <div className="mt-0.5 line-clamp-2 text-xs text-ink-3">{s.summary}</div>
          ) : null}
        </div>
      ),
    },
    {
      clave: "estado",
      cabecera: "Estado",
      ancho: "10rem",
      render: (s) => (
        <Estado
          tono={TONO_POR_ESTADO[s.status] ?? "idle"}
          etiqueta={s.status_label}
          variante="punto"
        />
      ),
    },
    {
      clave: "fecha",
      cabecera: "Fecha real",
      ancho: "10rem",
      render: (s) =>
        s.original_event_date ? (
          <span className="num" title="Fecha del acontecimiento">
            {fmtDate(s.original_event_date)}
          </span>
        ) : (
          <span className="id" title="No consta la fecha del acontecimiento">
            sin fecha
          </span>
        ),
    },
    {
      clave: "puntuacion",
      cabecera: "Puntuación",
      ancho: "4.5rem",
      numerica: true,
      render: (s) => <span className="num">{s.editorial_score ?? "—"}</span>,
    },
    {
      clave: "origen",
      cabecera: "Origen",
      ancho: "4.5rem",
      numerica: true,
      secundaria: true,
      render: (s) => <span className="num">{s.source_count ?? "—"}</span>,
    },
    {
      clave: "verificacion",
      cabecera: "Verificación",
      ancho: "9rem",
      secundaria: true,
      render: (s) => {
        if (!s.claim_count) {
          return (
            <span className="badge-neutral" title="No hay afirmaciones que comprobar">
              Sin afirmaciones
            </span>
          );
        }
        if (s.unverified_claims) {
          return <span className="badge-warn">Parcial</span>;
        }
        return <span className="badge-ok">Sin huecos</span>;
      },
    },
    {
      clave: "duplicados",
      cabecera: "Duplicados",
      ancho: "13rem",
      secundaria: true,
      render: (s) => {
        const duplicados = s.possible_duplicates ?? [];
        if (duplicados.length === 0) return <span className="id">—</span>;
        return (
          <details>
            <summary className="filtro cursor-pointer">
              {duplicados.length} posible{duplicados.length === 1 ? "" : "s"}
            </summary>
            <ul className="mt-1 flex flex-col gap-1">
              {duplicados.map((d) => (
                <li key={d.story_id} className="text-xs">
                  <Link href={`/noticias/${d.story_id}`} className="text-info hover:underline">
                    {d.title}
                  </Link>
                  <span className="block text-ink-3">{d.reason}</span>
                </li>
              ))}
            </ul>
          </details>
        );
      },
    },
    {
      clave: "acciones",
      cabecera: "Acciones",
      ancho: "10rem",
      render: (s) => (
        <div className="flex gap-1">
          <button
            type="button"
            className="btn-sm"
            onClick={() => void act(s, "research")}
            title={`Investigar «${s.title}»`}
          >
            Investigar
          </button>
          <Link href={`/noticias/${s.id}`} className="btn-sm">
            Abrir
          </Link>
        </div>
      ),
    },
  ];

  // --- Estados de página ----------------------------------------------------
  if (datos === null && error) {
    return (
      <Panel titulo="Noticias · sin datos" meta="error de lectura">
        <div className="alerta-fila alerta-fila-err" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p>No se ha podido leer el listado de noticias.</p>
            <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{error}</p>
          </div>
        </div>
        <div className="mt-3">
          <button type="button" className="btn-sm" onClick={() => void refresh()}>
            <IconoRefrescar /> Reintentar
          </button>
        </div>
      </Panel>
    );
  }

  if (datos === null) {
    return (
      <div className="space-y-3">
        <section className="ops-panel">
          <div className="ops-panel-head">
            <span className="esqueleto h-2 w-40" />
          </div>
          <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, indice) => (
              <EsqueletoMetrica key={indice} />
            ))}
          </div>
        </section>
        <Panel titulo="Noticias" meta="cargando">
          <EsqueletoTabla filas={10} />
        </Panel>
        <span className="sr-only">Cargando las noticias…</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* --- Banda de cabecera ---------------------------------------------- */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1">
            <h1 className="text-sm font-semibold tracking-tight text-ink">Noticias</h1>
            <Estado
              tono={situacion.aprobadas > 0 ? "ok" : "idle"}
              etiqueta={`${situacion.aprobadas} aprobadas`}
              variante="punto"
            />
            <span className="ops-panel-meta">
              {situacion.total} en total · {filtradas.length} con los filtros actuales
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              className="btn-sm"
              onClick={() => void refresh()}
              disabled={cargando}
            >
              <IconoRefrescar />
              {cargando ? "leyendo…" : "actualizar"}
            </button>
          </div>
        </div>

        {error ? (
          <div className="alerta-fila alerta-fila-warn border-l-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>Última lectura fallida; se conserva la anterior.</p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{error}</p>
            </div>
          </div>
        ) : null}

        {errorTrabajo ? (
          <div className="alerta-fila alerta-fila-warn border-l-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>El trabajo en marcha ha terminado con error.</p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{errorTrabajo}</p>
            </div>
          </div>
        ) : null}

        {waiting !== null ? (
          <div className="alerta-fila" role="status">
            <IconoFlecha className="mt-0.5 shrink-0 text-info" />
            <p className="text-ink-2">
              Trabajo <span className="font-mono tabular-nums text-ink">#{waiting}</span> en marcha…
            </p>
          </div>
        ) : null}
      </section>

      {/* --- Situación (bento de telemetría) -------------------------------- */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="ops-panel-title">Situación</h2>
            <span className="ops-panel-meta">{datos.length} noticias</span>
          </div>
        </div>
        <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          <Metrica etiqueta="noticias" valor={String(situacion.total)} />
          <Metrica
            etiqueta="aprobadas"
            valor={String(situacion.aprobadas)}
            tono={situacion.aprobadas > 0 ? "ok" : "neutro"}
          />
          <Metrica
            etiqueta="en curso"
            valor={String(situacion.enCurso)}
            tono={situacion.enCurso > 0 ? "warn" : "neutro"}
          />
          <Metrica
            etiqueta="para revisar"
            valor={String(situacion.paraRevisar)}
            tono={situacion.paraRevisar > 0 ? "warn" : "neutro"}
          />
          <Metrica
            etiqueta="descartadas"
            valor={String(situacion.descartadas)}
            tono={situacion.descartadas > 0 ? "crit" : "neutro"}
          />
          <Metrica
            etiqueta="sin verificar"
            valor={String(situacion.sinVerificar)}
            tono={situacion.sinVerificar > 0 ? "warn" : "neutro"}
            pista="afirmaciones sin respaldo"
          />
        </div>
      </section>

      {/* --- Rejilla principal: lista | contexto ---------------------------- */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-3">
          {/* Filtros: estado, orden, texto y página viven en la URL. */}
          <Panel titulo="Filtros" meta={`${filtradas.length} de ${datos.length}`}>
            <div className="flex flex-wrap items-center gap-2">
              <input
                className="input max-w-64"
                placeholder="Filtrar por tema o estado…"
                aria-label="Filtrar noticias por tema o estado"
                value={texto}
                onChange={(e) => {
                  setTexto(e.target.value);
                  aplicar({ q: e.target.value || null, pagina: "1" });
                }}
              />
              <label className="sr-only" htmlFor="orden-noticias">
                Ordenar noticias
              </label>
              <select
                id="orden-noticias"
                className="input max-w-40"
                value={orden}
                onChange={(e) => aplicar({ orden: e.target.value, pagina: "1" })}
              >
                {ORDENES.map((opcion) => (
                  <option key={opcion.clave} value={opcion.clave}>
                    Orden: {opcion.etiqueta}
                  </option>
                ))}
              </select>
              {estadoFiltro !== "todos" || texto.trim() !== "" || pagina !== 1 ? (
                <button
                  type="button"
                  className="filtro"
                  onClick={() => {
                    setTexto("");
                    aplicar({ estado: null, orden: null, q: null, pagina: null });
                  }}
                >
                  <IconoCruce /> restablecer
                </button>
              ) : null}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1">
              <button
                type="button"
                className={`filtro ${estadoFiltro === "todos" ? "filtro-on" : ""}`}
                onClick={() => aplicar({ estado: null, pagina: "1", q: texto || null })}
              >
                todas
              </button>
              {ESTADOS_NOTICIA.map((estado) => (
                <button
                  key={estado}
                  type="button"
                  className={`filtro ${estadoFiltro === estado ? "filtro-on" : ""}`}
                  onClick={() => aplicar({ estado, pagina: "1", q: texto || null })}
                >
                  {ETIQUETA_NOTICIA[estado] ?? estado}
                </button>
              ))}
            </div>
          </Panel>

          <Panel
            titulo="Noticias"
            meta={`${visibles.length} de ${filtradas.length}`}
            relleno="flush"
            acciones={
              <>
                {COLUMNAS_SECUNDARIAS.map((columna) => (
                  <button
                    key={columna.clave}
                    type="button"
                    className={`filtro ${!ocultas.includes(columna.clave) ? "filtro-on" : ""}`}
                    onClick={() =>
                      setOcultas((actual) =>
                        actual.includes(columna.clave)
                          ? actual.filter((item) => item !== columna.clave)
                          : [...actual, columna.clave],
                      )
                    }
                    title="Mostrar u ocultar columna"
                  >
                    {columna.etiqueta}
                  </button>
                ))}
              </>
            }
          >
            <TablaOps
              columnas={columnas}
              filas={visibles}
              claveFila={(s) => String(s.id)}
              ocultas={ocultas}
              vacio={
                <Vacio
                  titulo="No hay noticias con estos filtros"
                  pista="Quita los filtros o registra más fuentes en «Fuentes» para que el sistema proponga candidatas."
                  icono={<IconoFlecha />}
                />
              }
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-3 py-2">
              <span className="ops-panel-meta">
                página {paginaActual} de {totalPaginas} · {filtradas.length} resultados
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  className="btn-sm"
                  disabled={paginaActual <= 1}
                  onClick={() => aplicar({ pagina: String(paginaActual - 1) })}
                >
                  anterior
                </button>
                <button
                  type="button"
                  className="btn-sm"
                  disabled={paginaActual >= totalPaginas}
                  onClick={() => aplicar({ pagina: String(paginaActual + 1) })}
                >
                  siguiente
                </button>
              </div>
            </div>
          </Panel>
        </div>

        {/* --- Columna de contexto ------------------------------------------ */}
        <div className="min-w-0 space-y-3">
          <Panel titulo="Verificación" meta={`${situacion.sinVerificar} afirmaciones`}>
            <div className="flex flex-col gap-px bg-line">
              <div className="kv bg-surface">
                <span className="kv-clave">noticias sin afirmaciones</span>
                <span className="kv-valor">{situacion.sinAfirmaciones}</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">afirmaciones sin respaldo</span>
                <span className="kv-valor">{situacion.sinVerificar}</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">noticias para revisar</span>
                <span className="kv-valor">{situacion.paraRevisar}</span>
              </div>
            </div>
            <p className="mt-2 text-xs text-ink-3">
              Sin evidencia no se marca nada como confirmado: lanza «Investigar» sobre la noticia.
            </p>
          </Panel>

          <Panel titulo="Posibles duplicados" meta={String(situacion.conDuplicados.length)}>
            {situacion.conDuplicados.length === 0 ? (
              <Vacio
                titulo="Sin duplicados señalados"
                pista="El sistema sólo los propone cuando el parecido es alto: no hay ninguna noticia marcada ahora."
              />
            ) : (
              <ul className="flex flex-col gap-1.5">
                {situacion.conDuplicados.slice(0, 8).map((s) => (
                  <li key={s.id} className="text-xs">
                    <Link href={`/noticias/${s.id}`} className="text-ink hover:text-info">
                      {s.title}
                    </Link>
                    <span className="block font-mono text-[11px] tabular-nums text-ink-3">
                      {(s.possible_duplicates?.length ?? 0) === 1
                        ? "1 posible"
                        : `${s.possible_duplicates?.length ?? 0} posibles`}{" "}
                      · #{s.id}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel titulo="Cómo se lee esta vista">
            <p className="text-xs text-ink-2">
              La puntuación editorial es orientativa; la aprobación de un guion siempre es humana.
            </p>
            <p className="mt-2 font-mono text-[11px] tabular-nums text-ink-3">
              última lectura {ultimaLectura ? fmtDate(ultimaLectura) : "—"}
            </p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

export default function NoticiasPage() {
  return (
    <Suspense fallback={<EsqueletoNoticias />}>
      <NoticiasVista />
    </Suspense>
  );
}

/** Esqueleto con la forma real de la vista (nada de spinners). */
function EsqueletoNoticias() {
  return (
    <div className="space-y-3">
      <section className="ops-panel">
        <div className="ops-panel-head">
          <span className="esqueleto h-2 w-40" />
        </div>
        <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, indice) => (
            <EsqueletoMetrica key={indice} />
          ))}
        </div>
      </section>
      <Panel titulo="Noticias" meta="cargando">
        <EsqueletoTabla filas={10} />
      </Panel>
      <span className="sr-only">Cargando las noticias…</span>
    </div>
  );
}
