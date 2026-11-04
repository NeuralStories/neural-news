"use client";

/**
 * Apariencia: skins de la consola (capas de tokens sobre `globals.css`).
 *
 * Un skin es un intercambio de variables CSS (`data-skin` sobre `<html>`):
 * superficies, líneas, acentos, radios y pilas tipográficas. La semántica de
 * los acentos (ok/warn/crit/info/idle) es idéntica en todos; sólo cambia la
 * familia de tono.
 *
 * Persistencia: `localStorage["neural.skin"]`. El atributo lo pone el script
 * en línea de `layout.tsx` **antes del primer pintado** (sin destello), igual
 * que `data-tema`; aquí sólo se lee/escribe y se aplica en caliente cuando el
 * operador cambia de skin con la app abierta.
 */

export type Skin = "base" | "slate" | "papel" | "fosforo" | "carbon" | "plex";

export type SkinInfo = {
  id: Skin;
  nombre: string;
  /** Una línea: qué cambia respecto a la base. */
  descripcion: string;
};

/** Catálogo del selector: el orden es el de la interfaz. */
export const SKINS: SkinInfo[] = [
  {
    id: "base",
    nombre: "Industrial (base)",
    descripcion: "Zinc casi negro, radios 4 px, Inter + JetBrains Mono.",
  },
  {
    id: "slate",
    nombre: "Slate frío",
    descripcion: "Neutros azules de sala de control; mismo ritmo que la base.",
  },
  {
    id: "papel",
    nombre: "Papel técnico",
    descripcion: "Documento impreso: papiro cálido y tipografía IBM Plex.",
  },
  {
    id: "fosforo",
    nombre: "Fósforo",
    descripcion: "Terminal de telemetría: verdor CRT y todo monoespaciado.",
  },
  {
    id: "carbon",
    nombre: "Carbón",
    descripcion: "Negro puro, radios 2 px y máxima densidad de fila.",
  },
  {
    id: "plex",
    nombre: "Plex cuadrado",
    descripcion: "IBM Carbon: radios 0, acento azul y trazo cuadrado.",
  },
];

const CLAVE = "neural.skin";

/** Skin guardado (o el de la base). Ignora valores que ya no existen. */
export function skinGuardado(): Skin {
  try {
    const valor = localStorage.getItem(CLAVE);
    if (valor && SKINS.some((skin) => skin.id === valor)) return valor as Skin;
  } catch {
    /* almacenamiento no disponible: la skin dura lo que dura la pestaña */
  }
  return "base";
}

/**
 * Aplica el skin en caliente y lo persiste. `base` borra el atributo (vuelta
 * a los tokens por defecto) y su entrada de almacenamiento.
 */
export function aplicarSkin(skin: Skin): void {
  if (skin === "base") {
    delete document.documentElement.dataset.skin;
    try {
      localStorage.removeItem(CLAVE);
    } catch {
      /* sin persistencia: se acepta */
    }
    return;
  }
  document.documentElement.dataset.skin = skin;
  try {
    localStorage.setItem(CLAVE, skin);
  } catch {
    /* sin persistencia: se acepta */
  }
}
