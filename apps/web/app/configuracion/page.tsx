"use client";

/**
 * Configuración: proveedores, límites de uso y pesos editoriales.
 *
 * No cambia ninguna llamada a la API (`providerStatus`, `usage`,
 * `getScoreWeights`, `updateBudget`, `updateScoreWeights`): lo que cambia es
 * la superficie, migrada al sistema visual.
 *
 * Decisiones:
 * - **Cero dependencias**: `Panel`, `Metrica`, `Estado`, `TablaOps`, `Vacio` y
 *   las clases propias de `globals.css`.
 * - **Rejilla asimétrica**: a la izquierda lo que se edita (límites, pesos,
 *   proveedores), a la derecha lo que se consulta (entorno y consumo).
 * - **El dato viejo no se tira**: si una lectura falla, se conserva la última
 *   y se marca como obsoleta con el código literal del error.
 * - **Cifras tabulares**: todo número va en monoespaciado (`Metrica`,
 *   `kv-valor`, `input` con `tabular-nums`).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import type { ProviderStatus, UsageInfo } from "@/lib/types";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna } from "@/components/ui/tabla";
import { EsqueletoMetrica, EsqueletoPanel, Vacio } from "@/components/ui/estados";
import { IconoAlerta, IconoCaja, IconoCheck, IconoRefrescar } from "@/components/ui/icono";
import { aplicarSkin, skinGuardado, SKINS, type Skin } from "@/lib/apariencia";

type Datos = {
  proveedores: ProviderStatus[];
  demoMode: boolean;
  uso: UsageInfo;
  pesos: Record<string, number>;
};

type ClavePeso = "impacto" | "verificacion" | "novedad" | "visual";

/** Los cuatro pesos editoriales, con su etiqueta en el panel. */
const PESOS: Array<{ clave: ClavePeso; etiqueta: string }> = [
  { clave: "impacto", etiqueta: "Impacto" },
  { clave: "verificacion", etiqueta: "Verificación" },
  { clave: "novedad", etiqueta: "Novedad" },
  { clave: "visual", etiqueta: "Potencial visual" },
];

/** Estado del proveedor → tono semántico + etiqueta legible. */
const ESTADO_PROVEEDOR: Record<string, { tono: TonoEstado; etiqueta: string }> = {
  probado: { tono: "ok", etiqueta: "Verificado" },
  implementado: { tono: "info", etiqueta: "Preparado (sin validar)" },
  sin_clave: { tono: "warn", etiqueta: "Falta clave" },
  mock: { tono: "warn", etiqueta: "Solo demo" },
  fuera_de_mvp: { tono: "idle", etiqueta: "Fuera del MVP" },
};

/** Código literal del fallo: el estado HTTP, o la marca de un error sin estado. */
function codigoDeError(fallo: unknown): string {
  if (fallo instanceof ApiError) return `HTTP ${fallo.status}`;
  return "ERROR";
}

/** Hora legible: hoy → HH:MM:SS; antes de hoy → `dd/mm HH:MM`. Una consola
 *  no puede distinguir «hace 5 s» de «ayer» con la hora sola. */
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

