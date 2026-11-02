import { defineConfig, devices } from "@playwright/test";

/**
 * E2E del recorrido crítico de neural.news contra la web real (Next.js) + API real.
 *
 * - Usa el navegador Edge/Chrome ya instalado en el sistema (canal `msedge`):
 *   no hace falta descargar navegadores de Playwright.
 * - **La pila se levanta sola** (NN-113.14): antes había que tener el API, el
 *   worker y la web en marcha a mano en tres terminales, y el E2E fallaba con
 *   un error confuso si se olvidaba uno.
 * - Cada test parte de una base limpia: usa una fuente y una noticia propias.
 */
const reutilizar = false;

/**
 * Por qué `reuseExistingServer` es **false** (NN-113.14):
 *
 * Si el E2E reutiliza un servidor que ya estaba en marcha, puede estar
 * sirviendo un build **anterior**: al reconstruir (`npm run build`) los
 * ficheros de los chunks se sustituyen, el servidor viejo sigue sirviendo el
 * manifiesto viejo y el navegador pide chunks que ya no existen (HTTP 400).
 * La página se queda en «Cargando…» sin hidratar y el E2E se agota esperando
 * un botón que nunca aparece (pasó dos veces).
 *
 * Con `false`, Playwright levanta **siempre** su propia pila: si el puerto
 * está ocupado, lo dice con claridad («port 3000 is used…») en vez de
 * envenenar la ejecución.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.NEURAL_E2E_BASE_URL || "http://localhost:3000",
    channel: process.env.NEURAL_E2E_CHANNEL || "msedge",
    locale: "es-ES",
    timezoneId: "Europe/Madrid",
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "edge", use: { ...devices["Desktop Edge"] } }],
  webServer: [
    {
      command: "python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000",
      cwd: "../api",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: reutilizar,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "python -m neuralnews.worker",
      cwd: "../api",
      reuseExistingServer: reutilizar,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "npm run start",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: reutilizar,
      timeout: 180_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
