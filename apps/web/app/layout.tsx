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
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
