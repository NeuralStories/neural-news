"use client";

/**
 * Fuentes: el inventario de lo que ha entrado al sistema.
 *
 * Migrada al sistema visual (tokens semánticos, `Panel`, `TablaOps`, `Estado`):
 * tabla densa con filtros **en la URL**, columnas ocultables y el detalle de la
 * fuente seleccionada en una columna lateral (en vez de desplegar filas: el
 * alto de la tabla no baila al abrir un detalle).
 *
 * No cambia la API ni la lógica: se usan las mismas llamadas que antes
 * (`listSources`, `addSource`, `getSource`, `getTranscript`, `addTranscript`,
 * `transcribeSource`, `processSource`, `analyzeVideo`).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { BADGE_DE_FUENTE, ETIQUETA_FUENTE, insigniaDe } from "@/lib/estados";
import { idempotenciaDe } from "@/lib/http";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { SourceDetail, SourceListItem } from "@/lib/types";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna } from "@/components/ui/tabla";
import { EsqueletoPanel, EsqueletoTabla, Vacio } from "@/components/ui/estados";
import {
  IconoAlerta,
  IconoBuscar,
  IconoCaja,
  IconoCheck,
  IconoCruce,
  IconoFlecha,
  IconoRefrescar,
} from "@/components/ui/icono";

const LIMITE_PAGINA = 25;

const TONOS: Record<string, TonoEstado> = {
  "badge-ok": "ok",
  "badge-warn": "warn",
  "badge-err": "crit",
  "badge-info": "info",
  "badge-neutral": "idle",
};

function tonoDeFuente(estado: string): TonoEstado {
  return TONOS[insigniaDe(BADGE_DE_FUENTE, estado)] ?? "idle";
}

/** Columnas secundarias (ocultables por el operador). */
const COLUMNAS_SECUNDARIAS = ["proveedor", "autor", "publicada", "importada"];

