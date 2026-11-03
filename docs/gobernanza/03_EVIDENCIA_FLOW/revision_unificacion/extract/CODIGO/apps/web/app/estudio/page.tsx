"use client";

import { useEffect, useState } from "react";

/**
 * Estudio dentro de la aplicación única.
 *
 * El build del Studio se publica en `apps/web/public/studio-app` (base
 * `/studio-app/`), de modo que se sirve desde el MISMO origen que neural.news:
 * una sola URL, una sola cookie de sesión y ninguna dependencia de un segundo
 * servidor. El modo independiente (`npm run dev` en apps/studio) se conserva
 * para desarrollo.
 *
 * Además, si la URL trae `?story=<id>&revision=<n>`, el estudio carga ese
 * traspaso directamente del motor: no hay que copiar ningún JSON a mano.
 */
const STUDIO_PATH = "/studio/index.html";

export default function EstudioPage() {
  const [ready, setReady] = useState(false);
  const [section, setSection] = useState("Noticias");

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data as { type?: string; tab?: string };
      if (data?.type === "nn-studio-tab" && typeof data.tab === "string") {
        setSection(data.tab);
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  // Se conserva el deep-link hacia una noticia concreta.
  const params = new URLSearchParams(
    typeof window === "undefined" ? "" : window.location.search
  );
  const storyId = params.get("story");
  const revision = params.get("revision");
  const src =
    STUDIO_PATH +
    (storyId
      ? `?embed=1&story=${encodeURIComponent(storyId)}${revision ? `&revision=${encodeURIComponent(revision)}` : ""}`
      : "?embed=1");

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">
          Estudio audiovisual{" "}
          <span className="text-sm font-normal text-[#6b7a90]">
            paso 3 del flujo · sección activa: {section}
          </span>
        </h1>
        {storyId && (
          <span className="badge-info">
            Noticia {storyId}
            {revision ? ` · revisión ${revision}` : ""}
          </span>
        )}
      </div>

      <div className="relative overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
        {!ready && (
          <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-slate-400">
            Cargando el estudio…
          </div>
        )}
        <iframe
          src={src}
          title="NeuralStories Studio: preparación audiovisual de las noticias"
          className="block h-[calc(100vh-190px)] min-h-[560px] w-full"
          style={{ border: 0 }}
          onLoad={() => setReady(true)}
        />
      </div>
      <p className="hint">
        El estudio se sirve desde esta misma aplicación (sin segundo servidor ni otra cookie). La preparación
        de escenas es siempre editable y la aprobación editorial sigue siendo humana.
      </p>
    </div>
  );
}
