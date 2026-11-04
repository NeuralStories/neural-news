"use client";

/**
 * Acceso: la única superficie pública del producto.
 *
 * El comportamiento no cambia (demo → `/fuentes`); lo que cambia es la piel:
 * la página deja de ser un cartel centrado y pasa a usar el sistema visual
 * (tokens semánticos, `Panel`, `Estado`, `Vacio` y las clases propias).
 *
 * Decisiones:
 * - **Cero dependencias**: todo sale de `components/ui/` y de `globals.css`.
 * - **Rejilla asimétrica**: a la izquierda lo que se hace (entrar), a la
 *   derecha lo que se consulta (recorrido y alcance del modo demo).
 * - **Los tres estados del bloque de acceso**: vacío (no hay sesión), carga
 *   (esqueleto con la forma del botón) y error (código literal + reintento).
 * - **Sin spinners**: el esqueleto tiene la forma del contenido final.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/http";
import { Estado } from "@/components/ui/estado";
import { Panel } from "@/components/ui/panel";
import { Vacio } from "@/components/ui/estados";
import { IconoAlerta, IconoCheck, IconoFlecha } from "@/components/ui/icono";

/** El recorrido que se abre al entrar: el orden real de las vistas. */
const RECORRIDO = [
  { clave: "fuentes", texto: "Importa vídeos, RSS y transcripciones con su evidencia." },
  { clave: "noticias", texto: "Agrupa las fuentes en noticias y puntúa su solidez." },
  { clave: "estudio", texto: "Redacta el guion, monta el storyboard y revisa las afirmaciones." },
  { clave: "lotes", texto: "Agrupa las noticias aprobadas y exporta el paquete." },
];

/** Código literal del fallo: el estado HTTP, o la marca de un error sin estado. */
function codigoDeError(fallo: unknown): string {
  if (fallo instanceof ApiError) return `HTTP ${fallo.status}`;
  return "ERROR";
}

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [codigoError, setCodigoError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const enterDemo = async () => {
    setBusy(true);
    setError(null);
    setCodigoError(null);
    try {
      await api.demoLogin();
      router.replace("/fuentes");
    } catch (e) {
      setError((e as Error).message);
      setCodigoError(codigoDeError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-3">
      {/* --- Banda de identidad ------------------------------------------- */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
            <h1 className="text-sm font-semibold tracking-tight text-ink">
              neural<span className="text-info">.news</span>
            </h1>
            <Estado tono="idle" etiqueta="sin sesión" variante="punto" />
          </div>
          <span className="ops-panel-meta">acceso · modo demo</span>
        </div>
        <div className="ops-panel-body">
          <p className="text-sm text-ink-2">
            Investigación y producción editorial sobre inteligencia artificial.
          </p>
          <p className="mt-1 text-xs text-ink-3">
            Pipeline de fuentes a paquete: investigación con evidencia, guion
            revisado por una persona y aprobación humana antes de exportar.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {/* --- Acceso: lo que se hace ------------------------------------- */}
        <Panel titulo="Acceso" meta="modo demo">
          {busy ? (
            <div aria-hidden="true" className="space-y-2">
              <span className="esqueleto block h-9 w-full" />
              <span className="esqueleto block h-3 w-3/4" />
              <span className="esqueleto block h-3 w-1/2" />
            </div>
          ) : error ? (
            <div className="space-y-3">
              <div className="alerta-fila alerta-fila-err" role="alert">
                <IconoAlerta className="mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p>No se ha podido abrir la sesión de demo.</p>
                  <p className="mt-1 break-words font-mono text-[11px] text-ink-2">
                    {codigoError} · {error}
                  </p>
                </div>
              </div>
              <button type="button" className="btn-sm" onClick={() => void enterDemo()}>
                Reintentar
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <Vacio
                titulo="No hay sesión abierta"
                pista="Entra en modo demo para recorrer el flujo completo: sin claves, sin llamadas a servicios externos y con evidencia ficticia."
                icono={<IconoFlecha />}
              />
              <button type="button" className="btn-primary w-full" onClick={() => void enterDemo()}>
                Entrar en modo demo
              </button>
            </div>
          )}
          <span className="sr-only" role="status">
            {busy ? "Entrando en modo demo…" : ""}
          </span>
        </Panel>

        {/* --- Contexto: lo que se consulta ------------------------------- */}
        <div className="min-w-0 space-y-3">
          <Panel titulo="Recorrido" meta={`${RECORRIDO.length} pasos`}>
            <ol className="space-y-1.5">
              {RECORRIDO.map((paso, indice) => (
                <li key={paso.clave} className="flex items-start gap-2">
                  <span className="font-mono text-[11px] tabular-nums text-ink-3">
                    {String(indice + 1).padStart(2, "0")}
                  </span>
                  <span className="text-xs text-ink-2">
                    <span className="text-ink">{paso.clave}</span> · {paso.texto}
                  </span>
                </li>
              ))}
            </ol>
          </Panel>

          <Panel titulo="Alcance del demo" meta="sin claves">
            <div className="alerta-fila alerta-fila-warn">
              <IconoAlerta className="mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p>El modo demo usa contenidos y evidencia ficticios.</p>
                <p className="mt-0.5 text-ink-2">
                  Nada de lo generado en demo debe publicarse como real.
                </p>
              </div>
            </div>
            <div className="mt-2 flex flex-col gap-px bg-line">
              <div className="kv bg-surface">
                <span className="kv-clave">modo</span>
                <span className="kv-valor">demo</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">claves de proveedor</span>
                <span className="kv-valor">no requeridas</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">servicios externos</span>
                <span className="kv-valor">no se llaman</span>
              </div>
              <div className="kv bg-surface">
                <span className="kv-clave">publicable</span>
                <span className="kv-valor">
                  <span className="text-warn">no</span>
                </span>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs text-ink-3">
              <IconoCheck className="text-ok" />
              <span>Sin sesión: la navegación privada empieza al entrar.</span>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
