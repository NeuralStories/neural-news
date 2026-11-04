"use client";

/**
 * Detalle de una noticia: estado, afirmaciones, evidencia, guion y storyboard.
 *
 * Vista migrada al sistema visual (tokens semánticos + componentes propios).
 * Decisiones:
 * - **Rejilla asimétrica**: a la izquierda lo que se edita (guion,
 *   afirmaciones, evidencias); a la derecha lo que se consulta (resumen,
 *   fuentes, preparación visual).
 * - **Cifras tabulares**: palabras, duración, versiones y confidencias van en
 *   monoespaciado con cifras tabulares (`.num` / `.metrica-valor`).
 * - **Carga / vacío / error** con la forma real del contenido: esqueleto
 *   (nunca un spinner), vacío con pista operativa y error con el código
 *   literal y un reintento.
 * - **El dato viejo no se tira**: si una acción falla, la lectura anterior
 *   sigue en pantalla marcada como obsoleta.
 * - Cero dependencias nuevas: sólo Tailwind y `components/ui/`.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ETIQUETA_TIPO_AFIRMACION, ETIQUETA_VERIFICACION } from "@/lib/estados";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { ClaimItem, EvidenceItem, StoryDetail, Storyboard } from "@/lib/types";
import { Estado, type TonoEstado } from "@/components/ui/estado";
import { Metrica } from "@/components/ui/metrica";
import { Panel } from "@/components/ui/panel";
import { TablaOps, type Columna } from "@/components/ui/tabla";
import { EsqueletoMetrica, EsqueletoPanel, Vacio } from "@/components/ui/estados";
import { IconoAlerta, IconoCheck, IconoFlecha, IconoRefrescar } from "@/components/ui/icono";

/**
 * Tono semántico del estado de la noticia y de cada estado de verificación.
 * `ok` = respaldado/aprobado, `warn` = sin verificar, `crit` = contradicho,
 * `idle` = no verificable o en espera, `info` = en curso.
 */
const TONO_POR_ESTADO: Record<string, TonoEstado> = {
  CANDIDATE: "idle",
  RESEARCHING: "info",
  REVIEW_REQUIRED: "warn",
  SCRIPT_DRAFT: "info",
  APPROVED: "ok",
  REJECTED: "idle",
};

const TONO_POR_VERIFICACION: Record<string, TonoEstado> = {
  UNVERIFIED: "warn",
  SUPPORTED: "ok",
  CONTRADICTED: "crit",
  NOT_VERIFIABLE: "idle",
};

/** Columnas ocultables de la tabla de afirmaciones. */
const COLUMNAS_AFIRMACION = [{ clave: "notas", etiqueta: "notas" }] as const;

/** Columnas ocultables de la tabla de evidencias. */
const COLUMNAS_EVIDENCIA = [
  { clave: "fragmento", etiqueta: "fragmento" },
  { clave: "enlace", etiqueta: "enlace" },
] as const;

/** Error de API con su código literal (HTTP 4xx/5xx) para poder diagnosticarlo. */
function codigoDeError(fallo: unknown): string {
  const error = fallo as Error & { status?: number };
  const codigo = typeof error.status === "number" ? `HTTP ${error.status}` : "sin código";
  return `${codigo} · ${error.message}`;
}

