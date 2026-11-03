import { defineConfig, devices } from "@playwright/test";

/**
 * E2E del recorrido crítico de neural.news contra la web real (Next.js) + API real.
 *
 * - Usa el navegador Edge/Chrome ya instalado en el sistema (canal `msedge`):
 *   no hace falta descargar navegadores de Playwright.
 * - La API y el worker deben estar en marcha (ver docs/OPERATIONS.md §2).
 * - Cada test parte de una base limpia: usa una fuente y una noticia propias.
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
});
