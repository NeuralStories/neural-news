"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, useJobPolling } from "@/lib/hooks";
import type { StoryListItem, StoryListResponse } from "@/lib/types";

type Vista = "atencion" | "aprobar" | "aprobadas" | "todas";

const VISTAS: { id: Vista; label: string; hint: string }[] = [
  { id: "atencion", label: "Requieren atención", hint: "bloqueadas o sin terminar" },
  { id: "aprobar", label: "Listas para aprobar", hint: "guion pendiente de aprobación" },
  { id: "aprobadas", label: "Aprobadas", hint: "con guion aprobado" },
  { id: "todas", label: "Todas", hint: "todas las noticias" },
];

/**
 * Bandeja editorial: cada noticia dice qué le falta y cuál es la acción segura.
 * Los filtros, el orden y la paginación se resuelven en el servidor (la API
 * devuelve total, limit, offset y recuentos); la web no filtra sobre un recorte.
 */
export default function NoticiasPage() {
  const [data, setData] = useState<StoryListResponse>({
    total: 0,
    limit: 25,
    offset: 0,
    items: [],
    counts: { all: 0, attention: 0, to_approve: 0, approved: 0 },
  });
  const [vista, setVista] = useState<Vista>("atencion");
  const [stage, setStage] = useState<string>("todos");
  const [verification, setVerification] = useState<string>("todos");
  const [origin, setOrigin] = useState<string>("todos");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const { waiting, poll } = useJobPolling();

  const limit = 25;

  const refresh = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      // La búsqueda es transversal: si hay texto, se busca en TODAS las noticias
      // (una vista activa no debe impedir encontrar una noticia concreta).
      const searching = q.trim().length > 0;
      if (!searching) {
        if (vista === "atencion") params.set("attention", "true");
        if (vista === "aprobar") params.set("stage", "script");
        if (vista === "aprobadas") params.set("approval", "approved");
      }
      if (stage !== "todos") params.set("stage", stage);
      if (verification !== "todos") params.set("verification", verification);
      if (origin !== "todos") params.set("origin", origin);
      if (searching) params.set("q", q.trim());
      params.set("limit", String(limit));
      params.set("offset", String(page * limit));
      const response = await api.listStories(params.toString());
      setData(response);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [vista, stage, verification, origin, q, page]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const act = async (story: StoryListItem) => {
    try {
      const res = await api.research(story.id);
      await poll(res.job_id, refresh);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const counts = data.counts;
  const shown = data.items;
  const totalPages = Math.max(1, Math.ceil(data.total / limit));

  const nextAction = (s: StoryListItem) => {
    if (s.stage === "rejected") return null;
    if (s.stage === "candidate" || s.stage === "research") {
      return {
        kind: "research" as const,
        label: s.stage === "research" ? "Investigando…" : "Investigar",
        disabled: s.stage === "research",
      };
    }
    if (s.stage === "script") {
      return { kind: "link" as const, label: "Aprobar guion", href: `/noticias/${s.id}` };
    }
    if (s.approval === "approved") {
      return { kind: "link" as const, label: "Preparar traspaso", href: `/noticias/${s.id}` };
    }
    return { kind: "link" as const, label: "Abrir", href: `/noticias/${s.id}` };
  };

  const reason = (s: StoryListItem): string | null => {
    if (s.stage === "rejected") return "Descartada: no genera producción.";
    if (s.production_blockers.length > 0) return s.production_blockers[0];
    if (s.approval !== "approved") return "Sin aprobación humana del guion.";
    if (s.production_warnings.length > 0) return "Aprobada con revisión pendiente.";
    return null;
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">
          Noticias{" "}
          <span className="text-sm font-normal text-[#6b7a90]">
            paso 2: revisa la evidencia y aprueba el guion antes de producir
          </span>
        </h1>
        <input
          className="input max-w-64"
          placeholder="Buscar por tema o resumen…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(0);
          }}
          aria-label="Buscar noticias"
        />
      </div>

      {/* Vistas rápidas: cada una es un estado real de la lista */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Vistas rápidas de noticias">
        {VISTAS.map((v) => {
          const count =
            v.id === "atencion"
              ? counts.attention
              : v.id === "aprobar"
                ? counts.to_approve
                : v.id === "aprobadas"
                  ? counts.approved
                  : counts.all;
          const active = vista === v.id;
          return (
            <button
              key={v.id}
              onClick={() => {
                setVista(v.id);
                setPage(0);
              }}
              aria-pressed={active}
              className={`rounded-lg border px-3 py-2 text-left transition ${
                active
                  ? "border-sky-700 bg-sky-950/60 ring-1 ring-sky-800"
                  : "border-slate-800 bg-slate-900/60 hover:border-slate-600"
              }`}
            >
              <span className="block text-xs text-slate-400">{v.label}</span>
              <span className="block text-xl font-semibold tabular-nums text-slate-100">{count}</span>
              <span className="block text-[11px] text-[#6b7a90]">{v.hint}</span>
            </button>
          );
        })}
      </div>

      {/* Filtros por dimensión */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-[#6b7a90]">Etapa:</span>
        {[
          ["todos", "Todas"],
          ["candidate", "Candidata"],
          ["research", "Investigación"],
          ["script", "Guion"],
          ["approved", "Aprobada"],
        ].map(([id, label]) => (
          <FilterChip key={id} active={stage === id} onClick={() => { setStage(id); setPage(0); }} label={label} />
        ))}
        <span className="ml-2 text-[#6b7a90]">Verificación:</span>
        {[
          ["todos", "Todas"],
          ["in_review", "En revisión"],
          ["verified", "Verificada"],
          ["disputed", "Con contradicciones"],
          ["opinion", "No verificable"],
        ].map(([id, label]) => (
          <FilterChip key={id} active={verification === id} onClick={() => { setVerification(id); setPage(0); }} label={label} />
        ))}
        <span className="ml-2 text-[#6b7a90]">Origen:</span>
        {[
          ["todos", "Todos"],
          ["real", "Real"],
          ["demo", "DEMO"],
          ["manual", "Manual"],
          ["unknown", "No determinado"],
        ].map(([id, label]) => (
          <FilterChip key={id} active={origin === id} onClick={() => { setOrigin(id); setPage(0); }} label={label} />
        ))}
      </div>

      {q.trim() && (
        <p className="text-xs text-slate-400">
          Buscando en todas las noticias («{q.trim()}»): {data.total} resultado(s).
        </p>
      )}

      {error && (
        <p className="notice-err" role="alert">
          {error}
        </p>
      )}
      {waiting !== null && (
        <p className="notice-info" role="status">
          Trabajo #{waiting} en marcha…
        </p>
      )}

      {shown.length === 0 ? (
        <div className="empty-state">
          {data.total === 0 && counts.all === 0
            ? "No hay noticias todavía. Registra fuentes y el sistema propondrá candidatas."
            : "Ninguna noticia coincide con esta vista."}
        </div>
      ) : (
        <ul className="space-y-2">
          {shown.map((s) => {
            const action = nextAction(s);
            const motivo = reason(s);
            return (
              <li
                key={s.id}
                className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 transition hover:border-slate-700"
              >
                <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
                  <span
                    className={`mt-0.5 shrink-0 text-[11px] font-semibold uppercase tracking-wide ${
                      motivo ? "text-amber-400" : "text-emerald-400"
                    }`}
                  >
                    {motivo ? "Necesita atención" : "En curso"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <Link href={`/noticias/${s.id}`} className="font-medium text-slate-100 hover:text-sky-400">
                      {s.title}
                    </Link>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#6b7a90]">
                      <span>{s.stage_label}</span>
                      <span>{s.verification_label}</span>
                      <span>
                        {s.claim_total === 0
                          ? "Sin afirmaciones"
                          : `${s.claim_verified} de ${s.claim_total} afirmaciones verificadas`}
                      </span>
                      {s.source_count > 0 && <span>{s.source_count} fuente(s)</span>}
                      <span>{s.origin_label}</span>
                      {s.latest_version !== null && <span>Guion v{s.latest_version}</span>}
                      {s.original_event_date && <span>{fmtDate(s.original_event_date)}</span>}
                      {s.possible_duplicates.length > 0 && (
                        <span className="text-amber-400">
                          {s.possible_duplicates.length} posible(s) duplicado(s)
                        </span>
                      )}
                    </div>
                    {motivo && <p className="mt-1 text-xs text-amber-300">{motivo}</p>}
                    {s.production_warnings.length > 0 && (
                      <p className="mt-1 text-xs text-sky-300">{s.production_warnings[0]}</p>
                    )}
                    {s.summary && (
                      <p className="mt-1 line-clamp-2 text-xs text-slate-400">{s.summary}</p>
                    )}
                  </div>
                  {action && (
                    <div className="flex shrink-0 flex-wrap items-center gap-1">
                      {action.kind === "research" ? (
                        <button
                          className="btn-xs-primary"
                          onClick={() => act(s)}
                          disabled={action.disabled}
                        >
                          {action.label}
                        </button>
                      ) : (
                        <Link href={action.href} className="btn-xs-primary">
                          {action.label}
                        </Link>
                      )}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Paginación en servidor */}
      {data.total > limit && (
        <nav className="flex items-center justify-between gap-2 text-sm" aria-label="Paginación de noticias">
          <button
            className="btn-xs"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            ← Anteriores
          </button>
          <span className="text-xs text-slate-400">
            Página {page + 1} de {totalPages} · {data.total} resultado(s)
          </span>
          <button
            className="btn-xs"
            onClick={() => setPage((p) => (p + 1 < totalPages ? p + 1 : p))}
            disabled={page + 1 >= totalPages}
          >
            Siguientes →
          </button>
        </nav>
      )}

      <p className="text-xs text-[#6b7a90]">
        La puntuación es orientativa; la aprobación siempre es humana. Etapa, verificación, aprobación y
        origen son dimensiones independientes: una noticia puede estar «en guion» y seguir sin verificar.
      </p>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`min-h-8 rounded-full px-3 transition ${
        active
          ? "bg-sky-950/80 text-sky-200 ring-1 ring-sky-800"
          : "bg-slate-900 text-slate-400 ring-1 ring-slate-800 hover:text-slate-200"
      }`}
    >
      {label}
    </button>
  );
}
