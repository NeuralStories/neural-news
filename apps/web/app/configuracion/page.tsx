"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ProviderStatus, UsageInfo } from "@/lib/types";

const STATE_BADGE: Record<string, { cls: string; label: string }> = {
  probado: { cls: "badge-ok", label: "Verificado" },
  implementado: { cls: "badge-info", label: "Preparado (sin validar)" },
  sin_clave: { cls: "badge-warn", label: "Falta clave" },
  mock: { cls: "badge-warn", label: "Solo demo" },
  fuera_de_mvp: { cls: "badge-neutral", label: "Fuera del MVP" },
};

export default function ConfiguracionPage() {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [dailyLimit, setDailyLimit] = useState("0");
  const [paidEnabled, setPaidEnabled] = useState(false);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [status, usageData, w] = await Promise.all([api.providerStatus(), api.usage(), api.getScoreWeights()]);
      setProviders(status.providers);
      setDemoMode(status.demo_mode);
      setPaidEnabled(usageData.budget.paid_services_enabled);
      setDailyLimit(String(usageData.budget.daily_limit_eur));
      setUsage(usageData);
      setWeights(w);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const saveBudget = async () => {
    setMsg(null);
    setError(null);
    try {
      await api.updateBudget({ paid_services_enabled: paidEnabled, daily_limit_eur: Number(dailyLimit) || 0 });
      setMsg("Presupuesto actualizado.");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const saveWeights = async () => {
    setMsg(null);
    setError(null);
    try {
      await api.updateScoreWeights(weights);
      setMsg("Puntuación actualizada.");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Configuración</h1>

      {demoMode && (
        <div className="rounded-lg border border-fuchsia-800 bg-fuchsia-950/40 p-4 text-sm">
          <span className="badge-demo mr-2">DEMO</span>
          El modo demo está activado: todos los contenidos y evidencias son ficticios y los servicios de pago
          permanecen bloqueados. Para usar proveedores reales, desactiva <code>NEURAL_DEMO_MODE</code> y añade las
          claves en el archivo <code>.env</code>.
        </div>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}
      {msg && <p className="text-sm text-emerald-400">{msg}</p>}

      <section className="card">
        <h2 className="text-sm font-semibold text-neutral-300">Proveedores conectados</h2>
        <ul className="mt-3 space-y-3">
          {providers.map((p) => {
            const badge = STATE_BADGE[p.state] || { cls: "badge-neutral", label: p.state };
            return (
              <li key={p.key} className="rounded border border-neutral-800 bg-neutral-900 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{p.name}</span>
                  <span className={badge.cls}>{badge.label}</span>
                  {p.configured && <span className="badge-neutral">clave configurada</span>}
                </div>
                <p className="mt-1 text-xs text-neutral-500">{p.note}</p>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="card space-y-3">
        <h2 className="text-sm font-semibold text-neutral-300">Límites de uso</h2>
        {usage && (
          <p className="text-xs text-neutral-500">
            Hoy: {usage.today_calls} llamadas registradas · {usage.today_blocked} bloqueadas por presupuesto ·{" "}
            {usage.today_spent_eur.toFixed(2)} € consumidos.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={paidEnabled} onChange={(e) => setPaidEnabled(e.target.checked)} />
            Servicios de pago activados
          </label>
          <label className="flex items-center gap-2">
            Presupuesto diario (€)
            <input
              type="number"
              min={0}
              step="0.5"
              className="input w-24 px-2 py-1"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(e.target.value)}
            />
          </label>
          <button className="btn-primary" onClick={saveBudget}>
            Guardar límites
          </button>
        </div>
        <p className="text-xs text-neutral-500">
          Los servicios facturables empiezan siempre desactivados. Al agotarse el presupuesto, las llamadas de pago se
          detienen y puedes seguir en modo demo o manual.
        </p>
      </section>

      <section className="card space-y-3">
        <h2 className="text-sm font-semibold text-neutral-300">Puntuación editorial (sobre 100)</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          {(["impacto", "verificacion", "novedad", "visual"] as const).map((key) => (
            <label key={key} className="flex items-center gap-2">
              <span className="capitalize">{key}</span>
              <input
                type="number"
                min={0}
                max={100}
                className="input w-20 px-2 py-1"
                value={weights[key] ?? 0}
                onChange={(e) => setWeights((w) => ({ ...w, [key]: Number(e.target.value) || 0 }))}
              />
            </label>
          ))}
          <button className="btn-primary" onClick={saveWeights}>
            Guardar pesos
          </button>
        </div>
        <p className="text-xs text-neutral-500">
          Referencia: impacto 35 · verificación 30 · novedad 20 · potencial visual 15. Es orientativa y se registra el
          desglose por noticia; ninguna nota alta aprueba automáticamente.
        </p>
      </section>
    </div>
  );
}
