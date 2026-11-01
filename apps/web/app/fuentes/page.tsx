"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { SourceDetail, SourceListItem } from "@/lib/types";

const STATUS_BADGE: Record<string, string> = {
  NEW: "badge-neutral",
  FETCHING: "badge-info",
  READY: "badge-ok",
  PARTIAL: "badge-warn",
  METADATA_ONLY: "badge-warn",
  FAILED: "badge-err",
};

/**
 * Severidad explícita de un mensaje de la interfaz (hallazgo B4).
 * Antes, el mismo `msg` pintaba en verde tanto un éxito como un error: «el vídeo
 * no tiene subtítulos» se leía como una operación correcta. La severidad la
 * decide la acción, nunca el color.
 */
type MsgKind = "ok" | "warn" | "error";

const MSG_CLASS: Record<MsgKind, string> = {
  ok: "text-emerald-400",
  warn: "text-amber-400",
  error: "text-red-400",
};

type Msg = { text: string; kind: MsgKind } | null;

export default function FuentesPage() {
  const [items, setItems] = useState<SourceListItem[]>([]);
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { waiting, poll } = useJobPolling();
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listSources();
      setItems(data.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const submit = async (payload: Record<string, unknown>) => {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const key = `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const result = await api.addSource(payload, key);
      if (result.message) setNotice(result.message);
      else setNotice("Fuente registrada; el análisis está en marcha.");
      if (result.job_id) await poll(result.job_id, refresh);
      await refresh();
      setUrl("");
      setText("");
      setTranscript("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const onFile = async (file: File) => {
    if (file.size > 2_000_000) {
      setError("El archivo supera 2 MB; pega el texto directamente o usa un archivo más pequeño");
      return;
    }
    const content = await file.text();
    setText(content.slice(0, 2_000_000));
    setNotice(`Archivo «${file.name}» cargado; revisa el texto y pulsa Registrar`);
  };

  return (
    <div className="space-y-6">
      <section className="card space-y-4">
        <div>
          <h1 className="text-lg font-semibold">Añadir fuente</h1>
          <p className="mt-1 text-sm text-neutral-400">
            Pega una URL de YouTube, un episodio de Spotify, un artículo o feed web — o aporta texto y
            transcripciones directamente.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input"
            placeholder="https://… (YouTube, Spotify, artículo o feed RSS)"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            className="btn-primary shrink-0"
            disabled={loading || (!url && !text)}
            onClick={() =>
              submit({
                url: url || undefined,
                text: text || undefined,
                // La transcripción pegada se envía con el alta: antes se perdía en
                // silencio (hallazgo B2). El backend la guarda como TRANSCRIPT.
                transcript: transcript.trim() || undefined,
              })
            }
          >
            Registrar y analizar
          </button>
        </div>

        <details className="rounded-md border border-neutral-800 bg-neutral-900/40 p-3 text-sm">
          <summary className="cursor-pointer text-neutral-300">Aportar texto, archivo o transcripción</summary>
          <div className="mt-3 space-y-3">
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.md,.json,text/plain"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
            <button className="btn" onClick={() => fileInput.current?.click()}>
              Subir archivo de texto (.txt/.md, máx. 2 MB)
            </button>
            <textarea
              className="input min-h-24"
              placeholder="Texto pegado (se tratará como fuente manual)"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <textarea
              className="input min-h-16"
              placeholder="Transcripción (opcional): si el vídeo o episodio no tiene transcripción, pégala aquí para analizar lo que se ha dicho"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
            />
          </div>
        </details>

        {error && <p className="text-sm text-red-400">{error}</p>}
        {notice && <p className="text-sm text-emerald-400">{notice}</p>}
        {waiting !== null && <p className="text-sm text-sky-400">Analizando la fuente (trabajo #{waiting})…</p>}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Fuentes registradas</h2>
        <div className="overflow-x-auto rounded-lg border border-neutral-800">
          <table className="table-base">
            <thead>
              <tr>
                <th>Título</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Fecha original</th>
                <th>Enlace</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-neutral-500">
                    Todavía no hay fuentes. Registra la primera arriba.
                  </td>
                </tr>
              )}
              {items.map((s) => (
                <SourceRow key={s.id} source={s} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

type TranscriptInfo = {
  found: boolean;
  message?: string;
  content_type?: string;
  content_type_label?: string;
  is_verbatim?: boolean;
  provider?: string;
  text?: string;
  segments?: Array<{ start_ms: number | null; end_ms: number | null; text: string; sequence: number }>;
};

function SourceRow({ source }: { source: SourceListItem }) {
  const [detail, setDetail] = useState<SourceDetail | null>(null);
  const [transcript, setTranscript] = useState("");
  const [msg, setMsg] = useState<Msg>(null);
  const [busy, setBusy] = useState(false);
  const [transcriptData, setTranscriptData] = useState<TranscriptInfo | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const { poll } = useJobPolling();

  const toggle = async () => {
    if (detail) return setDetail(null);
    const d = await api.getSource(source.id);
    setDetail(d);
  };

  const loadTranscript = async () => {
    setShowTranscript((v) => !v);
    try {
      setTranscriptData(await api.getTranscript(source.id));
    } catch (e) {
      setMsg({ text: (e as Error).message, kind: "error" });
    }
  };

  const searchTranscript = async (event: React.MouseEvent) => {
    event.stopPropagation();
    setBusy(true);
    setMsg(null);
    try {
      const body = await api.transcribeSource(source.id);
      // `found: false` NO es un error: es una respuesta honesta con su motivo.
      setMsg({
        text: body.message ?? (body.created ? "Transcripción creada y almacenada." : "Transcripción encontrada."),
        kind: body.found ? "ok" : "warn",
      });
      setTranscriptData(await api.getTranscript(source.id));
      setDetail(await api.getSource(source.id));
    } catch (e) {
      setMsg({ text: (e as Error).message, kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  const saveTranscript = async () => {
    if (!transcript.trim()) return;
    try {
      await api.addTranscript(source.id, transcript);
      setMsg({
        text: "Transcripción guardada. Vuelve a procesar la fuente para extraer noticias.",
        kind: "ok",
      });
      setTranscript("");
      setDetail(await api.getSource(source.id));
    } catch (e) {
      setMsg({ text: (e as Error).message, kind: "error" });
    }
  };

  const reprocess = async (event: React.MouseEvent) => {
    event.stopPropagation();
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.processSource(source.id);
      setMsg({
        text: res.created ? "Volver a analizar la fuente…" : "Ya había un análisis en marcha; se reutiliza.",
        kind: "ok",
      });
      await poll(res.job_id, async () => {
        setDetail(await api.getSource(source.id));
      });
    } catch (e) {
      setMsg({ text: (e as Error).message, kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  const analyzeVideo = async (event: React.MouseEvent) => {
    event.stopPropagation();
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.analyzeVideo(source.id);
      setMsg({ text: "Pidiendo el análisis del vídeo…", kind: "ok" });
      await poll(res.job_id, async () => {
        setDetail(await api.getSource(source.id));
      });
    } catch (e) {
      setMsg({ text: (e as Error).message, kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <tr className="cursor-pointer hover:bg-neutral-900/60" onClick={toggle}>
        <td className="max-w-72">
          <div className="font-medium">{source.title || "(sin título)"}</div>
          <div className="text-xs text-neutral-500">
            {source.demo && <span className="badge-demo mr-1">DEMO</span>}
            registrado {fmtDate(source.imported_at)}
          </div>
        </td>
        <td className="capitalize text-neutral-300">{source.provider.replace("_", " ")}</td>
        <td>
          <span className={STATUS_BADGE[source.status] || "badge-neutral"}>{source.status_label}</span>
        </td>
        <td className="text-neutral-400">{fmtDate(source.published_at)}</td>
        <td className="max-w-56 truncate text-sky-400">
          {source.canonical_url ? (
            <a href={source.canonical_url} target="_blank" rel="noreferrer noopener" onClick={(e) => e.stopPropagation()}>
              abrir original
            </a>
          ) : (
            "—"
          )}
        </td>
        <td onClick={(e) => e.stopPropagation()}>
          <div className="flex flex-wrap gap-1">
            <button className="btn px-2 py-1 text-xs" onClick={reprocess} disabled={busy}>
              {busy ? "Trabajando…" : "Volver a analizar"}
            </button>
            {source.provider === "youtube" && (
              <button className="btn px-2 py-1 text-xs" onClick={analyzeVideo} disabled={busy}>
                Analizar vídeo
              </button>
            )}
            <button className="btn px-2 py-1 text-xs" onClick={loadTranscript}>
              Transcripción
            </button>
            <button
              className="btn-primary px-2 py-1 text-xs"
              onClick={searchTranscript}
              disabled={busy}
              title="Busca subtítulos públicos (YouTube), el texto del artículo o la transcripción del feed"
            >
              {busy ? "Buscando…" : "Buscar transcripción"}
            </button>
          </div>
        </td>
      </tr>
      {detail && (
        <tr className="bg-neutral-900/40">
          <td colSpan={6}>
            <div className="space-y-3 p-2">
              {detail.contents.length === 0 && <p className="text-sm text-neutral-400">Sin contenido todavía.</p>}
              {detail.contents.map((c) => (
                <div key={c.id} className="rounded border border-neutral-800 bg-neutral-900 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={c.content_type === "TRANSCRIPT" ? "badge-ok" : c.content_type === "METADATA_ONLY" ? "badge-warn" : "badge-info"}>
                      {c.content_type_label}
                    </span>
                    {c.is_verbatim ? <span className="badge-neutral">texto literal</span> : <span className="badge-neutral">no literal</span>}
                    {c.coverage !== null && <span className="badge-neutral">cobertura {Math.round(c.coverage * 100)}%</span>}
                    <span className="text-xs text-neutral-500">
                      {c.char_count.toLocaleString("es-ES")} caracteres · {c.segment_count} fragmentos · {c.provider || "—"}
                    </span>
                  </div>
                  {detail.stories.length > 0 && (
                    <div className="mt-2 text-xs text-neutral-400">
                      Noticias derivadas:{" "}
                      {detail.stories.map((st) => (
                        <a key={st.id} href={`/noticias/${st.id}`} className="mr-2 text-sky-400 hover:underline">
                          {st.title}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {showTranscript && (
                <div className="rounded border border-neutral-800 bg-neutral-950 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className={transcriptData?.found ? "badge-ok" : "badge-warn"}>
                      {transcriptData?.found ? `Transcripción (${transcriptData.content_type_label ?? "transcripción"})` : "Sin transcripción"}
                    </span>
                    {transcriptData?.found && transcriptData.provider && (
                      <span className="text-xs text-neutral-500">vía {transcriptData.provider}</span>
                    )}
                  </div>
                  {transcriptData?.found && transcriptData.text && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-sky-400">Ver texto completo</summary>
                      <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap text-xs text-neutral-200">{transcriptData.text}</pre>
                      {transcriptData.segments && transcriptData.segments.length > 0 && (
                        <p className="mt-1 text-xs text-neutral-500">
                          {transcriptData.segments.length} fragmentos con marcas de tiempo.
                        </p>
                      )}
                    </details>
                  )}
                  {!transcriptData?.found && transcriptData?.message && (
                    <p className="mt-1 text-xs text-neutral-400">{transcriptData.message}</p>
                  )}
                </div>
              )}
              {(source.status === "METADATA_ONLY" || source.status === "PARTIAL" || source.status === "READY") && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    className="input"
                    placeholder="Pega aquí una transcripción para analizar lo que se ha dicho"
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                  />
                  <button className="btn-primary shrink-0" onClick={saveTranscript} disabled={!transcript.trim()}>
                    Guardar transcripción
                  </button>
                </div>
              )}
              {msg && (
                <p
                  className={`text-sm ${MSG_CLASS[msg.kind]}`}
                  role={msg.kind === "error" ? "alert" : "status"}
                >
                  {msg.text}
                </p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
