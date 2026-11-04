/**
 * Estado de carga global (NN-113.1): la interfaz nunca aparece vacía.
 *
 * El esqueleto tiene la forma del contenido real (panel + bloques) y usa las
 * clases del sistema: sin spinners y sin destellos.
 */
export default function Cargando() {
  return (
    <main className="mx-auto w-full max-w-[1680px] px-4 py-4">
      <div className="ops-panel">
        <div className="ops-panel-head">
          <span className="esqueleto h-2 w-40" />
        </div>
        <div className="ops-panel-body grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
          {Array.from({ length: 8 }).map((_, indice) => (
            <div key={indice} className="metrica">
              <span className="esqueleto block h-2 w-16" />
              <span className="esqueleto mt-2 block h-5 w-12" />
            </div>
          ))}
        </div>
      </div>
      <span className="sr-only">Cargando…</span>
    </main>
  );
}