export default function FuentesPage() {
  const router = useRouter();
  const parametros = useSearchParams();

  const estado = parametros.get("estado") ?? "";
  const proveedor = parametros.get("proveedor") ?? "";
  const texto = parametros.get("q") ?? "";
  const pagina = Number(parametros.get("pagina") ?? "1");

  const [items, setItems] = useState<SourceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seleccionada, setSeleccionada] = useState<number | null>(null);
  const [ocultas, setOcultas] = useState<string[]>([]);
  const [url, setUrl] = useState("");
  const [textoFuente, setTextoFuente] = useState("");
  const [modo, setModo] = useState<"url" | "texto">("url");
  const [aviso, setAviso] = useState<string | null>(null);
  const { waiting, error: errorTrabajo, poll, stop } = useJobPolling();

  const actualizarUrl = useCallback(
    (cambios: Record<string, string>) => {
      const siguiente = new URLSearchParams(parametros.toString());
      for (const [clave, valor] of Object.entries(cambios)) {
        if (valor) siguiente.set(clave, valor);
        else siguiente.delete(clave);
      }
      router.replace(`/fuentes${siguiente.toString() ? `?${siguiente}` : ""}`, {
        scroll: false,
      });
    },
    [parametros, router],
  );

  const refrescar = useCallback(async () => {
    setCargando(true);
    try {
      const consulta = new URLSearchParams();
      if (estado) consulta.set("status", estado);
      if (proveedor) consulta.set("provider", proveedor);
      consulta.set("limit", String(LIMITE_PAGINA * pagina));
      // El cliente concatena la consulta a la ruta: tiene que llevar el «?».
      const datos = await api.listSources(`?${consulta.toString()}`);
      setItems(datos.items);
      setTotal(datos.total);
      setError(null);
    } catch (fallo) {
      setError((fallo as Error).message);
    } finally {
      setCargando(false);
    }
  }, [estado, proveedor, pagina]);

  useEffect(() => {
    void refrescar();
  }, [refrescar]);

  const proveedores = useMemo(
    () => Array.from(new Set(items.map((fuente) => fuente.provider))).sort(),
    [items],
  );

  const visibles = useMemo(() => {
    const busqueda = texto.trim().toLowerCase();
    if (!busqueda) return items;
    return items.filter((fuente) =>
      [fuente.title, fuente.author, fuente.canonical_url, fuente.provider]
        .filter(Boolean)
        .some((campo) => String(campo).toLowerCase().includes(busqueda)),
    );
  }, [items, texto]);

  const archivoRef = useRef<HTMLInputElement | null>(null);

  /** Reprocesa una fuente y espera al trabajo. */
  const reprocesar = useCallback(
    async (id: number) => {
      try {
        const res = await api.processSource(id);
        setAviso("Reprocesando la fuente…");
        await poll(res.job_id, async () => {
          await refrescar();
        });
      } catch (fallo) {
        setAviso(`No se pudo reprocesar: ${(fallo as Error).message}`);
      }
    },
    [poll, refrescar],
  );

  /** Pide el análisis de vídeo de una fuente y espera al trabajo. */
  const analizar = useCallback(
    async (id: number) => {
      try {
        const res = await api.analyzeVideo(id);
        setAviso("Analizando el vídeo…");
        await poll(res.job_id, async () => {
          await refrescar();
        });
      } catch (fallo) {
        setAviso(`No se pudo analizar el vídeo: ${(fallo as Error).message}`);
      }
    },
    [poll, refrescar],
  );

  const columnas: Columna<SourceListItem>[] = useMemo(
    () => [
      {
        clave: "id",
        cabecera: "#",
        ancho: "4.5rem",
        numerica: true,
        render: (fuente) => <span className="id">{fuente.id}</span>,
      },
      {
        clave: "proveedor",
        cabecera: "Tipo",
        ancho: "8rem",
        secundaria: true,
        render: (fuente) => <span className="text-ink-2">{fuente.provider}</span>,
      },
      {
        clave: "estado",
        cabecera: "Estado",
        ancho: "10rem",
        render: (fuente) => (
          <Estado
            tono={tonoDeFuente(fuente.status)}
            etiqueta={ETIQUETA_FUENTE[fuente.status] ?? fuente.status_label ?? fuente.status}
            variante="punto"
          />
        ),
      },
      {
        clave: "titulo",
        cabecera: "Título",
        // Ancho mínimo: la columna larga no puede quedarse con el sobrante
        // (el título se partía en ocho líneas y la tabla se descuadraba).
        ancho: "20rem",
        render: (fuente) => (
          <span className="text-ink" title={fuente.title ?? ""}>
            {fuente.title ?? <span className="id">sin título</span>}
          </span>
        ),
      },
      {
        clave: "enlace",
        cabecera: "Enlace",
        ancho: "12rem",
        secundaria: true,
        render: (fuente) =>
          fuente.canonical_url ? (
            <a
              className="text-info hover:underline"
              href={fuente.canonical_url}
              target="_blank"
              rel="noreferrer"
              title={fuente.canonical_url}
            >
              {fuente.canonical_url.replace(/^https?:\/\//, "").slice(0, 40)}
            </a>
          ) : (
            <span className="id">—</span>
          ),
      },
      {
        clave: "autor",
        cabecera: "Autor",
        ancho: "9rem",
        secundaria: true,
        render: (fuente) => <span className="text-ink-3">{fuente.author ?? "—"}</span>,
      },
      {
        clave: "publicada",
        cabecera: "Fecha original",
        ancho: "10rem",
        numerica: true,
        secundaria: true,
        render: (fuente) => <span className="num">{fmtDate(fuente.published_at)}</span>,
      },
      {
        clave: "importada",
        cabecera: "Importada",
        ancho: "10rem",
        numerica: true,
        secundaria: true,
        render: (fuente) => <span className="num">{fmtDate(fuente.imported_at)}</span>,
      },
      {
        clave: "acciones",
        cabecera: "Acciones",
        ancho: "9rem",
        numerica: true,
        render: (fuente) => (
          <span className="flex items-center gap-1">
            {/*
              Acciones rápidas por fila. Los rótulos («Volver a analizar»,
              «Analizar vídeo») son parte del contrato que comprueba el E2E.
            */}
            <button
              type="button"
              className="filtro"
              aria-label="Volver a analizar"
              title="Volver a analizar"
              disabled={waiting !== null}
              onClick={() => void reprocesar(fuente.id)}
            >
              <IconoRefrescar />
            </button>
            <button
              type="button"
              className="filtro"
              aria-label="Analizar vídeo"
              title="Analizar vídeo"
              disabled={waiting !== null}
              onClick={() => void analizar(fuente.id)}
            >
              <IconoFlecha />
            </button>
            <button
              type="button"
              className="filtro"
              aria-label={seleccionada === fuente.id ? "Cerrar el detalle" : "Ver el detalle"}
              title={seleccionada === fuente.id ? "Cerrar el detalle" : "Ver el detalle"}
              onClick={() => setSeleccionada(seleccionada === fuente.id ? null : fuente.id)}
            >
              {seleccionada === fuente.id ? <IconoCruce /> : <IconoFlecha />}
            </button>
          </span>
        ),
      },
    ],
    [seleccionada, waiting, reprocesar, analizar],
  );

  const añadir = async (payload: Record<string, unknown>) => {
    setAviso(null);
    try {
      const resultado = await api.addSource(payload, idempotenciaDe(payload));
      setAviso(resultado.message ?? `Fuente #${resultado.source.id} en cola.`);
      setUrl("");
      await refrescar();
    } catch (fallo) {
      setAviso(`No se pudo añadir la fuente: ${(fallo as Error).message}`);
    }
  };

  const subirArchivo = async (fichero: File) => {
    const datos = new FormData();
    datos.append("file", fichero);
    try {
      const respuesta = await fetch("/api/v1/sources", { method: "POST", body: datos });
      if (!respuesta.ok) {
        setAviso(`No se pudo subir el fichero (HTTP ${respuesta.status}).`);
        return;
      }
      setAviso(`Fichero «${fichero.name}» en cola.`);
      await refrescar();
    } catch (fallo) {
      setAviso(`No se pudo subir el fichero: ${(fallo as Error).message}`);
    }
  };

  return (
    <div className="space-y-3">
      {/* --- Alta de fuente ------------------------------------------------- */}
      <Panel
        titulo="Añadir fuente"
        meta="URL o texto"
        acciones={
          <button
            type="button"
            className="btn-sm"
            onClick={() => void refrescar()}
            disabled={cargando}
          >
            <IconoRefrescar />
            {cargando ? "leyendo…" : "refrescar"}
          </button>
        }
      >
        {/*
          Modos de alta. Los rótulos («Aportar texto, archivo o transcripción» y
          «Registrar y analizar») son parte del contrato que comprueban las
          pruebas de Playwright: no se cambian sin actualizar las pruebas.
        */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            className={`filtro ${modo === "url" ? "filtro-on" : ""}`}
            onClick={() => setModo("url")}
          >
            URL
          </button>
          <button
            type="button"
            className={`filtro ${modo === "texto" ? "filtro-on" : ""}`}
            onClick={() => setModo("texto")}
          >
            Aportar texto, archivo o transcripción
          </button>
        </div>

        {modo === "url" ? (
          <div className="mt-3">
            <label className="ops-panel-title" htmlFor="url-fuente">
              URL
            </label>
            <input
              id="url-fuente"
              className="input mt-1 font-mono"
              placeholder="https://… (YouTube, Spotify, artículo o feed RSS)"
              value={url}
              onChange={(evento) => setUrl(evento.target.value)}
            />
          </div>
        ) : (
          <div className="mt-3">
            <label className="ops-panel-title" htmlFor="texto-fuente">
              texto de la fuente
            </label>
            <textarea
              id="texto-fuente"
              className="input mt-1 h-28 font-mono text-xs"
              placeholder="Pega aquí el artículo, la transcripción o la nota…"
              value={textoFuente}
              onChange={(evento) => setTextoFuente(evento.target.value)}
            />
          </div>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            className="btn-sm-primary"
            disabled={modo === "url" ? !url.trim() : !textoFuente.trim()}
            onClick={() => {
              if (modo === "url") {
                if (url.trim()) void añadir({ url: url.trim() });
              } else if (textoFuente.trim()) {
                void añadir({
                  title: textoFuente.trim().slice(0, 120),
                  text: textoFuente.trim(),
                });
              }
            }}
          >
            <IconoCaja /> Registrar y analizar
          </button>
          <input
            ref={archivoRef}
            type="file"
            className="hidden"
            aria-label="Subir un fichero como fuente"
            onChange={(evento) => {
              const fichero = evento.target.files?.[0];
              if (fichero) void subirArchivo(fichero);
              evento.target.value = "";
            }}
          />
          <button
            type="button"
            className="btn-sm"
            onClick={() => archivoRef.current?.click()}
          >
            <IconoCaja /> subir fichero
          </button>
        </div>
        {aviso ? (
          <div className="alerta-fila alerta-fila-warn mt-3" role="status">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <p>{aviso}</p>
          </div>
        ) : null}
        {errorTrabajo ? (
          <div className="alerta-fila alerta-fila-err mt-3" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <p>{errorTrabajo}</p>
          </div>
        ) : null}
      </Panel>

      {/* --- Inventario + detalle ------------------------------------------- */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Panel
          titulo="Fuentes registradas"
          meta={`${visibles.length} de ${total}`}
          relleno="flush"
          acciones={
            <>
              <input
                className="input-compact w-40"
                placeholder="filtrar por texto…"
                defaultValue={texto}
                onChange={(evento) => actualizarUrl({ q: evento.target.value, pagina: "1" })}
                aria-label="Filtrar fuentes por texto"
              />
              <select
                className="input-compact w-32"
                value={estado}
                onChange={(evento) => actualizarUrl({ estado: evento.target.value, pagina: "1" })}
                aria-label="Filtrar por estado"
              >
                <option value="">todos los estados</option>
                {Object.entries(ETIQUETA_FUENTE).map(([clave, etiqueta]) => (
                  <option key={clave} value={clave}>
                    {etiqueta}
                  </option>
                ))}
              </select>
              <select
                className="input-compact w-32"
                value={proveedor}
                onChange={(evento) => actualizarUrl({ proveedor: evento.target.value, pagina: "1" })}
                aria-label="Filtrar por proveedor"
              >
                <option value="">todos los proveedores</option>
                {proveedores.map((nombre) => (
                  <option key={nombre} value={nombre}>
                    {nombre}
                  </option>
                ))}
              </select>
              {COLUMNAS_SECUNDARIAS.map((clave) => (
                <button
                  key={clave}
                  type="button"
                  className={`filtro ${!ocultas.includes(clave) ? "filtro-on" : ""}`}
                  onClick={() =>
                    setOcultas((actual) =>
                      actual.includes(clave)
                        ? actual.filter((item) => item !== clave)
                        : [...actual, clave],
                    )
                  }
                  title="Mostrar u ocultar columna"
                >
                  {clave}
                </button>
              ))}
            </>
          }
        >
          {cargando && items.length === 0 ? (
            <EsqueletoTabla filas={8} />
          ) : (
            <>
              {error ? (
                <div className="alerta-fila alerta-fila-err" role="alert">
                  <IconoAlerta className="mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <p>No se pudo leer el inventario de fuentes.</p>
                    <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{error}</p>
                  </div>
                </div>
              ) : null}
              <TablaOps
                columnas={columnas}
                filas={visibles}
                claveFila={(fuente) => String(fuente.id)}
                vacio={
                  <Vacio
                    titulo="No hay fuentes con estos filtros"
                    pista="Añade una URL arriba o quita los filtros de la barra."
                    icono={<IconoCaja />}
                  />
                }
              />
            </>
          )}
          <div className="flex items-center justify-between gap-2 border-t border-line px-3 py-2">
            <span className="ops-panel-meta">
              página {pagina} · {total} en total
            </span>
            <span className="flex items-center gap-1.5">
              <button
                type="button"
                className="filtro"
                disabled={pagina <= 1}
                onClick={() => actualizarUrl({ pagina: String(pagina - 1) })}
              >
                anterior
              </button>
              <button
                type="button"
                className="filtro"
                disabled={visibles.length < LIMITE_PAGINA && pagina * LIMITE_PAGINA >= total}
                onClick={() => actualizarUrl({ pagina: String(pagina + 1) })}
              >
                siguiente
              </button>
            </span>
          </div>
        </Panel>

        <DetalleFuente
          id={seleccionada}
          onCambio={refrescar}
          poll={poll}
          waiting={waiting}
          stop={stop}
        />
      </div>
    </div>
  );
}

/* --- Detalle -------------------------------------------------------------- */

type PropsDetalle = {
  id: number | null;
  onCambio: () => Promise<void>;
  poll: (jobId: number, onDone?: (info: { status: string; error: string | null }) => void) => Promise<{
    status: string;
    error: string | null;
  }>;
  waiting: number | null;
  stop: () => void;
};

function DetalleFuente({ id, onCambio, poll, waiting }: PropsDetalle) {
  const [detalle, setDetalle] = useState<SourceDetail | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcripcion, setTranscripcion] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (id === null) {
      setDetalle(null);
      return;
    }
    setCargando(true);
    try {
      setDetalle(await api.getSource(id));
      setError(null);
    } catch (fallo) {
      setError((fallo as Error).message);
    } finally {
      setCargando(false);
    }
  }, [id]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  if (id === null) {
    return (
      <Panel titulo="Detalle" meta="sin selección">
        <Vacio
          titulo="Ninguna fuente seleccionada"
          pista="Pulsa la flecha de una fila para ver su contenido, su transcripción y sus noticias."
          icono={<IconoCaja />}
        />
      </Panel>
    );
  }

  if (cargando && !detalle) {
    return (
      <Panel titulo="Detalle" meta={`fuente #${id}`}>
        <EsqueletoPanel lineas={5} />
      </Panel>
    );
  }

  if (error && !detalle) {
    return (
      <Panel titulo="Detalle" meta={`fuente #${id}`}>
        <div className="alerta-fila alerta-fila-err" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
        <button type="button" className="btn-sm mt-3" onClick={() => void cargar()}>
          <IconoRefrescar /> reintentar
        </button>
      </Panel>
    );
  }

  return (
    <Panel
      titulo="Detalle"
      meta={`fuente #${id}`}
      acciones={
        <button
          type="button"
          className="btn-sm"
          onClick={() => void cargar()}
          aria-label="Actualizar el detalle de la fuente"
          title="Actualizar el detalle de la fuente"
        >
          <IconoRefrescar />
        </button>
      }
    >
      {error ? (
        <div className="alerta-fila alerta-fila-err mb-3" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      ) : null}
      {mensaje ? (
        <div className="alerta-fila alerta-fila-warn mb-3" role="status">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <p>{mensaje}</p>
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-2">
        <Metrica etiqueta="contenidos" valor={String(detalle?.contents.length ?? 0)} />
        <Metrica etiqueta="noticias" valor={String(detalle?.stories.length ?? 0)} />
      </div>

      <div className="mt-3">
        <span className="ops-panel-title">contenidos</span>
        {detalle?.contents.length ? (
          detalle.contents.map((contenido) => (
            <div key={contenido.id} className="kv">
              <span className="kv-clave truncate" title={contenido.content_type_label}>
                {contenido.content_type_label}
              </span>
              <Estado
                tono={contenido.is_verbatim ? "info" : "idle"}
                etiqueta={contenido.is_verbatim ? "verbatim" : "derivado"}
                variante="punto"
              />
              <span className="kv-valor">
                {contenido.char_count.toLocaleString("es-ES")} car.
              </span>
            </div>
          ))
        ) : (
          <p className="ops-panel-meta mt-1">sin contenidos extraídos</p>
        )}
      </div>

      <div className="mt-3">
        <span className="ops-panel-title">noticias extraídas</span>
        {detalle?.stories.length ? (
          detalle.stories.map((noticia) => (
            <div key={noticia.id} className="kv">
              <span className="kv-clave truncate">{noticia.title}</span>
              <Estado
                tono={tonoDeFuente(noticia.status)}
                etiqueta={noticia.status_label}
                variante="punto"
              />
            </div>
          ))
        ) : (
          <p className="ops-panel-meta mt-1">todavía no hay noticias</p>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <button
          type="button"
          className="btn-sm"
          disabled={waiting !== null}
          onClick={async () => {
            const res = await api.processSource(id);
            setMensaje("Reprocesando la fuente…");
            await poll(res.job_id, async () => {
              await cargar();
              await onCambio();
            });
          }}
        >
          <IconoRefrescar /> Volver a analizar
        </button>
        <button
          type="button"
          className="btn-sm"
          disabled={waiting !== null}
          onClick={async () => {
            const res = await api.analyzeVideo(id);
            setMensaje("Analizando el vídeo…");
            await poll(res.job_id, async () => {
              await cargar();
              await onCambio();
            });
          }}
        >
          <IconoFlecha /> Analizar vídeo
        </button>
        <button
          type="button"
          className="btn-sm"
          disabled={waiting !== null}
          onClick={async () => {
            const res = await api.transcribeSource(id);
            setMensaje("Transcribiendo…");
            await poll(res.job_id, async () => {
              await cargar();
              await onCambio();
            });
          }}
        >
          <IconoCheck /> Transcribir
        </button>
        <button
          type="button"
          className="btn-sm"
          onClick={async () => {
            try {
              const info = await api.getTranscript(id);
              setTranscripcion(info.text ?? "");
              setMensaje(
                info.found
                  ? "Transcripción cargada."
                  : (info.message ?? "La fuente todavía no tiene transcripción."),
              );
            } catch (fallo) {
              setMensaje(`No se pudo leer la transcripción: ${(fallo as Error).message}`);
            }
          }}
        >
          <IconoBuscar /> Buscar transcripción
        </button>
      </div>

      <div className="mt-3">
        <label className="ops-panel-title" htmlFor="transcripcion">
          transcripción
        </label>
        <textarea
          id="transcripcion"
          className="input mt-1 h-24 font-mono text-xs"
          value={transcripcion}
          onChange={(evento) => setTranscripcion(evento.target.value)}
          placeholder="Pega aquí la transcripción si la fuente no la trae…"
        />
        <div className="mt-2">
          <button
            type="button"
            className="btn-sm"
            disabled={!transcripcion.trim()}
            onClick={async () => {
              try {
                await api.addTranscript(id, transcripcion);
                setMensaje("Transcripción guardada.");
                await cargar();
                await onCambio();
              } catch (fallo) {
                setMensaje(`No se pudo guardar: ${(fallo as Error).message}`);
              }
            }}
          >
            <IconoCheck /> guardar transcripción
          </button>
        </div>
      </div>
    </Panel>
  );
}
