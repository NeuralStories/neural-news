/**
 * Marcador de carga reutilizable (NN-113.1).
 *
 * Esqueleto con la forma del contenido que va a aparecer, con las clases del
 * sistema: sin spinners y sin animación.
 */
export default function MarcadorCarga({
  filas = 3,
  etiqueta = "Cargando…",
}: {
  filas?: number;
  etiqueta?: string;
}) {
  return (
    <div className="ops-panel-body" role="status" aria-live="polite">
      <p className="ops-panel-title">{etiqueta}</p>
      <div className="mt-2 flex flex-col gap-1.5">
        {Array.from({ length: filas }).map((_, indice) => (
          <span
            key={indice}
            className={`esqueleto block ${indice === 0 ? "h-5 w-1/3" : "h-3 w-full"}`}
          />
        ))}
      </div>
    </div>
  );
}
