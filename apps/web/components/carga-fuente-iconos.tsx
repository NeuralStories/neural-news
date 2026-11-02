"use client";

/**
 * Carga **sin bloquear** la hoja de la fuente de iconos (NN-113.10).
 *
 * Va en un componente cliente a propósito: el evento `onLoad` es un manejador
 * de React y los Server Components no admiten manejadores de eventos.
 *
 * Antes era un `<link>` normal a Google Fonts: bloqueaba el render en cada
 * carga. Con `media="print"` la hoja no se aplica al pintar; al terminar de
 * descargarse se cambia a `all` y los iconos aparecen.
 */
export default function CargaFuenteIconos({ href }: { href: string }) {
  return (
    <link
      rel="stylesheet"
      href={href}
      media="print"
      onLoad={(e) => {
        e.currentTarget.media = "all";
      }}
    />
  );
}
