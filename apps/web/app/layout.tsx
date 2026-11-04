import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "neural.news",
  description: "Investigación y producción editorial sobre inteligencia artificial",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-ES">
      <head>
        {/*
          Tema claro/oscuro y skin: los atributos `data-tema` y `data-skin` de
          `<html>` tienen que estar **antes del primer pintado**. Si se pusieran
          desde React, la página se pintaría primero con la base por defecto y
          luego saltaría (destello). Este script es síncrono y va en la
          cabecera, que es donde el navegador lo ejecuta antes de dibujar el
          cuerpo. Los valores se validan contra los skins existentes para que
          un valor viejo en almacenamiento no deje la app sin tokens.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var t=localStorage.getItem('neural.tema');" +
              "if(t==='claro'){document.documentElement.dataset.tema='claro';} " +
              "var s=localStorage.getItem('neural.skin');" +
              "if(s&&s!=='base'&&/^(slate|papel|fosforo|carbon|plex)$/.test(s))" +
              "{document.documentElement.dataset.skin=s;}}catch(e){}",
          }}
        />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
