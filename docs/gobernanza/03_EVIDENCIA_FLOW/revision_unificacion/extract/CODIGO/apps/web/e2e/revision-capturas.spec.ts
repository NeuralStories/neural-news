import { test, expect, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";

const DIR = "../../REVISION_UNIFICACION/CAPTURAS";
mkdirSync(DIR, { recursive: true });

async function login(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await page.waitForURL(/\/fuentes/);
  await page.waitForTimeout(1200);
}

test.describe.serial("Capturas para revisión de unificación", () => {
  let page: Page;
  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await login(page);
  });

  test("web: raíz de acceso (sin sesión)", async ({ browser }) => {
    const anon = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await anon.goto("/");
    await anon.waitForTimeout(1200);
    await anon.screenshot({ path: `${DIR}/web-00-acceso.png`, fullPage: false });
    await anon.close();
  });

  test("web: fuentes", async () => {
    await page.goto("/fuentes");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/web-01-fuentes.png`, fullPage: false });
  });

  test("web: noticias", async () => {
    await page.goto("/noticias");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/web-02-noticias.png`, fullPage: false });
  });

  test("web: detalle de noticia aprobada", async () => {
    await page.getByLabel("Buscar noticias").fill("Radar");
    await page.waitForTimeout(1500);
    await page.getByRole("link", { name: /Radar/ }).first().click();
    await page.waitForURL(/\/noticias\/\d+/);
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${DIR}/web-03-noticia-detalle.png`, fullPage: false });
    await page.screenshot({ path: `${DIR}/web-03b-noticia-detalle-completa.png`, fullPage: true });
  });

  test("web: lotes", async () => {
    await page.getByRole("navigation").getByRole("link", { name: /^Lotes/ }).click();
    await page.waitForURL(/\/lotes/);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/web-04-lotes.png`, fullPage: false });
  });

  test("web: configuración", async () => {
    await page.getByRole("navigation").getByRole("link", { name: /^Configuración/ }).click();
    await page.waitForURL(/\/configuracion/);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/web-05-configuracion.png`, fullPage: false });
  });

  test("web: estudio integrado (pestaña Noticias)", async () => {
    await page.getByRole("navigation").getByRole("link", { name: /^Estudio/ }).click();
    await page.waitForURL(/\/estudio/);
    await page.waitForTimeout(4500);
    await page.screenshot({ path: `${DIR}/web-06-estudio-integrado.png`, fullPage: false });
  });

  const TABS: [string, string][] = [
    ["Noticias", "07-studio-noticias"],
    ["Personaje", "08-studio-personaje"],
    ["Fondo CRT", "09-studio-fondo"],
    ["Guion y Escenas", "10-studio-guion"],
    ["Voz Algenib", "11-studio-voz"],
    ["Movimiento", "12-studio-movimiento"],
    ["Referencias", "13-studio-referencias"],
    ["Producción y Vídeo", "14-studio-produccion"],
  ];

  test("studio: recorrer las 8 secciones", async () => {
    const marco = page.frameLocator("iframe[title*='Studio']");
    for (const [label, archivo] of TABS) {
      const boton = marco
        .getByRole("button")
        .filter({ hasText: new RegExp(label.replace(/[.*+?^${}()|[\]\]/g, "\$&")) })
        .first();
      if (await boton.count()) {
        await boton.click();
        await page.waitForTimeout(1500);
        await page.screenshot({ path: `${DIR}/web-${archivo}.png`, fullPage: false });
      }
    }
  });

  test("móvil: pantallas principales", async ({ page: _p }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/noticias");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/movil-01-noticias.png` });
    await page.goto("/fuentes");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/movil-02-fuentes.png` });
    await page.goto("/estudio");
    await page.waitForTimeout(4000);
    await page.screenshot({ path: `${DIR}/movil-03-estudio.png` });
    await page.setViewportSize({ width: 1440, height: 900 });
  });
});
