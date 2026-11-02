/** Estado de carga global (NN-113.1): la interfaz nunca aparece vacía. */
export default function Cargando() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-3 p-6">
      <p className="text-sm text-neutral-500">Cargando…</p>
      <div className="h-24 animate-pulse rounded-lg bg-neutral-900/60" />
      <div className="h-10 animate-pulse rounded-lg bg-neutral-900/40" />
      <div className="h-40 animate-pulse rounded-lg bg-neutral-900/60" />
    </main>
  );
}
