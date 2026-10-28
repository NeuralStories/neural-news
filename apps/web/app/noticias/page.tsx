"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { StoryListItem } from "@/lib/types";

const STATUS_BADGE: Record<string, string> = {
  CANDIDATE: "badge-neutral",
  RESEARCHING: "badge-info",
  REVIEW_REQUIRED: "badge-warn",
  SCRIPT_DRAFT: "badge-info",
  APPROVED: "badge-ok",
  REJECTED: "badge-neutral",
};

export default function NoticiasPage() {
  const [items, setItems] = useState<StoryListItem[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { waiting, poll } = useJobPolling();

  const refresh = useCallback(async () => {
    try {
      const data = await api.listStories();
      setItems(data.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const act = async (story: StoryListItem, kind: "research" | "draft") => {
    try {
      const res = kind === "research" ? await api.research(story.id) : await api.draft(story.id);
      await poll(res.job_id, refresh);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const shown = filter
    ? items.filter(
        (s) =>
          s.title.toLowerCase().includes(filter.toLowerCase()) ||
          s.status_label.toLowerCase().includes(filter.toLowerCase()),
      )
    : items;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">Noticias candidatas y aprobadas</h1>
        <input
          className="input max-w-64"
          placeholder="Filtrar por tema o estado…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {waiting !== null && <p className="text-sm text-sky-400">Trabajo #{waiting} en marcha…</p>}

      <div className="overflow-x-auto rounded-lg border border-neutral-800">
        <table className="table-base">
          <thead>
            <tr>
              <th>Tema</th>
              <th>Fecha real</th>
              <th>Estado</th>
              <th>Puntuación</th>
              <th>Origen</th>
              <th>Verificación</th>
              <th>Duplicados</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-neutral-500">
                  No hay noticias todavía. Registra fuentes y el sistema propondrá candidatas.
                </td>
              </tr>
            )}
            {shown.map((s) => (
              <tr key={s.id} className="hover:bg-neutral-900/60">
                <td className="max-w-96">
                  <Link href={`/noticias/${s.id}`} className="font-medium hover:text-sky-400">
                    {s.title}
                  </Link>
                  {s.is_opinion && <span className="badge-warn ml-2">Opinión</span>}
                  {s.unverified_claims ? (
                    <span className="badge-warn ml-2" title="Afirmaciones sin respaldo suficiente">
                      {s.unverified_claims} sin verificar
                    </span>
                  ) : null}
                  <div className="mt-0.5 line-clamp-2 text-xs text-neutral-500">{s.summary}</div>
                </td>
                <td className="whitespace-nowrap text-neutral-400">
                  {s.original_event_date ? (
                    <span title="Fecha del acontecimiento">{fmtDate(s.original_event_date)}</span>
                  ) : (
                    <span className="text-neutral-600" title="No consta la fecha del acontecimiento">
                      sin fecha
                    </span>
                  )}
                </td>
                <td>
                  <span className={STATUS_BADGE[s.status] || "badge-neutral"}>{s.status_label}</span>
                </td>
                <td className="tabular-nums text-neutral-300">{s.editorial_score ?? "—"}</td>
                <td className="text-neutral-400">{s.source_count ?? "—"}</td>
                <td>
                  {!s.claim_count ? (
                    <span className="badge-neutral" title="No hay afirmaciones que comprobar">
                      Sin afirmaciones
                    </span>
                  ) : s.unverified_claims ? (
                    <span className="badge-warn">Parcial</span>
                  ) : (
                    <span className="badge-ok">Sin huecos</span>
                  )}
                </td>
                <td>
                  {s.possible_duplicates && s.possible_duplicates.length > 0 ? (
                    <details className="relative">
                      <summary className="badge-warn cursor-pointer">
                        {s.possible_duplicates.length} posible(s)
                      </summary>
                      <ul className="absolute z-10 mt-1 w-72 rounded border border-neutral-700 bg-neutral-900 p-2 text-xs text-neutral-300 shadow-lg">
                        {s.possible_duplicates.map((d) => (
                          <li key={d.story_id} className="mb-1">
                            <Link href={`/noticias/${d.story_id}`} className="text-sky-400 hover:underline">
                              {d.title}
                            </Link>
                            <span className="block text-neutral-500">{d.reason}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : (
                    <span className="text-neutral-600">—</span>
                  )}
                </td>
                <td>
                  <div className="flex flex-wrap gap-1">
                    <button className="btn px-2 py-1 text-xs" onClick={() => act(s, "research")}>
                      Investigar
                    </button>
                    <Link href={`/noticias/${s.id}`} className="btn px-2 py-1 text-xs">
                      Abrir
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-neutral-500">
        Última actualización: {fmtDate(new Date().toISOString())}. La puntuación es orientativa; la aprobación
        siempre es humana.
      </p>
    </div>
  );
}
