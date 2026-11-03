import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import CargaFuenteIconos from "@/components/carga-fuente-iconos";

export const metadata: Metadata = {
  title: "neural.news",
  description: "Investigación y producción editorial sobre inteligencia artificial",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-ES">
      <head>
        {/*
          Tema claro/oscuro: el atributo `data-tema` de `<html>` tiene que estar
          **antes del primer pintado**. Si se pusiera desde React, la página se
          pintaría primero en oscuro y luego saltaría a claro (destello). Este
          script es síncrono y va en la cabecera, que es donde el navegador lo
          ejecuta antes de dibujar el cuerpo.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('neural.tema');" +
              "if(t==='claro'){document.documentElement.dataset.tema='claro';}}catch(e){}",
          }}
        />
        {/*
          Iconos del Studio (Material Symbols).

          Antes era un `<link>` normal a Google Fonts: una petición **bloqueante**
          a un tercero en cada carga (NN-113.10). Se carga sin bloquear el
          render y con `display=optional`: si Google no responde, la página se
          ve igual y sólo faltan los iconos.

          La alternativa —alojar la variable en el repo— pesaba **4 MB** por
          archivo, así que queda anotada en «Ideas fuera de alcance» en vez de
          meterse en el repositorio.
        */}
        <CargaFuenteIconos href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=optional" />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
