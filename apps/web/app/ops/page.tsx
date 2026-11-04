"use client";

/**
 * Operación: la consola del sistema.
 *
 * Esta vista es la **superficie de referencia** del sistema visual: fija los
 * tokens, los estados semánticos, la rejilla de 1px y los patrones de
 * tabla/telemetría que reutilizarán el resto de vistas.
 *
 * Decisiones:
 * - **Cero dependencias**: todo sale del sistema de estilos de `globals.css`
 *   y de los componentes de `components/ui/`.
 * - **Densidad antes que decoración**: cifras tabulares en monoespaciado,
 *   etiquetas en versalitas de 10 px y sin espacio que sobre.
 * - **El dato viejo no se tira**: si un refresco falla, la última lectura
 *   sigue en pantalla marcada como obsoleta (con el error exacto), porque un
 *   panel vacío durante un fallo de red es peor que un dato con su fecha.
 * - **Autorefresco de 15 s** con pausa manual: el operador decide si la
 *   pantalla se repinta sola; con la pestaña oculta no se sondea y al volver
 *   se lee inmediatamente.
 * - **Lectura parcial**: cada bloque (salud, trabajos, uso, proveedores,
 *   métricas) se lee por separado y el ciclo nuevo aborta al anterior en
 *   vuelo. Un fallo no tira la pantalla: los paneles que sí respondieron se
 *   pintan y los que no conservan su última lectura buena, marcada.
 * - **Cabeceras ordenables**: `#`, `estado` y `creado` ordenan en cliente;
 *   el tercer clic devuelve el orden del servidor (creado descendente).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type {
  AlertaOperacion,
  EstadoSalud,
  JobInfo,
  MetricasOperacion,
  ProviderStatus,
  UsageInfo,
} from "@/lib/types";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna, type OrdenTabla } from "@/components/ui/tabla";
import { EsqueletoMetrica, EsqueletoPanel, Vacio } from "@/components/ui/estados";
import {
  IconoAlerta,
  IconoCheck,
  IconoCruce,
  IconoPulso,
  IconoRefrescar,
  IconoReloj,
} from "@/components/ui/icono";

const INTERVALO_MS = 15_000;

/** Bloques independientes de la lectura: cada uno falla por su cuenta. */
type ClaveLectura = "salud" | "trabajos" | "uso" | "proveedores" | "metricas";

type Datos = {
  salud: EstadoSalud;
  trabajos: JobInfo[];
  uso: UsageInfo;
  proveedores: ProviderStatus[];
  metricas: MetricasOperacion;
  alertas: AlertaOperacion[];
};

/** Fallos de la última lectura, por bloque (vacío = lectura completa). */
type FalloLectura = Partial<Record<ClaveLectura, string>>;

type FiltroEstado = "todos" | "fallidos" | "en_curso" | "completados";

const FILTROS_ESTADO: Array<{ clave: FiltroEstado; etiqueta: string }> = [
  { clave: "todos", etiqueta: "todos" },
  { clave: "fallidos", etiqueta: "fallidos" },
  { clave: "en_curso", etiqueta: "en curso" },
  { clave: "completados", etiqueta: "completados" },
];

/** Columnas que el operador puede ocultar (las secundarias). */
const COLUMNAS_SECUNDARIAS = ["intento", "detalle"] as const;

/** Hora legible: hoy → HH:MM:SS; antes de hoy → `dd/mm HH:MM`. Una consola
 *  de operación no puede distinguir «hace 5 s» de «ayer» con la hora sola. */
