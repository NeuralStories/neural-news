"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

const NAV = [
  {
    href: "/fuentes",
    label: "Fuentes",
    step: "1",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden className="h-4 w-4">
        <path d="M10 2a4 4 0 0 0-4 4v1H5a1 1 0 0 0-1 1v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8a1 1 0 0 0-1-1h-1V6a4 4 0 0 0-4-4Zm-2 5V6a2 2 0 1 1 4 0v1H8Z" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: "/noticias",
    label: "Noticias",
    step: "2",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden className="h-4 w-4">
        <path d="M3 4.5A1.5 1.5 0 0 1 4.5 3h8A1.5 1.5 0 0 1 14 4.5V6h1.5A1.5 1.5 0 0 1 17 7.5v8a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 15.5v-11Zm2 1.5v3h7V6H5Zm0 5v1h7v-1H5Zm0 3v1h7v-1H5Z" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: "/estudio",
    label: "Estudio",
    step: "3",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden className="h-4 w-4">
        <path d="M10 2 3 6v8l7 4 7-4V6l-7-4Zm0 2.3 4.8 2.7L10 9.7 5.2 7 10 4.3ZM5 8.7l4 2.3v4.7l-4-2.3V8.7Zm6 7v-4.7l4-2.3v4.7l-4 2.3Z" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: "/lotes",
    label: "Lotes",
    step: "4",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden className="h-4 w-4">
        <path d="M3 5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5Zm6 8a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2ZM3 13a2 2 0 0 1 2-2h2v2a2 2 0 0 0 2 2v2H5a2 2 0 0 1-2-2v-2Z" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: "/configuracion",
    label: "Configuración",
    step: "5",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden className="h-4 w-4">
        <path d="M10 6.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm-7.4 5 .9 1.6-.7 1.9a1 1 0 0 0 .2 1l1.4 1.4a1 1 0 0 0 1 .2l1.9-.7 1.6.9.7 1.8h2l.7-1.8 1.6-.9 1.9.7a1 1 0 0 0 1-.2l1.4-1.4a1 1 0 0 0 .2-1l-.7-1.9.9-1.6 1.8-.7v-2l-1.8-.7-.9-1.6.7-1.9a1 1 0 0 0-.2-1L16 1.7a1 1 0 0 0-1-.2l-1.9.7-1.6-.9L10.8-.5h-2L8.1 1.3l-1.6.9-1.9-.7a1 1 0 0 0-1 .2L2.2 3.1a1 1 0 0 0-.2 1l.7 1.9-.9 1.6L0 8.3v2l1.8.7Z" fill="currentColor" />
      </svg>
    ),
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (pathname === "/") {
      setChecked(true);
      return;
    }
    api
      .me()
      .then(setMe)
      .catch(() => router.replace("/"))
      .finally(() => setChecked(true));
  }, [pathname, router]);

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      setMe(null);
      router.replace("/");
    }
  };

  if (!checked) {
    return <div className="flex min-h-screen items-center justify-center text-[#6b7a90]">Cargando…</div>;
  }

  const isPublic = pathname === "/";
  const showDemoBadge = me?.is_demo || me?.demo_mode;

  return (
    <div className="min-h-screen">
      {/* Skip-link: permite saltar al contenido sin recorrer la navegación */}
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-sky-600 focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-slate-950"
      >
        Saltar al contenido
      </a>
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-2.5">
          <Link href="/fuentes" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            neural<span className="text-sky-400">.news</span>
          </Link>
          {showDemoBadge && (
            <span className="badge-demo" title="Los datos y la evidencia son ficticios; no se llama a servicios externos">
              DEMO
            </span>
          )}
          <nav aria-label="Secciones" className="ml-auto flex flex-wrap items-center gap-1 text-sm">
            {!isPublic &&
              NAV.map((item) => {
                const active = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    title={item.label}
                    className={`flex min-h-9 items-center gap-1.5 rounded-md px-3 py-1.5 transition ${
                      active
                        ? "bg-sky-950/80 text-sky-200 ring-1 ring-sky-800"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    <span className="badge-step" aria-hidden>
                      {item.step}
                    </span>
                    {item.icon}
                    <span className="hidden sm:inline">{item.label}</span>
                  </Link>
                );
              })}
            {!isPublic && me && (
              <button onClick={logout} className="btn-ghost !min-h-9 ml-1">
                Salir
              </button>
            )}
          </nav>
        </div>
      </header>
      <main id="contenido" className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 pb-8 pt-2 text-xs text-slate-600">
        neural.news MVP · el contenido de las fuentes es dato de trabajo; la aprobación de guiones es siempre humana.
      </footer>
    </div>
  );
}
