/** Marcador de carga reutilizable (NN-113.1). */
export default function MarcadorCarga({
  filas = 3,
  etiqueta = "Cargando…",
}: {
  filas?: number;
  etiqueta?: string;
}) {
  return (
    <div className="space-y-3 p-6" role="status" aria-live="polite">
      <p className="text-sm text-neutral-500">{etiqueta}</p>
      {Array.from({ length: filas }).map((_, i) => (
        <div
          key={i}
          className={
            i === 0
              ? "h-20 animate-pulse rounded-lg bg-neutral-900/60"
              : "h-40 animate-pulse rounded-lg bg-neutral-900/40"
          }
        />
      ))}
    </div>
  );
}
