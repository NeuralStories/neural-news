"use client";

/**
 * Operación (NN-115.1): lo que el operador necesita para saber si el sistema
 * está vivo y qué está fallando.
 *
 * Antes, los endpoints `/api/v1/jobs`, `/usage` y `/provider-status` existían
 * pero **no había ninguna página** que los mostrara: había que consultar la
 * API a mano para saber por qué un trabajo había fallado.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Estado = "cargando" | "listo" | "error";

export default function OperacionPage() {
  const [salud, setSalud] = useState<Awaited<ReturnType<typeof api.health>> | null>(null);
  const [trabajos, setTrabajos] = useState<Array<Record<string, unknown>>>([]);
  const [uso, setUso] = useState<Record<string, unknown> | null>(null);
  const [proveedores, setProveedores] = useState<Awaited<ReturnType<typeof api.providerStatus>> | null>(null);
  const [estado, setEstado] = useState<Estado>("cargando");
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    setEstado("cargando");
    try {
      const [s, j, u, p] = await Promise.all([
        api.health(),
        api.listJobs(),
        api.usage(),
        api.providerStatus(),
      ]);
      setSalud(s);
      setTrabajos(j.items as unknown as Array<Record<string, unknown>>);
      setUso(u as unknown as Record<string, unknown>);
      setProveedores(p);
      setError(null);
      setEstado("listo");
    } catch (e) {
      setError((e as Error).message);
      setEstado("error");
    }
  };

  useEffect(() => {
    void cargar();
    const t = setInterval(() => void cargar(), 15_000);
    return () => clearInterval(t);
  }, []);

  if (estado === "cargando" && !salud) {
    return <p className="p-6 text-sm text-neutral-500">Cargando el estado del sistema…</p>;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold text-neutral-100">Operación</h1>
        <button className="btn" onClick={() => void cargar()}>
          Actualizar
        </button>
      </header>

      {error ? (
        <p className="text-sm text-red-400" role="alert">
          No se ha podido leer el estado: {error}
        </p>
      ) : null}

      {salud ? (
        <section className="card space-y-2">
          <h2 className="text-sm font-semibold text-neutral-300">Dependencias</h2>
          <p className="text-xs text-neutral-500">
            {salud.app} v{salud.version} · entorno {salud.env} ·{" "}
            {salud.demo_mode ? "modo demo (servicios de pago bloqueados)" : "servicios de pago activos"}
          </p>
          <ul className="space-y-1 text-sm">
            {Object.entries(salud.checks).map(([nombre, check]) => (
              <li key={nombre} className="flex flex-wrap items-baseline gap-2">
                <span className={check.ok ? "badge-ok" : "badge-err"}>
                  {check.ok ? "OK" : "FALLA"}
                </span>
                <span className="text-neutral-300">{nombre}</span>
                <span className="text-xs text-neutral-500">{check.detalle}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {uso ? (
        <section className="card space-y-2">
          <h2 className="text-sm font-semibold text-neutral-300">Consumo de hoy</h2>
          <p className="text-sm text-neutral-400">
            {String(uso.today_calls ?? 0)} llamadas · {String(uso.today_blocked ?? 0)} bloqueadas por
            presupuesto · {Number(uso.today_spent_eur ?? 0).toFixed(4)} € consumidos
          </p>
        </section>
      ) : null}

      {proveedores ? (
        <section className="card space-y-2">
          <h2 className="text-sm font-semibold text-neutral-300">Proveedores</h2>
          <ul className="space-y-1 text-sm">
            {proveedores.providers.map((p) => (
              <li key={p.key} className="flex flex-wrap items-baseline gap-2">
                <span className={p.configured ? "badge-ok" : "badge-neutral"}>
                  {p.configured ? "configurado" : "sin clave"}
                </span>
                <span className="text-neutral-300">{p.name}</span>
                <span className="text-xs text-neutral-500">{p.note}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="card space-y-2">
        <h2 className="text-sm font-semibold text-neutral-300">Trabajos recientes</h2>
        {trabajos.length === 0 ? (
          <p className="text-sm text-neutral-500">Todavía no hay trabajos.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-neutral-500">
                <tr>
                  <th className="py-1 pr-3">#</th>
                  <th className="py-1 pr-3">Tipo</th>
                  <th className="py-1 pr-3">Estado</th>
                  <th className="py-1 pr-3">Motivo</th>
                  <th className="py-1 pr-3">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {trabajos.map((t) => (
                  <tr key={String(t.id)} className="border-t border-neutral-900">
                    <td className="py-1 pr-3 text-neutral-500">{String(t.id)}</td>
                    <td className="py-1 pr-3 text-neutral-300">{String(t.type)}</td>
                    <td className="py-1 pr-3">
                      <span
                        className={
                          t.status === "DONE"
                            ? "badge-ok"
                            : t.status === "QUEUED" || t.status === "RUNNING"
                              ? "badge-info"
                              : "badge-err"
                        }
                      >
                        {String(t.status_label ?? t.status)}
                      </span>
                    </td>
                    <td className="py-1 pr-3 text-neutral-400">
                      {t.error_kind_label ? String(t.error_kind_label) : "—"}
                    </td>
                    <td className="py-1 pr-3 text-xs text-neutral-500">
                      {t.error ? String(t.error) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
