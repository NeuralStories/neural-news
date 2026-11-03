"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { StoryDetail, Storyboard } from "@/lib/types";
import { DecisionHeader, ReadinessChecklist } from "@/components/editorial-decision";
import { readinessSteps } from "@/lib/editorialState";

const STATUS_BADGE: Record<string, string> = {
  CANDIDATE: "badge-neutral",
  RESEARCHING: "badge-info",
  REVIEW_REQUIRED: "badge-warn",
  SCRIPT_DRAFT: "badge-info",
  APPROVED: "badge-ok",
  REJECTED: "badge-neutral",
};

const VERIF_BADGE: Record<string, { cls: string; label: string }> = {
  UNVERIFIED: { cls: "badge-warn", label: "Sin verificar" },
  SUPPORTED: { cls: "badge-ok", label: "Confirmada" },
  CONTRADICTED: { cls: "badge-err", label: "Contradicha" },
  NOT_VERIFIABLE: { cls: "badge-neutral", label: "No verificable (opinión)" },
};

const KIND_LABEL: Record<string, string> = {
  PRIMARY: "Fuente primaria",
  CORROBORATION: "Corroboración",
  CONTRADICTING: "Contradicción",
  REFERENCE: "Referencia",
};

export default function StoryDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [wordsPerMinute, setWordsPerMinute] = useState(150);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const { waiting, poll } = useJobPolling();

  // Si el editor tiene texto sin guardar, una recarga del servidor NO lo pisa:
  // la edición local del editor tiene prioridad (nunca se pierde trabajo).
  const dirtyRef = useRef(false);
  // Versión vigente conocida: evita aprobar una versión anterior si el refresco
  // del servidor aún no ha llegado (carrera entre guardar y aprobar).
  // `version` es el número (lo espera expected_version) e `id` la fila (la que se aprueba).
  const latestVersionRef = useRef<number | null>(null);
  const latestVersionIdRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const d = await api.getStory(Number(params.id));
      setStory(d);
      const latest = d.script_versions[d.script_versions.length - 1];
      latestVersionIdRef.current = latest?.id ?? null;
      latestVersionRef.current = latest?.version ?? null;
      if (!dirtyRef.current) {
        setContent(latest?.content ?? "");
        setSelectedVersion(latest?.version ?? null);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [params.id]);

  useEffect(() => {
    refresh();
    const stored = Number(localStorage.getItem("nn-words-per-minute") || 150);
    if (stored > 0) setWordsPerMinute(stored);
  }, [refresh]);

  const latest = story?.script_versions[story.script_versions.length - 1] ?? null;
  const wordCount = useMemo(() => content.split(/\s+/).filter(Boolean).length, [content]);
  const estimatedSeconds = Math.max(0, Math.round((wordCount / wordsPerMinute) * 60));

  const run = async (kind: "research" | "draft") => {
    try {
      const res = kind === "research" ? await api.research(story!.id) : await api.draft(story!.id);
      await poll(res.job_id, refresh);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const saveEdit = async () => {
    // `expected_version` es el NÚMERO de versión, no el id de la fila.
    const baseVersion = latestVersionRef.current ?? latest?.version;
    if (!baseVersion) return;
    try {
      let res;
      try {
        res = await api.saveScript(story!.id, content, baseVersion);
      } catch (e) {
        const err = e as Error & { status?: number };
        // 409: otra versión se guardó mientras se escribía. Se reintenta con la
        // versión vigente del servidor: el texto del usuario no se pierde.
        if (err.status === 409) {
          await refresh();
          const retryVersion = latestVersionRef.current;
          if (retryVersion && retryVersion !== baseVersion) {
            res = await api.saveScript(story!.id, content, retryVersion);
          } else {
            throw err;
          }
        } else {
          throw err;
        }
      }
      dirtyRef.current = false;
      latestVersionIdRef.current = res.script_version.id;
      latestVersionRef.current = res.script_version.version;
      setNotice(`Guardado como versión ${res.script_version.version}. Si estaba aprobada, la aprobación queda anulada.`);
      await refresh();
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 409) {
        const current = (err as unknown as { detail?: { current_version?: number } }).detail?.current_version;
        setError(`${err.message} La versión actual del servidor es la ${current ?? "?"}; vuelve a guardar tu texto para crear una versión nueva.`);
      } else {
        setError(err.message);
      }
    }
  };

  const approve = async () => {
    const versionId = latestVersionIdRef.current ?? latest?.id;
    if (!versionId) return;
    try {
      await api.approve(story!.id, versionId);
      setNotice("Guion aprobado. Si editas el texto después, tendrás que aprobar la nueva versión.");
      await refresh();
    } catch (e) {
      const err = e as Error & { status?: number };
      // Carrera de versión: si otra acción ha creado una versión más reciente,
      // se reintenta con la que indique el servidor (nunca se pierde la aprobación).
      if (err.status === 400) {
        await refresh();
        const retryId = latestVersionIdRef.current;
        if (retryId && retryId !== versionId) {
          try {
            await api.approve(story!.id, retryId);
            setNotice(
              "Guion aprobado. Si editas el texto después, tendrás que aprobar la nueva versión."
            );
            await refresh();
            return;
          } catch (e2) {
            setError((e2 as Error).message);
            return;
          }
        }
      }
      setError(err.message);
    }
  };

  const reject = async () => {
    try {
      await api.reject(story!.id, rejectReason);
      setRejectOpen(false);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const loadStoryboard = async () => {
    try {
      setStoryboard(await api.getStoryboard(story!.id));
    } catch (e) {
      setError((e as Error).message);
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

  /** Descarga el traspaso production_handoff.v1 (o explica qué falta para emitirlo). */
  const downloadHandoff = async () => {
    setError(null);
    setNotice(null);
    try {
      const doc = await api.getHandoff(story!.id);
      const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `traspaso-noticia-${story!.id}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice(
        "Traspaso descargado. Impórtalo en NeuralStories Studio (pestaña «1. Noticias» → «Traspaso desde neural.news»).",
      );
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 409) setError(err.message);
      else setError(err.message);
    }
  };


  if (error && !story) return <p className="text-sm text-red-400">{error}</p>;
  if (!story) return <p className="text-[#6b7a90]">Cargando…</p>;

  const approvedActive = story.active_approval !== null && !story.pending_approval_flag;

  const stage = story.stage;
  const verification = story.verification;
  const approval = story.approval;
  const origin = story.origin;
  const claimVerified = story.claim_verified;
  const steps = readinessSteps({
    status: story.status,
    sourcesCount: story.source_count,
    hasContent: story.usable_content,
    claims: story.claims,
    versions: story.script_versions,
    approval,
    inBatch: story.in_batch,
  });
  const attentionSteps = steps.filter((s) => s.state === "attention");

  /** Qué falta para avanzar en el flujo editorial (fuente → guion aprobado → traspaso). */
  const nextStep = (() => {
    if (story.status === "REJECTED") {
      return { tone: "neutral" as const, text: "Noticia descartada: no generará producción." };
    }
    if (story.claims.length === 0) {
      return {
        tone: "info" as const,
        text: "Siguiente acción: lanzar «Investigar» para registrar afirmaciones y buscar evidencia.",
      };
    }
    if (story.claims.some((c) => c.verification_status === "UNVERIFIED")) {
      return {
        tone: "warn" as const,
        text: "Hay afirmaciones sin verificar: revisa la evidencia abajo antes de aprobar el guion.",
      };
    }
    if (story.script_versions.length === 0) {
      return {
        tone: "info" as const,
        text: "Con la evidencia lista, el siguiente paso es «Generar borrador de guion».",
      };
    }
    if (approvedActive) {
      return {
        tone: "ok" as const,
        text: "Guion aprobado: descarga el traspaso y llévalo a NeuralStories Studio (pestaña «1. Noticias»).",
      };
    }
    if (story.active_approval) {
      return {
        tone: "warn" as const,
        text: "El guion cambió tras aprobarse: revisa la última versión y vuelve a aprobar.",
      };
    }
    return {
      tone: "info" as const,
      text: "Siguiente acción: revisa el guion y pulsa «Aprobar esta versión».",
    };
  })();
  const NEXT_TONE = {
    ok: "notice-ok",
    warn: "rounded-md border border-amber-800 bg-amber-950/60 px-3 py-2 text-sm text-amber-300",
    info: "notice-info",
    neutral: "empty-state",
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{story.title}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <span className={STATUS_BADGE[story.status] || "badge-neutral"}>{story.status_label}</span>
            {story.is_opinion && <span className="badge-warn">Opinión (no verificable)</span>}
            {story.editorial_score !== null && <span className="badge-neutral">puntuación {story.editorial_score}/100</span>}
            <span className="text-xs text-[#6b7a90]">fecha del acontecimiento: {fmtDate(story.original_event_date)}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn" onClick={() => run("research")}>
            Investigar
          </button>
          <button className="btn" onClick={() => run("draft")}>
            Generar borrador de guion
          </button>
          {approvedActive && (
            <>
              <Link
                href={`/estudio?story=${story.id}&revision=${story.approved_version ?? story.latest_version ?? ""}`}
                className="btn-primary"
                title="Abre el estudio con esta noticia ya cargada (misma aplicación)"
              >
                Continuar en Studio
              </Link>
              <button className="btn" onClick={downloadHandoff}>
                Descargar traspaso (JSON)
              </button>
            </>
          )}
          {story.status !== "REJECTED" && (
            <button className="btn-danger" onClick={() => setRejectOpen((v) => !v)}>
              Descartar
            </button>
          )}
        </div>
      </div>

      <p className={NEXT_TONE[nextStep.tone]}>{nextStep.text}</p>

      {/* Cabecera de decisión: dónde está, qué sabe, qué versión vale y su origen */}
      <section className="card" aria-label="Estado editorial de la noticia">
        <DecisionHeader
          stage={stage}
          verification={verification}
          approval={approval}
          origin={origin}
          claimTotal={story.claims.length}
          claimVerified={claimVerified}
          scriptVersion={latest?.version ?? null}
          approvedBy={story.active_approval?.actor ?? null}
          approvedAt={story.active_approval ? fmtDate(story.active_approval.approved_at) : null}
        />
      </section>

      {/* Estado de preparación: qué está hecho y qué falta */}
      <section className="card" aria-label="Estado de preparación">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-300">Estado de preparación</h2>
          {attentionSteps.length > 0 && (
            <span className="badge-warn">
              {attentionSteps.length} punto(s) requieren atención
            </span>
          )}
        </div>
        <ReadinessChecklist steps={steps} />
      </section>

      {error && <p className="notice-err" role="alert">{error}</p>}
      {notice && <p className="notice-ok">{notice}</p>}
      {waiting !== null && <p className="notice-info">Trabajo #{waiting} en marcha…</p>}

      {rejectOpen && (
        <div className="card space-y-2">
          <p className="text-sm">Motivo del descarte (se registra en la auditoría):</p>
          <input className="input" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
          <button className="btn-danger" onClick={reject}>
            Confirmar descarte
          </button>
        </div>
      )}

      {story.summary && (
        <section className="card">
          <h2 className="text-sm font-semibold text-neutral-300">Resumen</h2>
          <p className="mt-1 text-sm text-neutral-300">{story.summary}</p>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="text-sm font-semibold text-neutral-300">Afirmaciones</h2>
          {story.claims.length === 0 && (
            <p className="mt-2 text-sm text-[#6b7a90]">Sin afirmaciones registradas todavía.</p>
          )}
          <ul className="mt-2 space-y-3">
            {story.claims.map((claim) => {
              const badge = VERIF_BADGE[claim.verification_status] || { cls: "badge-neutral", label: claim.verification_status };
              return (
                <li key={claim.id} className="rounded border border-neutral-800 bg-neutral-900 p-3">
                  <p className="text-sm">{claim.statement}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={badge.cls}>{badge.label}</span>
                    {claim.verification_notes && <span className="text-xs text-[#6b7a90]">{claim.verification_notes}</span>}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
        <div className="card">
          <h2 className="text-sm font-semibold text-neutral-300">Evidencias</h2>
          {story.claims.every((c) => c.evidence.length === 0) && (
            <p className="mt-2 text-sm text-[#6b7a90]">
              Sin evidencias. Lanza «Investigar» para buscar respaldo; sin evidencia no se marca nada como confirmado.
            </p>
          )}
          <ul className="mt-2 space-y-3">
            {story.claims.flatMap((claim) =>
              claim.evidence.map((ev) => (
                <li key={ev.id} className="rounded border border-neutral-800 bg-neutral-900 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="badge-info">{KIND_LABEL[ev.kind] || ev.kind}</span>
                    {ev.demo && <span className="badge-demo">DEMO (ficticia)</span>}
                    <span className="text-xs text-[#6b7a90]">confianza {ev.confidence}</span>
                  </div>
                  {ev.publisher && <p className="mt-1 font-medium">{ev.publisher}</p>}
                  {ev.excerpt_or_paraphrase && <p className="mt-1 text-neutral-400">{ev.excerpt_or_paraphrase}</p>}
                  <p className="mt-1 text-xs text-[#6b7a90]">
                    {ev.published_at ? `publicado ${fmtDate(ev.published_at)} · ` : ""}
                    recuperado {fmtDate(ev.retrieved_at)}
                  </p>
                  {ev.url && (
                    <a className="mt-1 inline-block break-all text-xs text-sky-400 hover:underline" href={ev.url} target="_blank" rel="noreferrer noopener">
                      {ev.url}
                    </a>
                  )}
                </li>
              )),
            )}
          </ul>
        </div>
      </section>

      <section className="card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-neutral-300">Guion</h2>
          <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-400">
            <label htmlFor="wpm">Velocidad de locución:</label>
            <input
              id="wpm"
              type="number"
              min={80}
              max={220}
              className="input w-20 px-2 py-1"
              value={wordsPerMinute}
              onChange={(e) => {
                const v = Number(e.target.value) || 150;
                setWordsPerMinute(v);
                localStorage.setItem("nn-words-per-minute", String(v));
              }}
            />
            <span>{wordCount} palabras · ≈{estimatedSeconds} s</span>
          </div>
        </div>

        {story.script_versions.length === 0 ? (
          <p className="text-sm text-[#6b7a90]">Sin versiones todavía. Pulsa «Generar borrador de guion».</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-1">
              {story.script_versions.map((v) => (
                <button
                  key={v.id}
                  onClick={() => {
                    dirtyRef.current = false;
                    setSelectedVersion(v.version);
                    setContent(v.content);
                  }}
                  className={`badge ${selectedVersion === v.version ? "bg-sky-900 text-sky-200" : "badge-neutral"}`}
                >
                  v{v.version} · {v.author_type === "AI" ? "auto" : "humana"}
                  {story.active_approval?.script_version_id === v.id && story.active_approval !== null ? " · aprobada" : ""}
                </button>
              ))}
            </div>

            {approvedActive && story.active_approval && (
              <div className="rounded border border-emerald-800 bg-emerald-950/50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Guion aprobado</p>
                <p className="mt-1 text-sm text-emerald-100">
                  v{story.script_versions.find((v) => v.id === story.active_approval!.script_version_id)?.version} · aprobado por{" "}
                  {story.active_approval.actor} el {fmtDate(story.active_approval.approved_at)}
                </p>
                <p className="mt-1 text-xs text-emerald-300/80">
                  Cualquier edición posterior crea una versión nueva y anula esta aprobación.
                </p>
              </div>
            )}
            {latest && story.active_approval && story.active_approval.script_version_id !== latest.id && (
              <p className="badge-warn w-fit">
                La aprobación de una versión anterior quedó anulada al editarse el guion: vuelve a aprobar la última.
              </p>
            )}

            <textarea
              className="input min-h-80 font-mono text-sm leading-relaxed"
              value={content}
              onChange={(e) => {
                dirtyRef.current = true;
                setContent(e.target.value);
              }}
              aria-label="Editor de guion"
            />
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" onClick={saveEdit} disabled={!latest || content === latest.content}>
                Guardar borrador
              </button>
              <button className="btn" onClick={approve} disabled={!latest || approvedActive}>
                Aprobar esta versión
              </button>
              <Link href="/lotes" className="btn">
                Ir a lotes
              </Link>
            </div>
          </>
        )}
      </section>

      <section className="card">
        <h2 className="text-sm font-semibold text-neutral-300">Fuentes de la noticia</h2>
        <ul className="mt-2 space-y-1 text-sm">
          {story.sources.map((s) => (
            <li key={s.source_id} className="flex flex-wrap items-center gap-2">
              <span className="capitalize badge-neutral">{s.provider.replace("_", " ")}</span>
              {s.canonical_url ? (
                <a href={s.canonical_url} target="_blank" rel="noreferrer noopener" className="text-sky-400 hover:underline">
                  {s.title || s.canonical_url}
                </a>
              ) : (
                <span>{s.title}</span>
              )}
              <span className="text-xs text-[#6b7a90]">({s.relevance})</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-neutral-300">Preparación visual (storyboard)</h2>
          <button className="btn px-2 py-1 text-xs" onClick={loadStoryboard} disabled={!latest}>
                {storyboard ? "Actualizar" : "Preparar escenas"}
          </button>
        </div>

        {!storyboard ? (
          <p className="text-sm text-[#6b7a90]">
            Genera el storyboard del guion vigente: escenas, duración orientativa, rótulos y un prompt de imagen
            preliminar por escena. No se genera ninguna imagen ni vídeo.
          </p>
        ) : (
          <>
            <p className="text-xs text-[#6b7a90]">
              Guion v{storyboard.script_version} · {storyboard.approved ? "aprobado" : "sin aprobar"} · {storyboard.note}
            </p>
            <ol className="space-y-2">
              {storyboard.scenes.map((scene, index) => (
                <li key={index} className="rounded border border-neutral-800 bg-neutral-900 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="badge-info">Escena {index + 1}</span>
                    <span className="badge-neutral">≈{scene.seconds} s</span>
                  </div>
                  <p className="mt-1">{scene.message}</p>
                  <p className="mt-1 text-xs text-neutral-400">Visual: {scene.visual}</p>
                  {scene.overlay_text && (
                    <p className="mt-1 text-xs text-neutral-400">Rótulo: {scene.overlay_text}</p>
                  )}
                  {scene.data_source && (
                    <p className="mt-1 text-xs text-[#6b7a90]">Origen del dato: {scene.data_source}</p>
                  )}
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-sky-400">Prompt de imagen</summary>
                    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap rounded bg-neutral-950 p-2 text-xs text-neutral-300">
                      {scene.image_prompt}
                    </pre>
                    <button
                      className="btn mt-1 px-2 py-0.5 text-xs"
                      onClick={() => copyPrompt(scene.image_prompt)}
                    >
                      Copiar prompt
                    </button>
                  </details>
                </li>
              ))}
            </ol>
          </>
        )}
      </section>
    </div>
  );
}
