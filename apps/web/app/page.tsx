"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const enterDemo = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.demoLogin();
      router.replace("/fuentes");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center">
      <div className="w-full max-w-sm space-y-6 text-center">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            neural<span className="text-sky-400">.news</span>
          </h1>
          <p className="mt-2 text-sm text-neutral-400">
            Investigación y producción editorial sobre inteligencia artificial.
          </p>
        </div>

        <button onClick={enterDemo} disabled={busy} className="btn-primary w-full py-2.5">
          {busy ? "Entrando…" : "Entrar en modo demo"}
        </button>
        <p className="text-xs leading-relaxed text-neutral-500">
          El modo demo usa contenidos y evidencia <strong>ficticios</strong> para recorrer el flujo completo sin
          claves ni llamadas externas. Nada de lo generado en demo debe publicarse como real.
        </p>
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    </div>
  );
}
