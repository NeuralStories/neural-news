"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { StoryDetail } from "@/lib/types";

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
  const { waiting, poll } = useJobPolling();

  const refresh = useCallback(async () => {
    try {
      const d = await api.getStory(Number(params.id));
      setStory(d);
      const latest = d.script_versions[d.script_versions.length - 1];
      setContent(latest?.content ?? "");
      setSelectedVersion(latest?.version ?? null);
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
    if (!latest) return;
    try {
      const res = await api.saveScript(story!.id, content, latest.version);
      setNotice(`Guardado como versión ${res.script_version.version}. Si estaba aprobada, la aprobación queda anulada.`);
      await refresh();
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 409) {
        setError(`${err.message} (la versión actual del servidor es la ${String((err as unknown as { detail?: { current_version?: number } }).detail?.current_version ?? "?")})`);
      } else {
        setError(err.message);
      }
    }
  };

  const approve = async () => {
    if (!latest) return;
    try {
      await api.approve(story!.id, latest.id);
      setNotice("Guion aprobado. Si editas el texto después, tendrás que aprobar la nueva versión.");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
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

  if (error && !story) return <p className="text-sm text-red-400">{error}</p>;
  if (!story) return <p className="text-neutral-500">Cargando…</p>;

  const approvedActive = story.active_approval !== null && !story.pending_approval_flag;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{story.title}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <span className={STATUS_BADGE[story.status] || "badge-neutral"}>{story.status_label}</span>
            {story.is_opinion && <span className="badge-warn">Opinión (no verificable)</span>}
            {story.editorial_score !== null && <span className="badge-neutral">puntuación {story.editorial_score}/100</span>}
            <span className="text-xs text-neutral-500">fecha del acontecimiento: {fmtDate(story.original_event_date)}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn" onClick={() => run("research")}>
            Investigar
          </button>
          <button className="btn" onClick={() => run("draft")}>
            Generar borrador de guion
          </button>
          {story.status !== "REJECTED" && (
            <button className="btn-danger" onClick={() => setRejectOpen((v) => !v)}>
              Descartar
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {notice && <p className="text-sm text-emerald-400">{notice}</p>}
      {waiting !== null && <p className="text-sm text-sky-400">Trabajo #{waiting} en marcha…</p>}

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
            <p className="mt-2 text-sm text-neutral-500">Sin afirmaciones registradas todavía.</p>
          )}
          <ul className="mt-2 space-y-3">
            {story.claims.map((claim) => {
              const badge = VERIF_BADGE[claim.verification_status] || { cls: "badge-neutral", label: claim.verification_status };
              return (
                <li key={claim.id} className="rounded border border-neutral-800 bg-neutral-900 p-3">
                  <p className="text-sm">{claim.statement}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={badge.cls}>{badge.label}</span>
                    {claim.verification_notes && <span className="text-xs text-neutral-500">{claim.verification_notes}</span>}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
        <div className="card">
          <h2 className="text-sm font-semibold text-neutral-300">Evidencias</h2>
          {story.claims.every((c) => c.evidence.length === 0) && (
            <p className="mt-2 text-sm text-neutral-500">
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
                    <span className="text-xs text-neutral-500">confianza {ev.confidence}</span>
                  </div>
                  {ev.publisher && <p className="mt-1 font-medium">{ev.publisher}</p>}
                  {ev.excerpt_or_paraphrase && <p className="mt-1 text-neutral-400">{ev.excerpt_or_paraphrase}</p>}
                  <p className="mt-1 text-xs text-neutral-500">
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
              <span className="text-xs text-neutral-500">({s.relevance})</span>
            </li>
          ))}
        </ul>
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
          <p className="text-sm text-neutral-500">Sin versiones todavía. Pulsa «Generar borrador de guion».</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-1">
              {story.script_versions.map((v) => (
                <button
                  key={v.id}
                  onClick={() => {
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

            {approvedActive && <p className="badge-ok w-fit">Aprobada ({fmtDate(story.active_approval?.approved_at)}) — cualquier edición anulará la aprobación</p>}
            {latest && story.active_approval && story.active_approval.script_version_id !== latest.id && (
              <p className="badge-warn w-fit">La aprobación de una versión anterior quedó anulada al editarse el guion</p>
            )}

            <textarea
              className="input min-h-80 font-mono text-sm leading-relaxed"
              value={content}
              onChange={(e) => setContent(e.target.value)}
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
    </div>
  );
}
