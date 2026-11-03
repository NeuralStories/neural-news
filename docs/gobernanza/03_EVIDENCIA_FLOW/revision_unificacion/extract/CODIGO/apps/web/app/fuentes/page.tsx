"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

type Mode = "url" | "text";

export default function FuentesPage() {
  const [items, setItems] = useState<SourceListItem[]>([]);
  const [mode, setMode] = useState<Mode>("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [transcript, setTranscript] = useState("");
  const [showExtra, setShowExtra] = useState(false);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("todas");
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

  const submit = async () => {
    const payload: Record<string, unknown> =
      mode === "url"
        ? { url: url || undefined, transcript: transcript || undefined }
        : { text: text || undefined };
    if (!payload.url && !payload.text) return;
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const key = `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const result = await api.addSource(payload, key);
      if (result.message) setNotice(result.message);
      else if (payload.transcript)
        setNotice("Fuente registrada con su transcripción; el análisis está en marcha.");
      else setNotice("Fuente registrada; el análisis está en marcha.");
      if (result.job_id) await poll(result.job_id, refresh);
      await refresh();
      setUrl("");
      setText("");
      setTranscript("");
      setShowExtra(false);
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
    setMode("text");
    setText(content.slice(0, 2_000_000));
    setNotice(`Archivo «${file.name}» cargado; revisa el texto y pulsa Registrar`);
  };

  const counts = useMemo(() => {
    const byStatus = new Map<string, number>();
    items.forEach((s) => byStatus.set(s.status, (byStatus.get(s.status) ?? 0) + 1));
    return { total: items.length, byStatus };
  }, [items]);

  const shown = useMemo(
    () =>
      items.filter((s) => {
        if (statusFilter !== "todas" && s.status !== statusFilter) return false;
        if (!filter.trim()) return true;
        const q = filter.toLowerCase();
        return (
          (s.title || "").toLowerCase().includes(q) ||
          (s.canonical_url || "").toLowerCase().includes(q)
        );
      }),
    [items, filter, statusFilter],
  );

  const canSubmit = mode === "url" ? Boolean(url.trim()) : Boolean(text.trim());

  return (
    <div className="space-y-6">
      <section className="card space-y-4">
        <div>
          <h1 className="text-lg font-semibold">Añadir fuente</h1>
          <p className="mt-1 text-sm text-slate-400">
            Paso 1 del flujo: registra de dónde sale la noticia. Después se propondrán candidatas en{" "}
            <a href="/noticias" className="text-sky-400 hover:underline">
              Noticias
            </a>
            .
          </p>
        </div>

        <div role="tablist" aria-label="Tipo de fuente" className="flex gap-1">
          {(
            [
              { id: "url", label: "Enlace (YouTube, Spotify, artículo o feed)" },
              { id: "text", label: "Texto o archivo" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={mode === tab.id}
              onClick={() => setMode(tab.id)}
              className={`min-h-9 rounded-md px-3 py-1.5 text-sm transition ${
                mode === tab.id
                  ? "bg-sky-950/80 text-sky-200 ring-1 ring-sky-800"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {mode === "url" ? (
          <div className="space-y-2">
            <label className="label" htmlFor="fuente-url">
              Enlace de la fuente
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                id="fuente-url"
                className="input"
                placeholder="https://… (YouTube, Spotify, artículo o feed RSS)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <button className="btn-primary shrink-0" disabled={loading || !canSubmit} onClick={submit}>
                Registrar y analizar
              </button>
            </div>
            <button
              className="btn-ghost text-xs"
              aria-expanded={showExtra}
              onClick={() => setShowExtra((v) => !v)}
            >
              {showExtra ? "▾" : "▸"} Transcripción (opcional)
            </button>
            {showExtra && (
              <div className="space-y-1">
                <textarea
                  className="input min-h-24"
                  aria-label="Transcripción de la fuente"
                  placeholder="Si el vídeo o episodio no tiene transcripción, pégala aquí y se analizará lo que se ha dicho (se guarda junto a la fuente)."
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                />
                <p className="hint">Se envía junto al enlace; sin ella, el análisis usa lo que el proveedor ofrece.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.md,.json,text/plain"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
            <div className="flex flex-wrap items-center gap-2">
              <button className="btn" onClick={() => fileInput.current?.click()}>
                Subir archivo de texto (.txt/.md, máx. 2 MB)
              </button>
              <span className="hint">o pega el texto abajo; se tratará como fuente manual.</span>
            </div>
            <textarea
              className="input min-h-32"
              aria-label="Texto de la fuente"
              placeholder="Pega aquí el texto, comunicado o documento…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div className="flex justify-end">
              <button className="btn-primary" disabled={loading || !canSubmit} onClick={submit}>
                Registrar y analizar
              </button>
            </div>
          </div>
        )}

        {error && <p className="notice-err" role="alert">{error}</p>}
        {notice && <p className="notice-ok">{notice}</p>}
        {waiting !== null && <p className="notice-info">Analizando la fuente (trabajo #{waiting})…</p>}
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">
            Fuentes registradas{" "}
            <span className="text-sm font-normal text-[#6b7a90]">
              ({counts.total}
              {statusFilter !== "todas" ? ` · filtradas: ${shown.length}` : ""})
            </span>
          </h2>
          <input
            className="input max-w-64"
            placeholder="Buscar título o enlace…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Buscar fuentes"
          />
        </div>

        <div className="mb-3 flex flex-wrap gap-1" role="group" aria-label="Filtrar por estado">
          {["todas", "READY", "PARTIAL", "METADATA_ONLY", "FAILED"].map((status) => {
            const count = status === "todas" ? counts.total : counts.byStatus.get(status) ?? 0;
            if (status !== "todas" && count === 0) return null;
            const label =
              status === "todas"
                ? "Todas"
                : { READY: "Listas", PARTIAL: "Parciales", METADATA_ONLY: "Sin transcripción", FAILED: "Con error" }[status] ?? status;
            return (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                aria-pressed={statusFilter === status}
                className={`min-h-8 rounded-full px-3 text-xs transition ${
                  statusFilter === status
                    ? "bg-sky-950/80 text-sky-200 ring-1 ring-sky-800"
                    : "bg-slate-900 text-slate-400 ring-1 ring-slate-800 hover:text-slate-200"
                }`}
              >
                {label} ({count})
              </button>
            );
          })}
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-800">
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
              {shown.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-[#6b7a90]">
                    {items.length === 0
                      ? "Todavía no hay fuentes. Registra la primera arriba."
                      : "Ninguna fuente coincide con el filtro."}
                  </td>
                </tr>
              )}
              {shown.map((s) => (
                <SourceRow key={s.id} source={s} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function SourceRow({ source }: { source: SourceListItem }) {
  const [detail, setDetail] = useState<SourceDetail | null>(null);
  const [transcript, setTranscript] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { poll } = useJobPolling();

  const toggle = async () => {
    if (detail) return setDetail(null);
    const d = await api.getSource(source.id);
    setDetail(d);
  };

  const saveTranscript = async () => {
    if (!transcript.trim()) return;
    try {
      await api.addTranscript(source.id, transcript);
      setMsg("Transcripción guardada. Vuelve a procesar la fuente para extraer noticias.");
      setTranscript("");
      setDetail(await api.getSource(source.id));
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  const reprocess = async (event: React.MouseEvent) => {
    event.stopPropagation();
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.processSource(source.id);
      setMsg(res.created ? "Volver a analizar la fuente…" : "Ya había un análisis en marcha; se reutiliza.");
      await poll(res.job_id, async () => {
        setDetail(await api.getSource(source.id));
      });
    } catch (e) {
      setMsg((e as Error).message);
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
      setMsg("Pidiendo el análisis del vídeo…");
      await poll(res.job_id, async () => {
        setDetail(await api.getSource(source.id));
      });
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <tr className="cursor-pointer hover:bg-slate-900/60" onClick={toggle}>
        <td className="max-w-72">
          <div className="font-medium">{source.title || "(sin título)"}</div>
          <div className="text-xs text-[#6b7a90]">
            {source.demo && <span className="badge-demo mr-1">DEMO</span>}
            registrado {fmtDate(source.imported_at)}
          </div>
        </td>
        <td className="capitalize text-slate-300">{source.provider.replace("_", " ")}</td>
        <td>
          <span className={STATUS_BADGE[source.status] || "badge-neutral"}>{source.status_label}</span>
        </td>
        <td className="text-slate-400">{fmtDate(source.published_at)}</td>
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
            <button className="btn-xs" onClick={reprocess} disabled={busy}>
              {busy ? "Trabajando…" : "Volver a analizar"}
            </button>
            {source.provider === "youtube" && (
              <button className="btn-xs" onClick={analyzeVideo} disabled={busy}>
                Analizar vídeo
              </button>
            )}
          </div>
        </td>
      </tr>
      {detail && (
        <tr className="bg-slate-900/40">
          <td colSpan={6}>
            <div className="space-y-3 p-2">
              {detail.contents.length === 0 && <p className="text-sm text-slate-400">Sin contenido todavía.</p>}
              {detail.contents.map((c) => (
                <div key={c.id} className="rounded border border-slate-800 bg-slate-900 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={c.content_type === "TRANSCRIPT" ? "badge-ok" : c.content_type === "METADATA_ONLY" ? "badge-warn" : "badge-info"}>
                      {c.content_type_label}
                    </span>
                    {c.is_verbatim ? <span className="badge-neutral">texto literal</span> : <span className="badge-neutral">no literal</span>}
                    {c.coverage !== null && <span className="badge-neutral">cobertura {Math.round(c.coverage * 100)}%</span>}
                    <span className="text-xs text-[#6b7a90]">
                      {c.char_count.toLocaleString("es-ES")} caracteres · {c.segment_count} fragmentos · {c.provider || "—"}
                    </span>
                  </div>
                  {detail.stories.length > 0 && (
                    <div className="mt-2 text-xs text-slate-400">
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
              {(source.status === "METADATA_ONLY" || source.status === "PARTIAL" || source.status === "READY") && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    className="input"
                    aria-label="Añadir transcripción a esta fuente"
                    placeholder="Pega aquí una transcripción para analizar lo que se ha dicho"
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                  />
                  <button className="btn-primary shrink-0" onClick={saveTranscript} disabled={!transcript.trim()}>
                    Guardar transcripción
                  </button>
                </div>
              )}
              {msg && <p className="notice-ok">{msg}</p>}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
