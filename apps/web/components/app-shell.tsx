"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { VERSION } from "@/lib/version";
import type { Me } from "@/lib/types";
import { IconoLuna, IconoSol } from "@/components/ui/icono";
import { aplicarSkin, skinGuardado, SKINS, type Skin } from "@/lib/apariencia";

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
  const [tema, setTema] = useState<"oscuro" | "claro">("oscuro");
  const [skin, setSkin] = useState<Skin>("base");

  /*
   * Tema: los tokens de `globals.css` tienen dos bases (oscura y clara) y el
   * conmutador sólo cambia el atributo `data-tema` de `<html>`. El atributo lo
   * pone un script en línea de `layout.tsx` **antes del primer pintado** (si
   * no, habría un destello del tema oscuro al cargar en modo claro).
   *
   * Skin: mismo mecanismo con `data-skin` (`lib/apariencia.ts`); aquí sólo se
   * sincroniza el estado inicial —el script en línea ya aplicó el guardado— y
   * se aplica en caliente al cambiar el selector.
   */
  useEffect(() => {
    setTema(document.documentElement.dataset.tema === "claro" ? "claro" : "oscuro");
    setSkin(skinGuardado());
  }, []);

  const cambiarSkin = (siguiente: Skin) => {
    aplicarSkin(siguiente);
    setSkin(siguiente);
  };

  const alternarTema = () => {
    const siguiente = tema === "oscuro" ? "claro" : "oscuro";
    document.documentElement.dataset.tema = siguiente;
    try {
      window.localStorage.setItem("neural.tema", siguiente);
    } catch {
      /* almacenamiento no disponible: el tema dura lo que dura la pestaña */
    }
    setTema(siguiente);
  };

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
    return <div className="flex min-h-screen items-center justify-center text-ink-3">Cargando…</div>;
  }

  const isPublic = pathname === "/";
  const showDemoBadge = me?.is_demo || me?.demo_mode;
  const ancho = pathname.startsWith("/ops") ? "max-w-[1680px]" : "max-w-6xl";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-bg/90 backdrop-blur">
        {/* La cabecera comparte el ancho del contenido: en /ops la consola
            mide 1680 px y los bordes de la marca y los controles deben
            alinear con los bordes de la rejilla (antes quedaba a 6xl). */}
        <div className={`mx-auto flex ${ancho} flex-wrap items-center gap-3 px-4 py-3`}>
          <Link href="/fuentes" className="text-lg font-semibold tracking-tight">
            neural<span className="text-info">.news</span>
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
                      ? "bg-surface-3 text-ink"
                      : "text-ink-2 hover:bg-surface-2 hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            {!isPublic && me && (
              <button onClick={logout} className="ml-2 text-ink-3 hover:text-ink">
                Salir
              </button>
            )}
            <select
              className="selector-skin"
              value={skin}
              onChange={(evento) => cambiarSkin(evento.target.value as Skin)}
              aria-label="Skin de la interfaz"
              title="Skin de la interfaz"
            >
              {SKINS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nombre}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={alternarTema}
              className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded-md border border-line bg-surface-2 text-ink-2 transition hover:bg-surface-3 hover:text-ink active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info/60"
              title={tema === "oscuro" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
              aria-label={tema === "oscuro" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
            >
              {tema === "oscuro" ? <IconoSol /> : <IconoLuna />}
            </button>
          </nav>
        </div>
      </header>
      {/* La consola de operación necesita más ancho que el resto del producto
          (tabla de trabajos + panel lateral): el contenedor se ensancha sólo
          en esa vista. */}
      <main className={`mx-auto px-4 py-4 ${ancho}`}>{children}</main>
      <footer className={`mx-auto px-4 pb-8 pt-2 text-xs text-ink-3 ${ancho}`}>
        neural.news v{VERSION} · el contenido de las fuentes es dato de trabajo; la aprobación de
        guiones es siempre humana.
      </footer>
    </div>
  );
}
