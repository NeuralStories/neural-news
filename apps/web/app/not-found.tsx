import Link from "next/link";

/** Página no encontrada (NN-113.1). */
export default function NoEncontrado() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold text-neutral-100">No hay nada por aquí</h1>
      <p className="text-sm text-neutral-400">
        La página que buscas no existe o ha cambiado de sitio.
      </p>
      <Link className="btn-primary" href="/">
        Volver al inicio
      </Link>
    </main>
  );
}
