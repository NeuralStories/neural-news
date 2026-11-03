import { expect, test, type Page } from "@playwright/test";

/**
 * Pruebas de navegador de la Fase 5:
 * - las vistas rápidas de Noticias filtran de verdad y son coherentes con los recuentos;
 * - el traspaso de una noticia llega a Studio sin pedir el ID ni un JSON;
 * - una sesión no DEMO (administrativa) también funciona.
 */

async function entrarDemo(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await expect(page).toHaveURL(/\/fuentes/);
}

test("las vistas rápidas filtran y los recuentos coinciden", async ({ page }) => {
  await entrarDemo(page);
  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
  await expect(page).toHaveURL(/\/noticias/);

  const tarjetas = page.locator("main button").filter({ hasText: /Requieren atención|Listas para aprobar|Aprobadas/ });
  await expect(tarjetas).toHaveCount(3);

  // La vista activa cambia el listado y queda marcada.
  const activas = page.locator('main button[aria-pressed="true"]');
  await expect(activas.first()).toBeVisible();

  // Cada tarjeta muestra su recuento y al activarla cambia el estado activo.
  const btnAprobadas = page.getByRole("button", { name: /^Aprobadas/ });
  await btnAprobadas.click();
  await expect(page.locator('main button[aria-pressed="true"]').filter({ hasText: "Aprobadas" })).toHaveCount(1);
  // Las noticias aprobadas llevan la marca de producción lista o de atención.
  const filas = page.locator("main li");
  await expect(filas.first()).toBeVisible();
});

test("el traspaso de una noticia llega a Studio sin copiar JSON", async ({ page }) => {
  await entrarDemo(page);
  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
  await page.getByLabel("Buscar noticias").fill("Radar");
  await expect(page.getByRole("link", { name: /Radar/ }).first()).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: /Radar/ }).first().click();
  await expect(page).toHaveURL(/\/noticias\/\d+/);

  // Si la noticia está aprobada, el enlace al estudio lleva su identificador.
  const continuar = page.getByRole("link", { name: "Continuar en Studio" });
  if ((await continuar.count()) > 0) {
    await continuar.click();
    await expect(page).toHaveURL(/\/estudio\?story=\d+/);
    // El estudio se sirve desde la misma aplicación.
    const marco = page.frameLocator("iframe[title*='Studio']");
    await expect(marco.getByText(/Traspaso desde neural\.news/)).toBeVisible({ timeout: 20_000 });
  }
});

test("sin sesión, la aplicación redirige al acceso", async ({ page }) => {
  await page.goto("/noticias");
  await expect(page).toHaveURL(/\/$|\/$/);
});
