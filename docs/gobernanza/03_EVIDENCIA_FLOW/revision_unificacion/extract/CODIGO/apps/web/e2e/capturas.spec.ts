import { test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";

const DIR = "../../docs/informes/capturas";

async function login(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await page.waitForURL(/\/fuentes/);
}

test("capturas del estado final", async ({ page }) => {
  test.setTimeout(180_000);
  mkdirSync(DIR, { recursive: true });

  // Escritorio
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);
  await page.screenshot({ path: `${DIR}/final-escritorio-01-fuentes.png`, fullPage: false });

  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
  await page.waitForURL(/\/noticias/);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${DIR}/final-escritorio-02-noticias.png`, fullPage: false });

  // Detalle: cabecera de decisión + checklist
  await page.getByLabel("Buscar noticias").fill("Radar");
  await page.waitForTimeout(1500);
  await page.getByRole("link", { name: /Radar/ }).first().click();
  await page.waitForURL(/\/noticias\/\d+/);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${DIR}/final-escritorio-03-detalle.png`, fullPage: false });

  // Lotes
  await page.getByRole("navigation").getByRole("link", { name: /^Lotes/ }).click();
  await page.waitForURL(/\/lotes/);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${DIR}/final-escritorio-04-lotes.png`, fullPage: false });

  // Estudio integrado (mismo origen)
  await page.getByRole("navigation").getByRole("link", { name: /^Estudio/ }).click();
  await page.waitForURL(/\/estudio/);
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${DIR}/final-escritorio-05-estudio.png`, fullPage: false });

  // Móvil
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/noticias");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${DIR}/final-movil-01-noticias.png`, fullPage: false });
  await page.goto("/fuentes");
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${DIR}/final-movil-02-fuentes.png`, fullPage: false });
});
