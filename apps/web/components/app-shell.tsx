"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

const NAV = [
  { href: "/fuentes", label: "Fuentes" },
  { href: "/noticias", label: "Noticias" },
  { href: "/estudio", label: "Estudio" },
  { href: "/lotes", label: "Lotes" },
  { href: "/ops", label: "Operación" },
  { href: "/configuracion", label: "Configuración" },
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
    return <div className="flex min-h-screen items-center justify-center text-neutral-500">Cargando…</div>;
  }

  const isPublic = pathname === "/";
  const showDemoBadge = me?.is_demo || me?.demo_mode;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-neutral-800 bg-neutral-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <Link href="/fuentes" className="text-lg font-semibold tracking-tight">
            neural<span className="text-sky-400">.news</span>
          </Link>
          {showDemoBadge && (
            <span className="badge-demo" title="Los datos y la evidencia son ficticios; no se llama a servicios externos">
              DEMO
            </span>
          )}
          <nav className="ml-auto flex flex-wrap items-center gap-1 text-sm">
            {!isPublic &&
              NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-1.5 transition ${
                    pathname.startsWith(item.href)
                      ? "bg-neutral-800 text-neutral-100"
                      : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            {!isPublic && me && (
              <button onClick={logout} className="ml-2 text-neutral-500 hover:text-neutral-300">
                Salir
              </button>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 pb-8 pt-2 text-xs text-neutral-600">
        neural.news MVP · el contenido de las fuentes es dato de trabajo; la aprobación de guiones es siempre humana.
      </footer>
    </div>
  );
}
