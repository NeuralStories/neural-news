"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BADGE_DE_NOTICIA, ETIQUETA_PAQUETE, insigniaDe } from "@/lib/estados";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { BatchDetail, StoryListItem } from "@/lib/types";

export default function LotesPage() {
  const [batches, setBatches] = useState<{ id: number; name: string; target_size: number; status: string; created_at: string }[]>([]);
  const [selected, setSelected] = useState<BatchDetail | null>(null);
  const [stories, setStories] = useState<StoryListItem[]>([]);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [targetSize, setTargetSize] = useState<5 | 10>(5);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { waiting, poll } = useJobPolling();

  const refresh = useCallback(async () => {
    try {
      const [batchList, storyList] = await Promise.all([api.listBatches(), api.listStories()]);
      setBatches(batchList.items);
      setStories(storyList.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = (id: number) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < targetSize) next.add(id);
      return next;
    });
  };

  const changeSize = (size: 5 | 10) => {
    setTargetSize(size);
    setChecked(new Set());
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
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const open = async (id: number) => {
    setError(null);
    try {
      setSelected(await api.getBatch(id));
    } catch (e) {
      setError((e as Error).message);
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
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const download = (batchId: number) => {
    window.open(`/api/v1/batches/${batchId}/package`, "_blank");
  };

  const pendingCount = checked.size < targetSize ? targetSize - checked.size : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Lotes editoriales (5 o 10 noticias)</h1>

      <section className="card space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-neutral-300">Tamaño:</span>
          {[5, 10].map((size) => (
            <button key={size} onClick={() => changeSize(size as 5 | 10)} className={checked.size === 0 && targetSize === size ? "btn-primary" : "btn"}>
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
          <button className="btn-primary" onClick={create} disabled={checked.size !== targetSize}>
            Crear lote ({checked.size}/{targetSize})
          </button>
        </div>
        {pendingCount > 0 && (
          <p className="text-xs text-neutral-500">Selecciona {pendingCount} noticia(s) más para completar el lote.</p>
        )}
        {checked.size > 0 && (
          <div className="max-h-40 space-y-1 overflow-y-auto rounded border border-neutral-800 p-2">
            {stories
              .filter((s) => checked.has(s.id))
              .map((s) => (
                <div key={s.id} className="flex items-center gap-2 text-sm">
                  <span className={insigniaDe(BADGE_DE_NOTICIA, s.status)}>{s.status_label}</span>
                  <span className="truncate">{s.title}</span>
                  <button className="ml-auto text-xs text-red-400 hover:underline" onClick={() => toggle(s.id)}>
                    quitar
                  </button>
                </div>
              ))}
          </div>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}
        {notice && <p className="text-sm text-emerald-400">{notice}</p>}
        {waiting !== null && <p className="text-sm text-sky-400">Exportando (trabajo #{waiting})…</p>}

        <div className="table-wrap">
          <table className="table-base">
            <thead>
              <tr>
                <th>Noticia</th>
                <th>Estado</th>
                <th>Puntuación</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {stories
                .filter((s) => !checked.has(s.id))
                .map((s) => (
                  <tr key={s.id} className="hover:bg-neutral-900/60">
                    <td className="max-w-96">
                      <Link href={`/noticias/${s.id}`} className="hover:text-sky-400">
                        {s.title}
                      </Link>
                    </td>
                    <td>
                      <span className={insigniaDe(BADGE_DE_NOTICIA, s.status)}>{s.status_label}</span>
                    </td>
                    <td className="tabular-nums">{s.editorial_score ?? "—"}</td>
                    <td>
                      <button className="btn px-2 py-1 text-xs" onClick={() => toggle(s.id)} disabled={checked.size >= targetSize}>
                        Añadir
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      {batches.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold text-neutral-300">Lotes existentes</h2>
          <ul className="space-y-1 text-sm">
            {batches.map((b) => (
              <li key={b.id}>
                <button onClick={() => open(b.id)} className="text-sky-400 hover:underline">
                  #{b.id} {b.name}
                </button>{" "}
                <span className="text-neutral-500">
                  · {b.target_size} noticias · {ETIQUETA_PAQUETE[b.status] ?? b.status} ·{" "}
                  {fmtDate(b.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {selected && (
        <section className="card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold">
              {selected.name} <span className="text-neutral-500">(#{selected.id})</span>
            </h2>
            <div className="flex flex-wrap gap-2">
              <button className="btn-primary" onClick={exportPackage}>
                Exportar paquete
              </button>
              {selected.packages && selected.packages.length > 0 && (
                <button className="btn" onClick={() => download(selected.id)}>
                  Descargar paquete (ZIP)
                </button>
              )}
            </div>
          </div>

          <p className="text-sm text-neutral-400">
            {selected.ready_count} aprobada(s) · {selected.pending_count} pendiente(s) de aprobación.
            {selected.pending_count > 0 && " Ninguna noticia pendiente puede grabarse todavía."}
          </p>

          <ul className="space-y-1">
            {selected.stories.map((s) => (
              <li key={s.story_id} className="flex flex-wrap items-center gap-2 rounded border border-neutral-800 bg-neutral-900 p-2 text-sm">
                <span className="text-neutral-500">{s.position + 1}.</span>
                <Link href={`/noticias/${s.story_id}`} className="hover:text-sky-400">
                  {s.title}
                </Link>
                <span className={s.approved ? "badge-ok" : "badge-warn"}>{s.approved ? "Aprobada" : "Pendiente de aprobación"}</span>
                {s.pending_reason && <span className="text-xs text-neutral-500">{s.pending_reason}</span>}
                <span className="ml-auto flex gap-1">
                  <button className="btn px-2 py-0.5 text-xs" onClick={() => move(s.story_id, -1)}>
                    ↑
                  </button>
                  <button className="btn px-2 py-0.5 text-xs" onClick={() => move(s.story_id, 1)}>
                    ↓
                  </button>
                </span>
              </li>
            ))}
          </ul>

          {selected.packages && selected.packages.length > 0 && (
            <p className="text-xs text-neutral-500">
              Último paquete: v{selected.packages[0].version} · sha256 {selected.packages[0].sha256.slice(0, 16)}… ·{" "}
              {fmtDate(selected.packages[0].created_at)}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
