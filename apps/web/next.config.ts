import path from "node:path";
import type { NextConfig } from "next";

/**
 * Proxy same-origin: la cookie de sesión viaja sin CORS.
 *
 * En local se puede dejar sin configurar (apunta a la API del propio equipo).
 * En cualquier otro caso la variable `NEURAL_API_URL` es OBLIGATORIA: antes el
 * destino por defecto era `http://127.0.0.1:8000` y `next build` NO fallaba
 * (los rewrites se evalúan en runtime), de modo que una instalación real se
 * quedaba sin datos y el fallo solo aparecía ya desplegada (hallazgo B9).
 *
 * Override con NEURAL_ENV=local para una instalación de escritorio en modo
 * producción (build + start en el mismo equipo).
 */
const DEFAULT_LOCAL_API = "http://127.0.0.1:8000";

function resolveApiUrl(): string {
  const configured = process.env.NEURAL_API_URL?.trim();
  const env = (process.env.NEURAL_ENV ?? "").trim().toLowerCase();
  const isLocal = env === "local" || env === "dev";

  if (isLocal) return configured?.replace(/\/$/, "") ?? DEFAULT_LOCAL_API;
  if (configured) return configured.replace(/\/$/, "");
  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "NEURAL_API_URL es obligatoria fuera del entorno local: el proxy same-origin " +
        "/api/* no puede apuntar a 127.0.0.1 en una instalación real. Define " +
        "NEURAL_API_URL (o NEURAL_ENV=local si es una instalación de escritorio).",
    );
  }
  return DEFAULT_LOCAL_API;
}

const nextConfig: NextConfig = {
  /**
   * Fija la raíz del workspace de Next.
   *
   * Sin esto, Next **infiere** la raíz buscando un `package-lock.json` hacia
   * arriba: si hay uno suelto en un directorio superior (en esta máquina, en
   * `C:\Users\haxth3\`), Next lo elige como raíz y el build deja de usar este
   * proyecto. Fijarla a la raíz del repositorio lo hace determinista
   * (hallazgo B32, beta 1.0.0-beta.1).
   */
  outputFileTracingRoot: path.join(__dirname, "..", ".."),
  async rewrites() {
    const api = resolveApiUrl();
    return [
      {
        source: "/api/:path*",
        destination: `${api}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
