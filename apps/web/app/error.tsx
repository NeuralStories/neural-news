"use client";

/**
 * Frontera de error de la aplicación (NN-113.1).
 *
 * Antes, un error de render dejaba la pantalla **en blanco**: el usuario veía
 * una página vacía sin saber qué pasó ni cómo reintentar. Esta frontera
 * muestra qué ha ocurrido y ofrece reintentar sin recargar a mano.
 */
import { useEffect } from "react";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // El detalle técnico va al registro del navegador; la interfaz habla claro.
    console.error("[neural.news] error de render", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold text-neutral-100">
        Esta sección no se ha podido mostrar
      </h1>
      <p className="text-sm text-neutral-400">
        Ha ocurrido un error al pintar la página. Tus datos están guardados: puedes reintentar
        sin perder el trabajo.
      </p>
      {error.digest ? (
        <p className="text-xs text-neutral-500">Referencia: {error.digest}</p>
      ) : null}
      <div className="flex gap-2">
        <button className="btn-primary" onClick={() => reset()}>
          Reintentar
        </button>
        <a className="btn" href="/">
          Volver al inicio
        </a>
      </div>
    </main>
  );
}