export default function StoryDetailPage() {
  const params = useParams<{ id: string }>();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [wordsPerMinute, setWordsPerMinute] = useState(150);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [ocultasAfirmacion, setOcultasAfirmacion] = useState<string[]>([]);
  const [ocultasEvidencia, setOcultasEvidencia] = useState<string[]>([]);
  // Mientras se guarda una versión, aprobar o volver a guardar actuaría sobre
  // una versión que el servidor puede haber descartado: los botones se bloquean.
  const [saving, setSaving] = useState(false);
  const { waiting, error: errorTrabajo, poll } = useJobPolling();

  const refresh = useCallback(async () => {
    try {
      const d = await api.getStory(Number(params.id));
      setStory(d);
      const latest = d.script_versions[d.script_versions.length - 1];
      setContent(latest?.content ?? "");
      setSelectedVersion(latest?.version ?? null);
      setError(null);
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  }, [params.id]);

  useEffect(() => {
    void refresh();
    const stored = Number(localStorage.getItem("nn-words-per-minute") || 150);
    if (stored > 0) setWordsPerMinute(stored);
  }, [refresh]);

  const latest = story?.script_versions[story.script_versions.length - 1] ?? null;
  const wordCount = useMemo(() => content.split(/\s+/).filter(Boolean).length, [content]);
  const estimatedSeconds = Math.max(0, Math.round((wordCount / wordsPerMinute) * 60));

  const totales = useMemo(() => {
    const afirmaciones = story?.claims ?? [];
    const evidencias = afirmaciones.flatMap((c) => c.evidence);
    const confirmadas = afirmaciones.filter((c) => c.verification_status === "SUPPORTED").length;
    return { afirmaciones, evidencias, confirmadas };
  }, [story]);

  const columnasAfirmacion: Columna<ClaimItem>[] = [
    {
      clave: "afirmacion",
      cabecera: "afirmación",
      // Ancho mínimo de la columna larga (ver `docs/DISENO.md`).
      ancho: "26rem",
      render: (claim) => <span className="text-ink">{claim.statement}</span>,
    },
    {
      clave: "estado",
      cabecera: "estado",
      ancho: "10rem",
      render: (claim) => (
        <Estado
          tono={TONO_POR_VERIFICACION[claim.verification_status] ?? "idle"}
          etiqueta={
            ETIQUETA_VERIFICACION[claim.verification_status] ?? claim.verification_status
          }
          variante="punto"
        />
      ),
    },
    {
      clave: "evidencias",
      cabecera: "evid.",
      ancho: "4.5rem",
      numerica: true,
      render: (claim) => <span className="num">{claim.evidence.length}</span>,
    },
    {
      clave: "notas",
      cabecera: "notas",
      secundaria: true,
      render: (claim) =>
        claim.verification_notes ? (
          <span className="text-ink-3">{claim.verification_notes}</span>
        ) : (
          <span className="id">—</span>
        ),
    },
  ];

  const columnasEvidencia: Columna<EvidenceItem>[] = [
    {
      clave: "tipo",
      cabecera: "tipo",
      ancho: "9rem",
      render: (ev) => (
        <span className="flex flex-wrap items-center gap-1">
          <span className="badge-info">{ETIQUETA_TIPO_AFIRMACION[ev.kind] || ev.kind}</span>
          {ev.demo ? <span className="badge-demo">DEMO</span> : null}
        </span>
      ),
    },
    {
      clave: "publicador",
      cabecera: "publicador",
      ancho: "10rem",
      render: (ev) =>
        ev.publisher ? (
          <span className="text-ink-2">{ev.publisher}</span>
        ) : (
          <span className="id">—</span>
        ),
    },
    {
      clave: "confianza",
      cabecera: "confianza",
      ancho: "5.5rem",
      numerica: true,
      render: (ev) => <span className="num">{ev.confidence}</span>,
    },
    {
      clave: "publicado",
      cabecera: "publicado",
      ancho: "9.5rem",
      render: (ev) => (
        <span className="num" title={`Recuperado ${fmtDate(ev.retrieved_at)}`}>
          {ev.published_at ? fmtDate(ev.published_at) : "—"}
        </span>
      ),
    },
    {
      clave: "fragmento",
      cabecera: "fragmento",
      ancho: "22rem",
      secundaria: true,
      render: (ev) =>
        ev.excerpt_or_paraphrase ? (
          <span className="text-ink-2">{ev.excerpt_or_paraphrase}</span>
        ) : (
          <span className="id">—</span>
        ),
    },
    {
      clave: "enlace",
      cabecera: "enlace",
      ancho: "12rem",
      secundaria: true,
      render: (ev) =>
        ev.url ? (
          <a
            className="block truncate text-info hover:underline"
            href={ev.url}
            target="_blank"
            rel="noreferrer noopener"
            title={ev.url}
          >
            {ev.url}
          </a>
        ) : (
          <span className="id">—</span>
        ),
    },
  ];

  const run = async (kind: "research" | "draft") => {
    try {
      const res = kind === "research" ? await api.research(story!.id) : await api.draft(story!.id);
      await poll(res.job_id, refresh);
      await refresh();
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const saveEdit = async () => {
    if (!latest || saving) return;
    setSaving(true);
    try {
      const res = await api.saveScript(story!.id, content, latest.version);
      // El estado se actualiza **antes** de avisar: si el aviso saliera antes,
      // quien pulse «Aprobar esta versión» podría aprobar la versión anterior
      // (la API exige la más reciente) y el guardado parecería un fallo.
      await refresh();
      setNotice(
        `Guardado como versión ${res.script_version.version}. Si estaba aprobada, la aprobación queda anulada.`,
      );
    } catch (fallo) {
      const err = fallo as Error & { status?: number; detail?: { current_version?: number } };
      if (err.status === 409) {
        setError(
          `${err.message} (la versión actual del servidor es la ${String(err.detail?.current_version ?? "?")})`,
        );
      } else {
        setError(codigoDeError(fallo));
      }
    } finally {
      setSaving(false);
    }
  };

  const approve = async () => {
    if (!latest || saving) return;
    try {
      await api.approve(story!.id, latest.id);
      setNotice("Guion aprobado. Si editas el texto después, tendrás que aprobar la nueva versión.");
      await refresh();
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const reject = async () => {
    try {
      await api.reject(story!.id, rejectReason);
      setRejectOpen(false);
      await refresh();
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const loadStoryboard = async () => {
    try {
      setStoryboard(await api.getStoryboard(story!.id));
    } catch (fallo) {
      setError(codigoDeError(fallo));
    }
  };

  const copyPrompt = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setNotice("Prompt copiado al portapapeles");
    } catch {
      setError("No se ha podido copiar; selecciona el texto del prompt manualmente");
    }
  };

  // --- Estados de página ----------------------------------------------------
  if (!story && error) {
    return (
      <Panel titulo="Noticia · sin datos" meta="error de lectura">
        <div className="alerta-fila alerta-fila-err" role="alert">
          <IconoAlerta className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p>No se ha podido leer la noticia #{params.id}.</p>
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

  if (!story) {
    return (
      <div className="space-y-3">
        <section className="ops-panel">
          <div className="ops-panel-head">
            <span className="esqueleto h-2 w-56" />
          </div>
          <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, indice) => (
              <EsqueletoMetrica key={indice} />
            ))}
          </div>
        </section>
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <EsqueletoPanel lineas={10} />
          <EsqueletoPanel lineas={6} />
        </div>
        <span className="sr-only">Cargando la noticia…</span>
      </div>
    );
  }

  const approvedActive = story.active_approval !== null && !story.pending_approval_flag;
  const sinGuion = story.script_versions.length === 0;

  return (
    <div className="space-y-3">
      {/* --- Banda de cabecera ------------------------------------------------ */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-1">
            <h1 className="min-w-0 truncate text-sm font-semibold tracking-tight text-ink">
              {story.title}
            </h1>
            <Estado
              tono={TONO_POR_ESTADO[story.status] ?? "idle"}
              etiqueta={story.status_label}
              variante="punto"
            />
            <span className="ops-panel-meta">
              #{story.id} · {fmtDate(story.original_event_date)}
            </span>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-1.5">
            <button type="button" className="btn-sm" onClick={() => void run("research")}>
              Investigar
            </button>
            <button type="button" className="btn-sm" onClick={() => void run("draft")}>
              Borrador de guion
            </button>
            {story.status !== "REJECTED" ? (
              <button
                type="button"
                className="btn-sm"
                onClick={() => setRejectOpen((valor) => !valor)}
              >
                Descartar
              </button>
            ) : null}
          </div>
        </div>

        <div className="ops-panel-body flex flex-wrap items-center gap-1.5">
          {story.is_opinion ? <span className="badge-warn">Opinión (no verificable)</span> : null}
          {story.editorial_score !== null ? (
            <span className="badge-neutral">puntuación {story.editorial_score}/100</span>
          ) : null}
          <span className="badge-neutral">
            {totales.afirmaciones.length} afirmaciones
          </span>
          <span className="badge-neutral">{totales.evidencias.length} evidencias</span>
          <span className="ops-panel-meta">
            fecha del acontecimiento: {fmtDate(story.original_event_date)}
          </span>
        </div>

        {error ? (
          <div className="alerta-fila alerta-fila-warn border-l-warn" role="alert">
            <IconoAlerta className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p>La última operación ha fallado; se conserva la lectura anterior.</p>
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

        {notice ? (
          <div className="alerta-fila" role="status">
            <IconoCheck className="mt-0.5 shrink-0 text-ok" />
            <p className="text-ink-2">{notice}</p>
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

      {/* --- Telemetría -------------------------------------------------------- */}
      <section className="ops-panel">
        <div className="ops-panel-head">
          <h2 className="ops-panel-title">Telemetría del guion</h2>
        </div>
        <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          <Metrica etiqueta="palabras" valor={String(wordCount)} />
          <Metrica
            etiqueta="duración estimada"
            valor={String(estimatedSeconds)}
            sufijo="s"
            pista={`a ${wordsPerMinute} palabras/min`}
          />
          <Metrica etiqueta="versiones" valor={String(story.script_versions.length)} />
          <Metrica
            etiqueta="afirmaciones"
            valor={String(totales.afirmaciones.length)}
            pista={`${totales.confirmadas} confirmadas`}
          />
          <Metrica etiqueta="evidencias" valor={String(totales.evidencias.length)} />
          <Metrica
            etiqueta="aprobación"
            valor={approvedActive ? "activa" : "ninguna"}
            tono={approvedActive ? "ok" : "neutro"}
            pista={approvedActive ? fmtDate(story.active_approval?.approved_at) : "ninguna versión aprobada"}
          />
        </div>
      </section>

      {rejectOpen ? (
        <div className="card-compact">
          <p className="text-sm text-ink-2">
            Motivo del descarte (se registra en la auditoría):
          </p>
          <div className="mt-2">
            <input
              className="input"
              aria-label="Motivo del descarte"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-sm" onClick={() => setRejectOpen(false)}>
              Cancelar
            </button>
            <button type="button" className="btn-danger" onClick={() => void reject()}>
              Confirmar descarte
            </button>
          </div>
        </div>
      ) : null}

      {/* --- Rejilla principal: edición | contexto ---------------------------- */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="min-w-0 space-y-3">
          {/* --- Guion --------------------------------------------------------- */}
          <Panel
            titulo="Guion"
            meta={sinGuion ? "sin versiones" : `v${selectedVersion ?? "—"} seleccionada`}
            acciones={
              <span className="ops-panel-meta">
                {wordCount} palabras · ≈{estimatedSeconds} s
              </span>
            }
          >
            {sinGuion ? (
              <Vacio
                titulo="Sin versiones todavía"
                pista="Pulsa «Borrador de guion» para generar la primera versión; después podrás editarla y aprobarla."
                icono={<IconoFlecha />}
              />
            ) : (
              <>
                <div className="flex flex-wrap gap-1">
                  {story.script_versions.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => {
                        setSelectedVersion(v.version);
                        setContent(v.content);
                      }}
                      className={`filtro ${selectedVersion === v.version ? "filtro-on" : ""}`}
                      aria-label={`Versión ${v.version}, ${v.author_type === "AI" ? "automática" : "humana"}`}
                    >
                      v{v.version} · {v.author_type === "AI" ? "auto" : "humana"}
                      {story.active_approval?.script_version_id === v.id ? " · aprobada" : ""}
                    </button>
                  ))}
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  {approvedActive ? (
                    <span className="badge-ok">
                      Aprobada ({fmtDate(story.active_approval?.approved_at)}) — cualquier edición
                      anulará la aprobación
                    </span>
                  ) : null}
                  {latest && story.active_approval && story.active_approval.script_version_id !== latest.id ? (
                    <span className="badge-warn">
                      La aprobación de una versión anterior quedó anulada al editarse el guion
                    </span>
                  ) : null}
                </div>

                <div className="mt-3">
                  <label className="sr-only" htmlFor="editor-guion">
                    Editor de guion
                  </label>
                  <textarea
                    id="editor-guion"
                    className="input min-h-80 font-mono text-sm leading-relaxed"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                  />
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <label className="text-xs text-ink-3" htmlFor="wpm">
                    Velocidad de locución
                  </label>
                  <input
                    id="wpm"
                    type="number"
                    min={80}
                    max={220}
                    className="input w-20 px-2 py-1 font-mono tabular-nums"
                    value={wordsPerMinute}
                    onChange={(e) => {
                      const v = Number(e.target.value) || 150;
                      setWordsPerMinute(v);
                      localStorage.setItem("nn-words-per-minute", String(v));
                    }}
                  />
                  <span className="font-mono text-[11px] tabular-nums text-ink-3">
                    {wordCount} palabras · ≈{estimatedSeconds} s
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => void saveEdit()}
                    disabled={!latest || content === latest.content || saving}
                  >
                    {saving ? "Guardando…" : "Guardar borrador"}
                  </button>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => void approve()}
                    disabled={!latest || approvedActive || saving}
                  >
                    Aprobar esta versión
                  </button>
                  <Link href="/lotes" className="btn">
                    Ir a lotes
                  </Link>
                </div>
              </>
            )}
          </Panel>

          {/* --- Afirmaciones ------------------------------------------------- */}
          <Panel
            titulo="Afirmaciones"
            meta={`${totales.afirmaciones.length}`}
            relleno="flush"
            acciones={
              <>
                {COLUMNAS_AFIRMACION.map((columna) => (
                  <button
                    key={columna.clave}
                    type="button"
                    className={`filtro ${!ocultasAfirmacion.includes(columna.clave) ? "filtro-on" : ""}`}
                    onClick={() =>
                      setOcultasAfirmacion((actual) =>
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
              columnas={columnasAfirmacion}
              filas={totales.afirmaciones}
              claveFila={(claim) => String(claim.id)}
              ocultas={ocultasAfirmacion}
              vacio={
                <Vacio
                  titulo="Sin afirmaciones registradas todavía"
                  pista="Lanza «Investigar» para extraer las afirmaciones verificables de esta noticia."
                />
              }
            />
          </Panel>

          {/* --- Evidencias ---------------------------------------------------- */}
          <Panel
            titulo="Evidencias"
            meta={`${totales.evidencias.length}`}
            relleno="flush"
            acciones={
              <>
                {COLUMNAS_EVIDENCIA.map((columna) => (
                  <button
                    key={columna.clave}
                    type="button"
                    className={`filtro ${!ocultasEvidencia.includes(columna.clave) ? "filtro-on" : ""}`}
                    onClick={() =>
                      setOcultasEvidencia((actual) =>
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
              columnas={columnasEvidencia}
              filas={totales.evidencias}
              claveFila={(ev) => String(ev.id)}
              ocultas={ocultasEvidencia}
              vacio={
                <Vacio
                  titulo="Sin evidencias"
                  pista="Sin evidencia no se marca nada como confirmado: lanza «Investigar» para buscar respaldo."
                  icono={<IconoAlerta />}
                />
              }
            />
          </Panel>
        </div>

        {/* --- Columna de contexto ---------------------------------------------- */}
        <div className="min-w-0 space-y-3">
          {story.summary ? (
            <Panel titulo="Resumen">
              <p className="text-sm text-ink-2">{story.summary}</p>
            </Panel>
          ) : null}

          <Panel titulo="Fuentes de la noticia" meta={`${story.sources.length}`}>
            {story.sources.length === 0 ? (
              <Vacio
                titulo="Sin fuentes registradas"
                pista="Las fuentes llegan al procesar los medios: revisa «Fuentes» para registrar una."
              />
            ) : (
              <ul className="flex flex-col gap-1.5">
                {story.sources.map((s) => (
                  <li key={s.source_id} className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="chip capitalize">{s.provider.replace("_", " ")}</span>
                    {s.canonical_url ? (
                      <a
                        href={s.canonical_url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-info hover:underline"
                      >
                        {s.title || s.canonical_url}
                      </a>
                    ) : (
                      <span className="text-ink-2">{s.title}</span>
                    )}
                    <span className="font-mono text-[11px] tabular-nums text-ink-3">
                      ({s.relevance})
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel
            titulo="Preparación visual (storyboard)"
            meta={storyboard ? `v${storyboard.script_version}` : "sin generar"}
            acciones={
              <button
                type="button"
                className="btn-sm"
                onClick={() => void loadStoryboard()}
                disabled={!latest}
              >
                {storyboard ? "Actualizar" : "Preparar escenas"}
              </button>
            }
          >
            {!storyboard ? (
              <Vacio
                titulo="Storyboard sin generar"
                pista="Genera el storyboard del guion vigente: escenas, duración orientativa, rótulos y un prompt de imagen preliminar por escena. No se genera ninguna imagen ni vídeo."
                icono={<IconoFlecha />}
              />
            ) : (
              <>
                <p className="font-mono text-[11px] tabular-nums text-ink-3">
                  guion v{storyboard.script_version} ·{" "}
                  {storyboard.approved ? "aprobado" : "sin aprobar"} · {storyboard.note}
                </p>
                <ol className="mt-2 flex flex-col gap-2">
                  {storyboard.scenes.map((scene, index) => (
                    <li key={index} className="card-quiet">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="badge-info">Escena {index + 1}</span>
                        <span className="badge-neutral">
                          ≈<span className="font-mono tabular-nums">{scene.seconds}</span> s
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-ink">{scene.message}</p>
                      <p className="mt-1 text-xs text-ink-2">Visual: {scene.visual}</p>
                      {scene.overlay_text ? (
                        <p className="mt-1 text-xs text-ink-2">Rótulo: {scene.overlay_text}</p>
                      ) : null}
                      {scene.data_source ? (
                        <p className="mt-1 font-mono text-[11px] tabular-nums text-ink-3">
                          Origen del dato: {scene.data_source}
                        </p>
                      ) : null}
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs text-info">Prompt de imagen</summary>
                        <pre className="inset mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-ink-2">
                          {scene.image_prompt}
                        </pre>
                        <button
                          type="button"
                          className="btn-sm mt-1"
                          onClick={() => void copyPrompt(scene.image_prompt)}
                        >
                          Copiar prompt
                        </button>
                      </details>
                    </li>
                  ))}
                </ol>
              </>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