export default function ConfiguracionPage() {
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [codigoError, setCodigoError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [actualizando, setActualizando] = useState(false);
  const [guardando, setGuardando] = useState<"presupuesto" | "pesos" | null>(null);
  const [ultimaLectura, setUltimaLectura] = useState<Date | null>(null);

  const [paidEnabled, setPaidEnabled] = useState(false);
  const [dailyLimit, setDailyLimit] = useState("0");
  const [pesos, setPesos] = useState<Record<string, number>>({});
  const [skin, setSkin] = useState<Skin>("base");

  useEffect(() => {
    setSkin(skinGuardado());
  }, []);

  const refresh = useCallback(async () => {
    setActualizando(true);
    try {
      const [status, usageData, w] = await Promise.all([
        api.providerStatus(),
        api.usage(),
        api.getScoreWeights(),
      ]);
      setDatos({
        proveedores: status.providers,
        demoMode: status.demo_mode,
        uso: usageData,
        pesos: w,
      });
      setPaidEnabled(usageData.budget.paid_services_enabled);
      setDailyLimit(String(usageData.budget.daily_limit_eur));
      setPesos(w);
      setError(null);
      setCodigoError(null);
      setUltimaLectura(new Date());
    } catch (e) {
      setError((e as Error).message);
      setCodigoError(codigoDeError(e));
    } finally {
      setActualizando(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveBudget = async () => {
    setGuardando("presupuesto");
    setMensaje(null);
    setError(null);
    setCodigoError(null);
    try {
      await api.updateBudget({
        paid_services_enabled: paidEnabled,
        daily_limit_eur: Number(dailyLimit) || 0,
      });
      setMensaje("Presupuesto actualizado.");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
      setCodigoError(codigoDeError(e));
    } finally {
      setGuardando(null);
    }
  };

  const saveWeights = async () => {
    setGuardando("pesos");
    setMensaje(null);
    setError(null);
    setCodigoError(null);
    try {
      await api.updateScoreWeights(pesos);
      setMensaje("Puntuación actualizada.");
    } catch (e) {
      setError((e as Error).message);
      setCodigoError(codigoDeError(e));
    } finally {
      setGuardando(null);
    }
  };

  const columnasProveedor: Columna<ProviderStatus>[] = useMemo(
    () => [
      {
        clave: "nombre",
        cabecera: "proveedor",
        ancho: "12rem",
        render: (proveedor) => (
          <span className="text-ink">
            {proveedor.name}
            <span className="ml-1 text-ink-3">{proveedor.key}</span>
          </span>
        ),
      },
      {
        clave: "estado",
        cabecera: "estado",
        ancho: "13rem",
        render: (proveedor) => {
          const estado = ESTADO_PROVEEDOR[proveedor.state] ?? {
            tono: "idle" as TonoEstado,
            etiqueta: proveedor.state,
          };
          return <Estado tono={estado.tono} etiqueta={estado.etiqueta} variante="punto" />;
        },
      },
      {
        clave: "clave",
        cabecera: "clave",
        ancho: "8rem",
        render: (proveedor) => (
          <span className="num">{proveedor.configured ? "configurada" : "—"}</span>
        ),
      },
      {
        clave: "nota",
        cabecera: "nota",
        secundaria: true,
        render: (proveedor) => <span className="text-ink-3">{proveedor.note}</span>,
      },
    ],
    [],
  );

  /* --- Carga: el esqueleto tiene la forma de la vista final -------------- */
  if (!datos && !error) {
    return (
      <div className="space-y-3">
        <div className="ops-panel">
          <div className="ops-panel-head">
            <span className="esqueleto h-2 w-40" />
          </div>
          <div className="ops-panel-body grid grid-cols-3 gap-2">
            <EsqueletoMetrica />
            <EsqueletoMetrica />
            <EsqueletoMetrica />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <EsqueletoPanel lineas={6} />
          <EsqueletoPanel lineas={4} />
        </div>
        <span className="sr-only">Cargando la configuración…</span>
      </div>
    );
  }

  /* --- Error sin datos: código literal y reintento ---------------------- */
  if (!datos && error) {
    return (
      <Panel titulo="Configuración · sin datos" meta="error de lectura">
        <div className="alerta-fila alerta-fila-err" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p>No se ha podido leer la configuración.</p>
            <p className="mt-1 break-words font-mono text-[11px] text-ink-2">
              {codigoError} · {error}
            </p>
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

  if (!datos) return null;

  const { proveedores, demoMode, uso, pesos: pesosServidor } = datos;
  const presupuestoUsado =
    uso.budget.daily_limit_eur > 0
      ? Math.min(1, uso.today_spent_eur / uso.budget.daily_limit_eur)
      : 0;
  const totalPesos = PESOS.reduce((suma, peso) => suma + (pesos[peso.clave] ?? 0), 0);
  const sinPesos = Object.keys(pesosServidor).length === 0;

  return (
    <div className="space-y-3">
      {/* --- Banda de cabecera -------------------------------------------- */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
            <h1 className="text-sm font-semibold tracking-tight text-ink">Configuración</h1>
            <Estado
              tono={demoMode ? "warn" : "ok"}
              etiqueta={demoMode ? "modo demo" : "modo real"}
              variante="punto"
            />
            <span className="ops-panel-meta">
              {proveedores.length} proveedores ·{" "}
              {ultimaLectura ? `lectura ${hora(ultimaLectura.toISOString())}` : "sin lectura"}
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <button
              type="button"
              className="btn-sm"
              onClick={() => void refresh()}
              disabled={actualizando}
            >
              <IconoRefrescar />
              {actualizando ? "leyendo…" : "actualizar"}
            </button>
          </div>
        </div>

        {error ? (
          <div className="alerta-fila alerta-fila-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>Última lectura fallida; se conserva la anterior.</p>
              <p className="mt-1 break-words font-mono text-[11px] text-ink-2">
                {codigoError} · {error}
              </p>
            </div>
          </div>
        ) : null}

        {mensaje ? (
          <div className="alerta-fila" role="status">
            <IconoCheck className="mt-0.5 shrink-0 text-ok" />
            <div className="min-w-0">
              <p>{mensaje}</p>
            </div>
          </div>
        ) : null}
      </section>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        {/* --- Columna de edición ---------------------------------------- */}
        <div className="min-w-0 space-y-3">
          <Panel
            titulo="Límites de uso"
            meta={uso.budget.paid_services_enabled ? "pago activo" : "pago bloqueado"}
          >
            <div className="grid grid-cols-3 gap-2">
              <Metrica etiqueta="llamadas hoy" valor={String(uso.today_calls)} />
              <Metrica
                etiqueta="bloqueadas"
                valor={String(uso.today_blocked)}
                tono={uso.today_blocked > 0 ? "warn" : "neutro"}
              />
              <Metrica etiqueta="consumido" valor={uso.today_spent_eur.toFixed(4)} sufijo="€" />
            </div>

            <div className="mt-3">
              <div className="flex items-center justify-between gap-2">
                <span className="ops-panel-title">presupuesto diario</span>
                <span className="ops-panel-meta">
                  {uso.budget.daily_limit_eur.toFixed(2)} € de límite
                </span>
              </div>
              <div className="barra mt-1.5">
                <div
                  className={`barra-relleno ${
                    presupuestoUsado > 0.8
                      ? "barra-relleno-crit"
                      : presupuestoUsado > 0.5
                        ? "barra-relleno-warn"
                        : ""
                  }`}
                  style={{ width: `${Math.round(presupuestoUsado * 100)}%` }}
                />
              </div>
            </div>

            <div className="mt-3 space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <input
                    id="pago-activo"
                    type="checkbox"
                    className="h-4 w-4 shrink-0 accent-info"
                    checked={paidEnabled}
                    onChange={(e) => setPaidEnabled(e.target.checked)}
                  />
                  <label htmlFor="pago-activo" className="text-xs text-ink-2">
                    Servicios de pago activados
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <label htmlFor="limite-diario" className="text-xs text-ink-2">
                    Presupuesto diario (€)
                  </label>
                  <div className="w-24 shrink-0">
                    <input
                      id="limite-diario"
                      type="number"
                      min={0}
                      step="0.5"
                      className="input font-mono tabular-nums"
                      value={dailyLimit}
                      onChange={(e) => setDailyLimit(e.target.value)}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-sm-primary"
                  onClick={() => void saveBudget()}
                  disabled={guardando !== null}
                >
                  {guardando === "presupuesto" ? "guardando…" : "Guardar límites"}
                </button>
              </div>
              <p className="text-xs text-ink-3">
                Los servicios facturables empiezan siempre desactivados. Al agotarse el presupuesto, las
                llamadas de pago se detienen y puedes seguir en modo demo o manual.
              </p>
            </div>
          </Panel>

          <Panel titulo="Puntuación editorial" meta="sobre 100">
            {sinPesos ? (
              <Vacio
                titulo="Sin pesos guardados"
                pista="El servidor todavía no tiene pesos propios: fija los cuatro valores y guárdalos para que se apliquen a la puntuación de cada noticia."
                icono={<IconoCaja />}
              />
            ) : null}

            <div className="mt-2 space-y-2">
              {PESOS.map(({ clave, etiqueta }) => {
                const valor = pesos[clave] ?? 0;
                return (
                  <div key={clave} className="flex items-center gap-2">
                    <label htmlFor={`peso-${clave}`} className="w-24 shrink-0 text-xs text-ink-2">
                      {etiqueta}
                    </label>
                    <div className="w-16 shrink-0">
                      <input
                        id={`peso-${clave}`}
                        aria-label={`Peso de ${clave}`}
                        type="number"
                        min={0}
                        max={100}
                        className="input font-mono tabular-nums"
                        value={valor}
                        onChange={(e) =>
                          setPesos((actual) => ({
                            ...actual,
                            [clave]: Number(e.target.value) || 0,
                          }))
                        }
                      />
                    </div>
                    <div className="barra min-w-0 flex-1">
                      <div
                        className="barra-relleno-info"
                        style={{ width: `${Math.min(100, Math.max(0, valor))}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-3 flex items-center justify-between gap-2">
              <Estado
                tono={totalPesos === 100 ? "ok" : "warn"}
                etiqueta={`total ${totalPesos} / 100`}
                variante="punto"
              />
              <button
                type="button"
                className="btn-sm-primary"
                onClick={() => void saveWeights()}
                disabled={guardando !== null}
              >
                {guardando === "pesos" ? "guardando…" : "Guardar pesos"}
              </button>
            </div>

            <p className="mt-2 text-xs text-ink-3">
              Referencia: impacto 35 · verificación 30 · novedad 20 · potencial visual 15. Es orientativa y se
              registra el desglose por noticia; ninguna nota alta aprueba automáticamente.
            </p>
          </Panel>

          <Panel titulo="Proveedores" meta={`${proveedores.length}`} relleno="flush">
            <TablaOps
              columnas={columnasProveedor}
              filas={proveedores}
              claveFila={(proveedor) => proveedor.key}
              vacio={
                <Vacio
                  titulo="No hay proveedores declarados"
                  pista="Los proveedores se declaran en el backend: comprueba la instalación de la API y vuelve a leer la configuración."
                  icono={<IconoCaja />}
                />
              }
            />
          </Panel>
        </div>

        {/* --- Columna de contexto ---------------------------------------- */}
        <div className="min-w-0 space-y-3">
          {demoMode ? (
            <Panel titulo="Modo demo" meta="activo">
              <div className="alerta-fila alerta-fila-warn">
                <span className="badge-demo shrink-0">demo</span>
                <div className="min-w-0">
                  <p>
                    El modo demo está activado: todos los contenidos y evidencias son ficticios y los servicios de
                    pago permanecen bloqueados.
                  </p>
                  <p className="mt-0.5 text-ink-2">
                    Para usar proveedores reales, desactiva{" "}
                    <code className="font-mono text-[11px] text-ink">NEURAL_DEMO_MODE</code> y añade las claves
                    en el archivo <code className="font-mono text-[11px] text-ink">.env</code>.
                  </p>
                </div>
              </div>
            </Panel>
          ) : null}

          <Panel titulo="Apariencia" meta="skin de la consola">
            <div className="flex flex-wrap gap-1.5">
              {SKINS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`filtro ${skin === item.id ? "filtro-on" : ""}`}
                  aria-pressed={skin === item.id}
                  onClick={() => {
                    aplicarSkin(item.id);
                    setSkin(item.id);
                  }}
                >
                  {item.nombre}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-3">
              {SKINS.find((item) => item.id === skin)?.descripcion} El skin cambia sólo los
              tokens (superficies, acentos, radios y tipografía): los datos, la rejilla y los
              controles no se mueven. El conmutador claro/oscuro de la cabecera sigue
              funcionando dentro de cada skin.
            </p>
          </Panel>

          <Panel titulo="Entorno" meta={ultimaLectura ? hora(ultimaLectura.toISOString()) : "sin lectura"}>
            <div className="flex flex-col gap-px bg-line">
              <div className="kv bg-surface">
                <span className="kv-clave">modo</span>
                <Estado
                  tono={demoMode ? "warn" : "ok"}
                  etiqueta={demoMode ? "demo" : "real"}
                  variante="punto"
                />
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">servicios de pago</span>
                <Estado
                  tono={paidEnabled ? "warn" : "idle"}
                  etiqueta={paidEnabled ? "activos" : "bloqueados"}
                  variante="punto"
                />
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">límite diario</span>
                <span className="kv-valor">{uso.budget.daily_limit_eur.toFixed(2)} €</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">llamadas hoy</span>
                <span className="kv-valor">{uso.today_calls}</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">bloqueadas hoy</span>
                <span className="kv-valor">{uso.today_blocked}</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">proveedores</span>
                <span className="kv-valor">{proveedores.length}</span>
              </div>
            </div>
          </Panel>

          <Panel titulo="Consumo por proveedor" meta="hoy">
            {Object.keys(uso.by_provider).length > 0 ? (
              <div className="flex flex-col gap-px bg-line">
                {Object.entries(uso.by_provider).map(([proveedor, llamadas]) => (
                  <div key={proveedor} className="kv bg-surface">
                    <span className="kv-clave truncate">{proveedor}</span>
                    <span className="kv-valor">{llamadas}</span>
                  </div>
                ))}
              </div>
            ) : (
              <Vacio
                titulo="Sin llamadas registradas hoy"
                pista="El consumo aparece en cuanto un proveedor real recibe una llamada; en modo demo no se llama a ningún servicio externo."
                icono={<IconoCaja />}
              />
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