function hora(iso?: string): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return "—";
  const hoy = new Date();
  const mismoDia =
    fecha.getFullYear() === hoy.getFullYear() &&
    fecha.getMonth() === hoy.getMonth() &&
    fecha.getDate() === hoy.getDate();
  if (mismoDia) return fecha.toLocaleTimeString("es-ES", { hour12: false });
  const dia = `${String(fecha.getDate()).padStart(2, "0")}/${String(fecha.getMonth() + 1).padStart(2, "0")}`;
  return `${dia} ${fecha.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
}

function porcentaje(fraction: number): string {
  return `${(fraction * 100).toFixed(1)} %`;
}

/** Primer fallo de una lectura (para el mensaje del banner de error). */
function primerFalloDe(lecturas: Array<{ fallo: string | null }>): string {
  return lecturas.find((lectura) => lectura.fallo)?.fallo ?? "error de lectura";
}

function tonoDeTrabajo(status: string): TonoEstado {
  if (status === "DONE") return "ok";
  if (status === "QUEUED" || status === "RUNNING") return "info";
  if (status === "FAILED" || status === "UNKNOWN") return "crit";
  return "idle";
}

function tonoDeProveedor(configured: boolean, state: string): TonoEstado {
  if (configured) return "ok";
  if (state === "mock") return "info";
  if (state === "fuera_de_mvp") return "idle";
  return "warn";
}

function etiquetaDeProveedor(configured: boolean, state: string): string {
  if (configured) return "configurado";
  if (state === "mock") return "simulado";
  if (state === "fuera_de_mvp") return "fuera de mvp";
  return "sin clave";
}

export default function OperacionPage() {
  const router = useRouter();
  const parametros = useSearchParams();
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fallos, setFallos] = useState<FalloLectura>({});
  const [ultimaLectura, setUltimaLectura] = useState<Date | null>(null);
  const [actualizando, setActualizando] = useState(false);
  const [autorefresco, setAutorefresco] = useState(true);
  const [orden, setOrden] = useState<OrdenTabla | null>(null);

  // Los filtros viven **en la URL**: una vista de operaciones se comparte
  // (mando, enlace) con el filtro puesto, y recargar no pierde el contexto.
  const filtroEstado = (parametros.get("estado") ?? "todos") as FiltroEstado;
  const filtroTipo = parametros.get("tipo") ?? "todos";
  // El filtro de alerta guarda el **código** de la alerta, no el array de
  // trabajos: cada ciclo trae objetos nuevos y una comparación por identidad
  // dejaba el filtro aplicado con el botón ya incapaz de quitarlo.
  const [codigoAlerta, setCodigoAlerta] = useState<string | null>(null);
  const [ocultas, setOcultas] = useState<string[]>([]);
  const controlador = useRef<AbortController | null>(null);
  const datosRef = useRef<Datos | null>(null);

  const actualizarUrl = useCallback(
    (cambios: Record<string, string>) => {
      const siguiente = new URLSearchParams(parametros.toString());
      for (const [clave, valor] of Object.entries(cambios)) {
        if (valor && valor !== "todos") siguiente.set(clave, valor);
        else siguiente.delete(clave);
      }
      router.replace(`/ops${siguiente.toString() ? `?${siguiente}` : ""}`, { scroll: false });
    },
    [parametros, router],
  );

  const cargar = useCallback(async () => {
    controlador.current?.abort();
    const actual = new AbortController();
    controlador.current = actual;
    const { signal } = actual;
    setActualizando(true);

    /** Un bloque que falla no propaga: devuelve su fallo para el banner. */
    const leer = async <T,>(
      clave: ClaveLectura,
      peticion: () => Promise<T>,
    ): Promise<{ clave: ClaveLectura; dato: T | null; fallo: string | null }> => {
      try {
        return { clave, dato: await peticion(), fallo: null };
      } catch (fallo) {
        if (signal.aborted || (fallo as Error).name === "AbortError") throw fallo;
        return { clave, dato: null, fallo: (fallo as Error).message };
      }
    };

    try {
      const [salud, trabajos, uso, proveedores, metricas] = await Promise.all([
        leer("salud", () => api.health({ signal })),
        leer("trabajos", () => api.listJobs({ signal })),
        leer("uso", () => api.usage({ signal })),
        leer("proveedores", () => api.providerStatus({ signal })),
        leer("metricas", () => api.metrics({ signal })),
      ]);
      if (signal.aborted) return;

      const previo = datosRef.current;
      const completos = [salud, trabajos, uso, proveedores, metricas].filter(
        (lectura) => lectura.fallo === null,
      );
      const nuevosFallos: FalloLectura = {};
      for (const lectura of [salud, trabajos, uso, proveedores, metricas]) {
        if (lectura.fallo) nuevosFallos[lectura.clave] = lectura.fallo;
      }
      setFallos(nuevosFallos);

      if (completos.length === 0) {
        // Lectura entera fallida: el dato viejo no se tira. Si no había
        // nada, es el error de arranque de siempre.
        setError(primerFalloDe([salud, trabajos, uso, proveedores, metricas]));
        return;
      }
      if (completos.length < 5 && !previo) {
        // Primera lectura parcial: sin datos previos que conservar.
        setError(primerFalloDe([salud, trabajos, uso, proveedores, metricas]));
        return;
      }

      // El bloque que falló conserva su última lectura buena (obsoleta).
      const siguiente: Datos = {
        salud: salud.dato ?? previo!.salud,
        trabajos: trabajos.dato ? trabajos.dato.items : previo!.trabajos,
        uso: uso.dato ?? previo!.uso,
        proveedores: proveedores.dato ? proveedores.dato.providers : previo!.proveedores,
        metricas: metricas.dato ? metricas.dato.metricas : previo!.metricas,
        alertas: metricas.dato ? metricas.dato.alertas : previo!.alertas,
      };
      datosRef.current = siguiente;
      setError(null);
      setDatos(siguiente);
      setUltimaLectura(new Date());
    } catch {
      /* lectura abortada por un ciclo más nuevo: no se pinta nada */
    } finally {
      if (!signal.aborted) setActualizando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  useEffect(() => {
    if (!autorefresco) return;
    const temporizador = setInterval(() => {
      // Pestaña oculta: el operador no está mirando, no se sondea.
      if (document.hidden) return;
      void cargar();
    }, INTERVALO_MS);
    return () => clearInterval(temporizador);
  }, [autorefresco, cargar]);

  // Al volver a la pestaña, lectura inmediata (el último ciclo pudo saltarse).
  useEffect(() => {
    const alVolver = () => {
      if (!document.hidden && autorefresco) void cargar();
    };
    document.addEventListener("visibilitychange", alVolver);
    return () => document.removeEventListener("visibilitychange", alVolver);
  }, [autorefresco, cargar]);

  const tipos = useMemo(() => {
    const distintos = new Set((datos?.trabajos ?? []).map((trabajo) => trabajo.type));
    return Array.from(distintos).sort();
  }, [datos]);

  // Trabajos de la alerta filtrada, derivados del **código**: estable entre
  // ciclos de autorefresco (los arrays llegan nuevos en cada lectura).
  const trabajosDeAlerta = useMemo(() => {
    if (!codigoAlerta) return null;
    return datos?.alertas.find((alerta) => alerta.codigo === codigoAlerta)?.trabajos ?? null;
  }, [codigoAlerta, datos]);

  const trabajosFiltrados = useMemo(() => {
    const base = datos?.trabajos ?? [];
    return base.filter((trabajo) => {
      if (filtroEstado === "fallidos" && trabajo.status !== "FAILED") return false;
      if (filtroEstado === "en_curso" && !(trabajo.status === "QUEUED" || trabajo.status === "RUNNING"))
        return false;
      if (filtroEstado === "completados" && trabajo.status !== "DONE") return false;
      if (filtroTipo !== "todos" && trabajo.type !== filtroTipo) return false;
      if (trabajosDeAlerta && !trabajosDeAlerta.includes(trabajo.id)) return false;
      return true;
    });
  }, [datos, filtroEstado, filtroTipo, trabajosDeAlerta]);

  // Orden en cliente sobre la ventana filtrada; `null` = el orden del
  // servidor (creado descendente). Tres estados: asc → desc → sin orden.
  const trabajosOrdenados = useMemo(() => {
    if (!orden) return trabajosFiltrados;
    const sentido = orden.dir === "asc" ? 1 : -1;
    const filas = [...trabajosFiltrados];
    if (orden.clave === "id") filas.sort((a, b) => (a.id - b.id) * sentido);
    else if (orden.clave === "creado")
      filas.sort(
        (a, b) =>
          (new Date(a.created_at ?? 0).getTime() - new Date(b.created_at ?? 0).getTime()) *
          sentido,
      );
    else if (orden.clave === "estado")
      filas.sort((a, b) => a.status.localeCompare(b.status) * sentido);
    return filas;
  }, [trabajosFiltrados, orden]);

  const alternarOrden = useCallback((clave: string) => {
    setOrden((actual) => {
      if (actual?.clave !== clave) return { clave, dir: "asc" };
      if (actual.dir === "asc") return { clave, dir: "desc" };
      return null; // tercer clic: vuelve el orden del servidor
    });
  }, []);

  const columnas: Columna<JobInfo>[] = useMemo(
    () => [
      {
        clave: "id",
        cabecera: "#",
        ancho: "4.5rem",
        numerica: true,
        ordenable: true,
        render: (trabajo) => <span className="id">{trabajo.id}</span>,
      },
      {
        clave: "tipo",
        cabecera: "tipo",
        ancho: "11rem",
        render: (trabajo) => <span className="text-ink-2">{trabajo.type}</span>,
      },
      {
        clave: "estado",
        cabecera: "estado",
        ancho: "9rem",
        ordenable: true,
        render: (trabajo) => (
          <Estado
            tono={tonoDeTrabajo(trabajo.status)}
            etiqueta={trabajo.status_label || trabajo.status}
          />
        ),
      },
      {
        clave: "intento",
        cabecera: "intento",
        ancho: "5rem",
        numerica: true,
        secundaria: true,
        render: (trabajo) => <span className="num">{trabajo.attempt ?? 1}</span>,
      },
      {
        clave: "motivo",
        cabecera: "motivo",
        ancho: "9rem",
        render: (trabajo) =>
          trabajo.error_kind_label ? (
            <span className="text-ink-2">{trabajo.error_kind_label}</span>
          ) : (
            <span className="id">—</span>
          ),
      },
      {
        clave: "detalle",
        cabecera: "detalle",
        secundaria: true,
        render: (trabajo) =>
          trabajo.error ? (
            <span className="text-ink-3" title={trabajo.error}>
              {trabajo.error.length > 90 ? `${trabajo.error.slice(0, 90)}…` : trabajo.error}
            </span>
          ) : (
            <span className="id">—</span>
          ),
      },
      {
        clave: "creado",
        cabecera: "creado",
        ancho: "6.5rem",
        numerica: true,
        ordenable: true,
        render: (trabajo) => (
          <span className="num" title={trabajo.created_at}>
            {hora(trabajo.created_at)}
          </span>
        ),
      },
    ],
    [],
  );

  if (!datos && !error) {
    return (
      <div className="space-y-3">
        <div className="ops-panel">
          <div className="ops-panel-head">
            <span className="esqueleto h-2 w-40" />
          </div>
          <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
            {Array.from({ length: 8 }).map((_, indice) => (
              <EsqueletoMetrica key={indice} />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <EsqueletoPanel lineas={8} />
          <EsqueletoPanel lineas={5} />
        </div>
        <span className="sr-only">Cargando el estado del sistema…</span>
      </div>
    );
  }

  if (!datos && error) {
    return (
      <Panel titulo="Operación · sin datos" meta="error de lectura">
        <div className="alerta-fila alerta-fila-err" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p>No se ha podido leer el estado del sistema.</p>
            <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{error}</p>
          </div>
        </div>
        <div className="mt-3">
          <button type="button" className="btn-sm" onClick={() => void cargar()}>
            <IconoRefrescar /> Reintentar
          </button>
        </div>
      </Panel>
    );
  }

  if (!datos) return null;

  const { salud, metricas, alertas, proveedores, uso, trabajos } = datos;
  const degradado = salud.checks
    ? Object.entries(salud.checks).filter(([, comprobacion]) => !comprobacion.ok)
    : [];
  const hayErrorCritico = !salud.ok || degradado.length > 0 || alertas.some((a) => a.severidad === "error");
  const clavesFallidas = Object.keys(fallos) as ClaveLectura[];
  const tonoGlobal: TonoEstado = hayErrorCritico
    ? "crit"
    : clavesFallidas.length > 0
      ? "warn"
      : "ok";
  const presupuestoUsado =
    uso.budget.daily_limit_eur > 0
      ? Math.min(1, uso.today_spent_eur / uso.budget.daily_limit_eur)
      : 0;

  const columnasTrabajo: Columna<JobInfo>[] = columnas.filter(
    (columna) => !ocultas.includes(columna.clave),
  );

  return (
    <div className="space-y-3">
      {/* --- Banda de estado ------------------------------------------------ */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1">
            <h1 className="text-sm font-semibold tracking-tight text-ink">Operación</h1>
            <Estado
              tono={tonoGlobal}
              etiqueta={hayErrorCritico ? "degradado" : clavesFallidas.length > 0 ? "lectura parcial" : "nominal"}
              variante="punto"
            />
            <span className="ops-panel-meta">
              {salud.app} v{salud.version} · {salud.env} ·{" "}
              {salud.demo_mode ? "modo demo" : "servicios de pago activos"}
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="ops-panel-meta">
              {ultimaLectura ? `lectura ${hora(ultimaLectura.toISOString())}` : "sin lectura"}
            </span>
            <button
              type="button"
              className={`filtro ${autorefresco ? "filtro-on" : ""}`}
              onClick={() => setAutorefresco((valor) => !valor)}
              title="Autorefresco cada 15 s"
            >
              auto 15 s
            </button>
            <button
              type="button"
              className="btn-sm"
              onClick={() => void cargar()}
              disabled={actualizando}
            >
              <IconoRefrescar />
              {actualizando ? "leyendo…" : "actualizar"}
            </button>
          </div>
        </div>

        {error ? (
          <div className="alerta-fila alerta-fila-warn border-l-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>Última lectura fallida; se conserva la anterior ({hora(ultimaLectura?.toISOString())}).</p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">{error}</p>
            </div>
          </div>
        ) : clavesFallidas.length > 0 ? (
          <div className="alerta-fila alerta-fila-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>
                Lectura parcial: sin {clavesFallidas.join(", ")}. Esos paneles conservan su
                última lectura buena; el resto está fresco.
              </p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">
                {clavesFallidas.map((clave) => `${clave}: ${fallos[clave]}`).join(" · ")}
              </p>
            </div>
          </div>
        ) : null}
      </section>

      {/* --- Alertas (lo primero que el operador tiene que ver) ------------ */}
      {alertas.length > 0 ? (
        <section className="ops-panel">
          <div className="ops-panel-head">
            <div className="flex items-center gap-2">
              <h2 className="ops-panel-title">Alertas</h2>
              <span className="ops-panel-meta">{alertas.length}</span>
            </div>
          </div>
          <div className="flex flex-col gap-px bg-line">
            {alertas.map((alerta) => (
              <div
                key={`${alerta.codigo}-${alerta.mensaje}`}
                className={`alerta-fila ${
                  alerta.severidad === "error" ? "alerta-fila-err" : "alerta-fila-warn"
                }`}
                role="alert"
              >
                <IconoAlerta className="mt-0.5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-ink">{alerta.mensaje}</p>
                  <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.08em] text-ink-3">
                    {alerta.codigo} · {alerta.severidad}
                  </p>
                </div>
                {alerta.trabajos && alerta.trabajos.length > 0 ? (
                  <button
                    type="button"
                    className={`filtro shrink-0 ${codigoAlerta === alerta.codigo ? "filtro-on" : ""}`}
                    onClick={() =>
                      setCodigoAlerta((actual) => (actual === alerta.codigo ? null : alerta.codigo))
                    }
                  >
                    {codigoAlerta === alerta.codigo
                      ? "quitar filtro"
                      : `ver ${alerta.trabajos.length} trabajos`}
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* --- Rejilla principal: telemetría + trabajo | contexto ------------ */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-3">
          <Panel
            titulo="Telemetría"
            meta={`ventana ${metricas.ventana_horas} h`}
            acciones={
              <>
                <span className="ops-panel-meta">
                  {metricas.jobs_total} trabajos
                </span>
              </>
            }
          >
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metrica
                etiqueta="completados"
                valor={String(metricas.jobs_terminados_ok)}
                tono="ok"
                pista={`de ${metricas.jobs_total} en la ventana`}
              />
              <Metrica
                etiqueta="fallidos"
                valor={String(metricas.jobs_fallidos)}
                tono={metricas.jobs_fallidos > 0 ? "crit" : "neutro"}
                pista={porcentaje(metricas.tasa_fallo)}
              />
              <Metrica
                etiqueta="tasa de fallo"
                valor={porcentaje(metricas.tasa_fallo)}
                tono={metricas.tasa_fallo > 0.2 ? "crit" : metricas.tasa_fallo > 0.05 ? "warn" : "ok"}
                pista={`${metricas.jobs_fallidos} de ${metricas.jobs_total}`}
              />
              <Metrica
                etiqueta="profundidad de cola"
                valor={String(metricas.profundidad_cola)}
                tono={metricas.profundidad_cola > 0 ? "warn" : "neutro"}
                pista="trabajos sin recoger"
              />
              <Metrica
                etiqueta="p95 de duración"
                valor={metricas.p95_duracion_s === null ? "—" : metricas.p95_duracion_s.toFixed(3)}
                sufijo="s"
              />
              <Metrica
                etiqueta="duración media"
                valor={metricas.duracion_media_s === null ? "—" : metricas.duracion_media_s.toFixed(3)}
                sufijo="s"
              />
              <Metrica
                etiqueta="reintentables"
                valor={String(metricas.jobs_reintentables)}
                tono={metricas.jobs_reintentables > 0 ? "warn" : "neutro"}
              />
              <Metrica
                etiqueta="trabajos"
                valor={String(metricas.jobs_total)}
                pista={`ventana de ${metricas.ventana_horas} h`}
              />
            </div>

            <div className="mt-3">
              <div className="flex items-center justify-between">
                <span className="ops-panel-title">reparto por tipo</span>
                <span className="ops-panel-meta">
                  {Object.keys(metricas.por_tipo).length} tipos
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {/* Descendente por recuento: lo más frecuente se lee primero. */}
                {Object.entries(metricas.por_tipo)
                  .sort((a, b) => b[1] - a[1])
                  .map(([tipo, numero]) => (
                  <span key={tipo} className="chip">
                    {tipo}
                    <span className="tabular-nums text-ink-2">{numero}</span>
                  </span>
                ))}
                {Object.keys(metricas.por_tipo).length === 0 ? (
                  <span className="ops-panel-meta">sin trabajos en la ventana</span>
                ) : null}
              </div>
            </div>

            {Object.keys(metricas.por_error_kind).length > 0 ? (
              <div className="mt-3">
                <span className="ops-panel-title">fallos por motivo</span>
                <div className="mt-1">
                  {Object.entries(metricas.por_error_kind).map(([motivo, numero]) => (
                    <div key={motivo} className="kv">
                      <span className="kv-clave">{motivo}</span>
                      <span className="kv-valor">{numero}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </Panel>

          <Panel
            titulo="Trabajos"
            meta={`${trabajosFiltrados.length} de ${trabajos.length}`}
            relleno="flush"
            acciones={
              <>
                {FILTROS_ESTADO.map((filtro) => (
                  <button
                    key={filtro.clave}
                    type="button"
                    className={`filtro ${filtroEstado === filtro.clave ? "filtro-on" : ""}`}
                    onClick={() => actualizarUrl({ estado: filtro.clave })}
                  >
                    {filtro.etiqueta}
                  </button>
                ))}
                <span className="mx-1 h-4 w-px bg-line" aria-hidden="true" />
                <button
                  type="button"
                  className={`filtro ${filtroTipo !== "todos" ? "filtro-on" : ""}`}
                  onClick={() =>
                    actualizarUrl({ tipo: filtroTipo === "todos" ? (tipos[0] ?? "todos") : "todos" })
                  }
                  title="Filtrar por tipo de trabajo"
                >
                  {filtroTipo === "todos" ? "tipo: todos" : filtroTipo}
                </button>
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
                {codigoAlerta ? (
                  <button
                    type="button"
                    className="filtro filtro-on"
                    onClick={() => setCodigoAlerta(null)}
                  >
                    <IconoCruce /> alerta
                  </button>
                ) : null}
              </>
            }
          >
            <TablaOps
              columnas={columnasTrabajo}
              filas={trabajosOrdenados}
              claveFila={(trabajo) => String(trabajo.id)}
              orden={orden}
              alOrdenar={alternarOrden}
              vacio={
                <Vacio
                  titulo="No hay trabajos con estos filtros"
                  pista="Quita los filtros o espera al siguiente refresco (15 s)."
                  icono={<IconoPulso />}
                />
              }
            />
          </Panel>
        </div>

        {/* --- Columna de contexto ---------------------------------------- */}
        <div className="min-w-0 space-y-3">
          <Panel titulo="Consumo de hoy" meta={uso.budget.paid_services_enabled ? "pago activo" : "pago bloqueado"}>
            <div className="grid grid-cols-3 gap-2">
              <Metrica etiqueta="llamadas" valor={String(uso.today_calls)} />
              <Metrica
                etiqueta="bloqueadas"
                valor={String(uso.today_blocked)}
                tono={uso.today_blocked > 0 ? "warn" : "neutro"}
              />
              <Metrica etiqueta="consumido" valor={uso.today_spent_eur.toFixed(4)} sufijo="€" />
            </div>
            <div className="mt-3">
              <div className="flex items-center justify-between">
                <span className="ops-panel-title">presupuesto diario</span>
                <span className="ops-panel-meta">
                  {uso.budget.daily_limit_eur.toFixed(2)} € de límite
                </span>
              </div>
              <div className="barra mt-1.5">
                <div
                  className={`barra-relleno ${
                    presupuestoUsado > 0.8 ? "barra-relleno-crit" : presupuestoUsado > 0.5 ? "barra-relleno-warn" : ""
                  }`}
                  style={{ width: `${Math.round(presupuestoUsado * 100)}%` }}
                />
              </div>
            </div>
            {Object.keys(uso.by_provider).length > 0 ? (
              <div className="mt-3">
                <span className="ops-panel-title">por proveedor</span>
                {Object.entries(uso.by_provider).map(([proveedor, llamadas]) => (
                  <div key={proveedor} className="kv">
                    <span className="kv-clave">{proveedor}</span>
                    <span className="kv-valor">{llamadas}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </Panel>

          <Panel titulo="Dependencias" meta={`${Object.keys(salud.checks ?? {}).length} comprobaciones`}>
            <div className="flex flex-col gap-px bg-line">
              {Object.entries(salud.checks ?? {}).map(([nombre, comprobacion]) => (
                <div key={nombre} className="kv bg-surface">
                  <span className="kv-clave truncate">{nombre}</span>
                  <Estado
                    tono={comprobacion.ok ? "ok" : "crit"}
                    etiqueta={comprobacion.ok ? "ok" : "falla"}
                    variante="punto"
                  />
                  <span className="kv-valor w-2/5 truncate text-ink-3" title={comprobacion.detalle}>
                    {comprobacion.detalle}
                  </span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel titulo="Proveedores" meta={`${proveedores.length}`}>
            <div className="flex flex-col gap-px bg-line">
              {proveedores.map((proveedor) => (
                <div key={proveedor.key} className="kv bg-surface">
                  <span className="kv-clave truncate" title={proveedor.note}>
                    {proveedor.name}
                  </span>
                  <Estado
                    tono={tonoDeProveedor(proveedor.configured, proveedor.state)}
                    etiqueta={etiquetaDeProveedor(proveedor.configured, proveedor.state)}
                    variante="punto"
                  />
                  <span className="kv-valor w-2/5 truncate text-ink-3" title={proveedor.note}>
                    {proveedor.note}
                  </span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel titulo="Cola" meta="últimos trabajos">
            <div className="flex items-center gap-2">
              <IconoReloj className="text-ink-3" />
              <span className="text-xs text-ink-2">
                {trabajos.length} trabajos listados · refresco automático cada 15 s
              </span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              <span className="chip">
                <IconoCheck className="text-ok" /> {metricas.jobs_terminados_ok} ok
              </span>
              <span className="chip">
                <IconoAlerta className="text-crit" /> {metricas.jobs_fallidos} fallidos
              </span>
              <span className="chip">
                <IconoPulso className="text-info" /> {metricas.profundidad_cola} en cola
              </span>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
