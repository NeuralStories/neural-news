"use client";

/**
 * Lotes editoriales: grupos de 5 o 10 noticias para grabar.
 *
 * Vista migrada al sistema visual (tokens semánticos + componentes propios).
 * Decisiones:
 * - **Rejilla asimétrica**: a la izquierda lo que se compone (selección y
 *   catálogo de noticias); a la derecha lo que se consulta (lotes existentes y
 *   el lote abierto, con su orden).
 * - **Tablas densas** (`TablaOps`): cabecera pegajosa, cifras tabulares y
 *   columnas secundarias ocultables por el usuario.
 * - **Filtros en la URL**: estado, orden, texto y página son *search params*
 *   (`useSearchParams` + `router.replace`), de modo que la vista es
 *   enlazable y el botón «atrás» deshace un filtro. Sin dependencias.
 * - **Carga / vacío / error** con la forma real del contenido: esqueleto
 *   (nunca un spinner), vacío con pista operativa y error con el código
 *   literal y un reintento.
 * - Cero dependencias nuevas: sólo Tailwind y `components/ui/`.
 */
import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { ESTADOS_NOTICIA, ETIQUETA_NOTICIA, ETIQUETA_PAQUETE } from "@/lib/estados";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { BatchDetail, StoryListItem } from "@/lib/types";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna } from "@/components/ui/tabla";
import { EsqueletoMetrica, EsqueletoTabla, Vacio } from "@/components/ui/estados";
import { IconoAlerta, IconoCaja, IconoCruce, IconoFlecha, IconoRefrescar } from "@/components/ui/icono";

/** Filas por página del catálogo de noticias. */
const TAMANO_PAGINA = 15;

/** Tamaños de lote admitidos por la API. */
const TAMANOS = [5, 10] as const;
type Tamano = (typeof TAMANOS)[number];

/** Tono semántico del estado de una noticia. */
const TONO_POR_ESTADO: Record<string, TonoEstado> = {
  CANDIDATE: "idle",
  RESEARCHING: "info",
  REVIEW_REQUIRED: "warn",
  SCRIPT_DRAFT: "info",
  APPROVED: "ok",
  REJECTED: "idle",
};

/** Tono semántico del estado de un lote (paquete). */
const TONO_POR_LOTE: Record<string, TonoEstado> = {
  NOT_STARTED: "idle",
  DRAFT: "info",
  READY_FOR_REVIEW: "warn",
  EXPORTED: "ok",
};

const ORDENES = [
  { clave: "recientes", etiqueta: "recientes" },
  { clave: "antiguos", etiqueta: "antiguos" },
  { clave: "puntuacion", etiqueta: "puntuación" },
  { clave: "titulo", etiqueta: "título" },
] as const;

/** Columnas ocultables del catálogo de noticias. */
const COLUMNAS_NOTICIA = [
  { clave: "puntuacion", etiqueta: "punt." },
  { clave: "fecha", etiqueta: "fecha" },
] as const;

/** Columnas ocultables del listado de lotes. */
const COLUMNAS_LOTE = [
  { clave: "tamano", etiqueta: "tamaño" },
  { clave: "fecha", etiqueta: "fecha" },
] as const;

/** Error de API con su código literal (HTTP 4xx/5xx) para poder diagnosticarlo. */
function codigoDeError(fallo: unknown): string {
  const error = fallo as Error & { status?: number };
  const codigo = typeof error.status === "number" ? `HTTP ${error.status}` : "sin código";
  return `${codigo} · ${error.message}`;
}

type LoteResumen = {
  id: number;
  name: string;
  target_size: number;
  status: string;
  created_at: string;
};

function LotesVista() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [batches, setBatches] = useState<LoteResumen[] | null>(null);
  const [stories, setStories] = useState<StoryListItem[] | null>(null);
  const [selected, setSelected] = useState<BatchDetail | null>(null);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [targetSize, setTargetSize] = useState<Tamano>(5);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [ocultasNoticia, setOcultasNoticia] = useState<string[]>([]);
  const [ocultasLote, setOcultasLote] = useState<string[]>([]);
  const { waiting, error: errorTrabajo, poll } = useJobPolling();

  // --- Estado de los filtros: vive en la URL -------------------------------
  const estadoFiltro = searchParams.get("estado") ?? "todos";
  const orden = searchParams.get("orden") ?? "recientes";
  const paginaPedida = Number(searchParams.get("pagina") ?? "1");
  const pagina = Number.isFinite(paginaPedida) && paginaPedida > 0 ? paginaPedida : 1;

  const [texto, setTexto] = useState(() => searchParams.get("q") ?? "");
  useEffect(() => {
    const q = searchParams.get("q") ?? "";
    setTexto((prev) => (prev === q ? prev : q));
  }, [searchParams]);

  const aplicar = useCallback(
    (cambios: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [clave, valor] of Object.entries(cambios)) {
        if (valor === null || valor === "") params.delete(clave);
        else params.set(clave, valor);
      }
      const query = params.toString();
      router.replace(query ? `/lotes?${query}` : "/lotes", { scroll: false });
    },
    [router, searchParams],
  );

  const refresh = useCallback(async () => {
    setCargando(true);
    try {
      const [batchList, storyList] = await Promise.all([api.listBatches(), api.listStories()]);
      setBatches(batchList.items);
      setStories(storyList.items);
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

  const toggle = (id: number) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < targetSize) next.add(id);
      return next;
    });
  };

  const changeSize = (size: Tamano) => {
    setTargetSize(size);
    setChecked(new Set());
  };

  const open = async (id: number) => {
    setError(null);
    try {
      setSelected(await api.getBatch(id));
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const create = async () => {
    setError(null);
    setNotice(null);
    try {
      const res = await api.createBatch({ name, target_size: targetSize, story_ids: [...checked] });
      setNotice(`Lote creado (#${res.id}).`);
      setChecked(new Set());
      setName("");
      await refresh();
      await open(res.id);
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const move = async (storyId: number, delta: number) => {
    if (!selected) return;
    const ids = selected.stories.map((s) => s.story_id);
    const from = ids.indexOf(storyId);
    const to = from + delta;
    if (to < 0 || to >= ids.length) return;
    [ids[from], ids[to]] = [ids[to], ids[from]];
    await api.reorderBatch(selected.id, ids);
    await open(selected.id);
  };

  const exportPackage = async () => {
    if (!selected) return;
    setError(null);
    setNotice(null);
    try {
      const res = await api.exportBatch(selected.id);
      await poll(res.job_id, refresh);
      await open(selected.id);
      setNotice("Paquete exportado. Usa «Descargar paquete» para obtener el ZIP.");
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const download = (batchId: number) => {
    window.open(`/api/v1/batches/${batchId}/package`, "_blank");
  };

  // --- Derivados ------------------------------------------------------------
  const candidatas = useMemo(() => {
    const base = (stories ?? []).filter((s) => !checked.has(s.id));
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
  }, [stories, checked, estadoFiltro, orden, texto]);

  const totalPaginas = Math.max(1, Math.ceil(candidatas.length / TAMANO_PAGINA));
  const paginaActual = Math.min(pagina, totalPaginas);
  const visibles = candidatas.slice(
    (paginaActual - 1) * TAMANO_PAGINA,
    paginaActual * TAMANO_PAGINA,
  );

  const seleccionadas = useMemo(
    () => (stories ?? []).filter((s) => checked.has(s.id)),
    [stories, checked],
  );

  const pendingCount = checked.size < targetSize ? targetSize - checked.size : 0;

  const columnasNoticia: Columna<StoryListItem>[] = [
    {
      clave: "id",
      cabecera: "#",
      ancho: "3.75rem",
      numerica: true,
      render: (s) => <span className="id">{s.id}</span>,
    },
    {
      clave: "tema",
      cabecera: "Noticia",
      // Ancho mínimo de la columna larga (ver `docs/DISENO.md`).
      ancho: "20rem",
      render: (s) => (
        <Link href={`/noticias/${s.id}`} className="text-ink hover:text-info">
          {s.title}
        </Link>
      ),
    },
    {
      clave: "estado",
      cabecera: "Estado",
      ancho: "9.5rem",
      render: (s) => (
        <Estado
          tono={TONO_POR_ESTADO[s.status] ?? "idle"}
          etiqueta={s.status_label}
          variante="punto"
        />
      ),
    },
    {
      clave: "puntuacion",
      cabecera: "Puntuación",
      ancho: "4.5rem",
      numerica: true,
      secundaria: true,
      render: (s) => <span className="num">{s.editorial_score ?? "—"}</span>,
    },
    {
      clave: "fecha",
      cabecera: "fecha",
      ancho: "9.5rem",
      secundaria: true,
      render: (s) => <span className="num">{fmtDate(s.created_at)}</span>,
    },
    {
      clave: "anadir",
      cabecera: "acción",
      ancho: "6rem",
      render: (s) => (
        <button
          type="button"
          className="btn-sm"
          onClick={() => toggle(s.id)}
          disabled={checked.size >= targetSize}
          title={`Añadir «${s.title}» al lote`}
        >
          Añadir
        </button>
      ),
    },
  ];

  const columnasLote: Columna<LoteResumen>[] = [
    {
      clave: "id",
      cabecera: "#",
      ancho: "3.75rem",
      numerica: true,
      render: (b) => <span className="id">{b.id}</span>,
    },
    {
      clave: "nombre",
      cabecera: "Lote",
      render: (b) => (
        <button
          type="button"
          className="text-left text-ink hover:text-info"
          onClick={() => void open(b.id)}
        >
          {b.name || `Lote #${b.id}`}
        </button>
      ),
    },
    {
      clave: "tamano",
      cabecera: "Tamaño",
      ancho: "4.5rem",
      numerica: true,
      secundaria: true,
      render: (b) => <span className="num">{b.target_size}</span>,
    },
    {
      clave: "estado",
      cabecera: "Estado",
      ancho: "9.5rem",
      render: (b) => (
        <Estado
          tono={TONO_POR_LOTE[b.status] ?? "idle"}
          etiqueta={ETIQUETA_PAQUETE[b.status] ?? b.status}
          variante="punto"
        />
      ),
    },
    {
      clave: "fecha",
      cabecera: "Creado",
      ancho: "9.5rem",
      secundaria: true,
      render: (b) => <span className="num">{fmtDate(b.created_at)}</span>,
    },
  ];

  // --- Estados de página ----------------------------------------------------
  if (batches === null && error) {
    return (
      <Panel titulo="Lotes · sin datos" meta="error de lectura">
        <div className="alerta-fila alerta-fila-err" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p>No se ha podido leer la lista de lotes.</p>
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

  if (batches === null) {
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
        <Panel titulo="Catálogo de noticias" meta="cargando">
          <EsqueletoTabla filas={8} />
        </Panel>
        <span className="sr-only">Cargando los lotes…</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* --- Banda de cabecera ------------------------------------------------ */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1">
            <h1 className="text-sm font-semibold tracking-tight text-ink">
              Lotes editoriales (5 o 10 noticias)
            </h1>
            <Estado
              tono={selected ? (selected.pending_count > 0 ? "warn" : "ok") : "idle"}
              etiqueta={
                selected
                  ? selected.pending_count > 0
                    ? `${selected.pending_count} pendientes`
                    : "listo para grabar"
                  : "sin lote abierto"
              }
              variante="punto"
            />
            <span className="ops-panel-meta">
              {batches.length} lotes · {stories?.length ?? 0} noticias
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
              <p>La última operación ha fallido; se conserva la lectura anterior.</p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{error}</p>
            </div>
          </div>
        ) : null}

        {errorTrabajo ? (
          <div className="alerta-fila alerta-fila-warn border-l-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>El trabajo de exportación ha terminado con error.</p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{errorTrabajo}</p>
            </div>
          </div>
        ) : null}

        {notice ? (
          <div className="alerta-fila" role="status">
            <IconoCaja className="mt-0.5 shrink-0 text-ok" />
            <p className="text-ink-2">{notice}</p>
          </div>
        ) : null}

        {waiting !== null ? (
          <div className="alerta-fila" role="status">
            <IconoFlecha className="mt-0.5 shrink-0 text-info" />
            <p className="text-ink-2">
              Exportando (trabajo{" "}
              <span className="font-mono tabular-nums text-ink">#{waiting}</span>)…
            </p>
          </div>
        ) : null}
      </section>

      {/* --- Telemetría -------------------------------------------------------- */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <h2 className="ops-panel-title">Situación</h2>
        </div>
        <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          <Metrica etiqueta="noticias" valor={String(stories?.length ?? 0)} />
          <Metrica
            etiqueta="seleccionadas"
            valor={`${checked.size}/${targetSize}`}
            tono={checked.size === targetSize ? "ok" : "neutro"}
            pista={pendingCount > 0 ? `faltan ${pendingCount}` : "lote completo"}
          />
          <Metrica etiqueta="lotes" valor={String(batches.length)} />
          <Metrica
            etiqueta="lote · aprobadas"
            valor={selected ? String(selected.ready_count) : "—"}
            tono={selected && selected.ready_count > 0 ? "ok" : "neutro"}
          />
          <Metrica
            etiqueta="lote · pendientes"
            valor={selected ? String(selected.pending_count) : "—"}
            tono={selected && selected.pending_count > 0 ? "warn" : "neutro"}
          />
          <Metrica
            etiqueta="paquetes"
            valor={selected?.packages?.length ? String(selected.packages.length) : "0"}
          />
        </div>
      </section>

      {/* --- Rejilla principal: composición | contexto ------------------------ */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-3">
          {/* --- Componer el lote ------------------------------------------- */}
          <Panel
            titulo="Componer lote"
            meta={`${checked.size} de ${targetSize} seleccionadas`}
            acciones={
              <button
                type="button"
                className="btn-primary"
                onClick={() => void create()}
                disabled={checked.size !== targetSize}
              >
                Crear lote ({checked.size}/{targetSize})
              </button>
            }
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="ops-panel-title">tamaño</span>
              {TAMANOS.map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => changeSize(size)}
                  className={`filtro ${targetSize === size ? "filtro-on" : ""}`}
                  aria-label={`Lotes de ${size} noticias`}
                >
                  {size}
                </button>
              ))}
              <input
                className="input max-w-64"
                placeholder="Nombre del lote (opcional)"
                aria-label="Nombre del lote"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            {pendingCount > 0 ? (
              <p className="mt-2 text-xs text-ink-3">
                Selecciona {pendingCount} noticia{pendingCount === 1 ? "" : "s"} más para completar el
                lote.
              </p>
            ) : null}

            {seleccionadas.length > 0 ? (
              <ul className="mt-2 flex flex-col gap-1">
                {seleccionadas.map((s) => (
                  <li
                    key={s.id}
                    className="flex flex-wrap items-center gap-2 border-b border-line/60 pb-1 text-sm last:border-b-0"
                  >
                    <Estado
                      tono={TONO_POR_ESTADO[s.status] ?? "idle"}
                      etiqueta={s.status_label}
                      variante="punto"
                    />
                    <span className="min-w-0 truncate">{s.title}</span>
                    <button
                      type="button"
                      className="btn-sm ml-auto"
                      onClick={() => toggle(s.id)}
                      title={`Quitar «${s.title}» del lote`}
                    >
                      <IconoCruce /> quitar
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </Panel>

          {/* --- Catálogo de noticias --------------------------------------- */}
          <Panel titulo="Filtros" meta={`${candidatas.length} noticias disponibles`}>
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
              <label className="sr-only" htmlFor="orden-lotes">
                Ordenar noticias
              </label>
              <select
                id="orden-lotes"
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
            titulo="Noticias disponibles"
            meta={`${visibles.length} de ${candidatas.length}`}
            relleno="flush"
            acciones={
              <>
                {COLUMNAS_NOTICIA.map((columna) => (
                  <button
                    key={columna.clave}
                    type="button"
                    className={`filtro ${!ocultasNoticia.includes(columna.clave) ? "filtro-on" : ""}`}
                    onClick={() =>
                      setOcultasNoticia((actual) =>
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
              columnas={columnasNoticia}
              filas={visibles}
              claveFila={(s) => String(s.id)}
              ocultas={ocultasNoticia}
              vacio={
                <Vacio
                  titulo="No hay noticias con estos filtros"
                  pista="Quita los filtros o revisa que no estén ya dentro del lote que estás componiendo."
                  icono={<IconoFlecha />}
                />
              }
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-3 py-2">
              <span className="ops-panel-meta">
                página {paginaActual} de {totalPaginas} · {candidatas.length} resultados
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

        {/* --- Columna de contexto --------------------------------------------- */}
        <div className="min-w-0 space-y-3">
          <Panel
            titulo="Lotes existentes"
            meta={`${batches.length}`}
            relleno="flush"
            acciones={
              <>
                {COLUMNAS_LOTE.map((columna) => (
                  <button
                    key={columna.clave}
                    type="button"
                    className={`filtro ${!ocultasLote.includes(columna.clave) ? "filtro-on" : ""}`}
                    onClick={() =>
                      setOcultasLote((actual) =>
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
              columnas={columnasLote}
              filas={batches}
              claveFila={(b) => String(b.id)}
              ocultas={ocultasLote}
              vacio={
                <Vacio
                  titulo="Todavía no hay lotes"
                  pista="Compón el primer lote seleccionando 5 o 10 noticias aprobadas en el catálogo."
                  icono={<IconoCaja />}
                />
              }
            />
          </Panel>

          {selected ? (
            <Panel
              titulo={`Lote #${selected.id}`}
              meta={selected.name || "sin nombre"}
              acciones={
                <>
                  <button type="button" className="btn-sm-primary" onClick={() => void exportPackage()}>
                    Exportar paquete
                  </button>
                  {selected.packages && selected.packages.length > 0 ? (
                    <button type="button" className="btn-sm" onClick={() => download(selected.id)}>
                      Descargar ZIP
                    </button>
                  ) : null}
                </>
              }
            >
              <div className="grid grid-cols-2 gap-2">
                <Metrica
                  etiqueta="aprobadas"
                  valor={String(selected.ready_count)}
                  tono={selected.ready_count > 0 ? "ok" : "neutro"}
                />
                <Metrica
                  etiqueta="pendientes"
                  valor={String(selected.pending_count)}
                  tono={selected.pending_count > 0 ? "warn" : "neutro"}
                />
              </div>

              {selected.pending_count > 0 ? (
                <p className="mt-2 text-xs text-ink-3">
                  Ninguna noticia pendiente puede grabarse todavía.
                </p>
              ) : null}

              <ol className="mt-3 flex flex-col gap-1">
                {selected.stories.map((s) => (
                  <li
                    key={s.story_id}
                    className="flex flex-wrap items-center gap-2 border-b border-line/60 pb-1 text-xs last:border-b-0"
                  >
                    <span className="font-mono tabular-nums text-ink-3">{s.position + 1}.</span>
                    <Link href={`/noticias/${s.story_id}`} className="min-w-0 text-ink hover:text-info">
                      {s.title}
                    </Link>
                    {s.approved ? (
                      <span className="badge-ok">Aprobada</span>
                    ) : (
                      <span className="badge-warn">Pendiente de aprobación</span>
                    )}
                    {s.pending_reason ? (
                      <span className="text-ink-3">{s.pending_reason}</span>
                    ) : null}
                    <span className="ml-auto flex gap-1">
                      <button
                        type="button"
                        className="btn-sm"
                        onClick={() => void move(s.story_id, -1)}
                        disabled={s.position === 0}
                        title={`Subir «${s.title}» en el lote`}
                      >
                        subir
                      </button>
                      <button
                        type="button"
                        className="btn-sm"
                        onClick={() => void move(s.story_id, 1)}
                        disabled={s.position === selected.stories.length - 1}
                        title={`Bajar «${s.title}» en el lote`}
                      >
                        bajar
                      </button>
                    </span>
                  </li>
                ))}
              </ol>

              {selected.packages && selected.packages.length > 0 ? (
                <p className="mt-2 font-mono text-[11px] tabular-nums text-ink-3">
                  Último paquete: v{selected.packages[0].version} · sha256{" "}
                  {selected.packages[0].sha256.slice(0, 16)}… · {fmtDate(selected.packages[0].created_at)}
                </p>
              ) : null}
            </Panel>
          ) : (
            <Panel titulo="Lote abierto">
              <Vacio
                titulo="Ningún lote abierto"
                pista="Elige un lote de la lista para ver su orden, exportarlo o descargar su ZIP."
                icono={<IconoCaja />}
              />
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LotesPage() {
  return (
    <Suspense fallback={<EsqueletoLotes />}>
      <LotesVista />
    </Suspense>
  );
}

/** Esqueleto con la forma real de la vista (nada de spinners). */
function EsqueletoLotes() {
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
      <Panel titulo="Catálogo de noticias" meta="cargando">
        <EsqueletoTabla filas={8} />
      </Panel>
      <span className="sr-only">Cargando los lotes…</span>
    </div>
  );
}
