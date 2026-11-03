import { test, expect, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync, appendFileSync } from "node:fs";

const DIR = "../../docs/auditoria-funcional/capturas";
const JSONL = "../../docs/auditoria-funcional/datos-navegacion.jsonl";
mkdirSync(DIR, { recursive: true });

function registrar(h: Record<string, unknown>) {
  appendFileSync(JSONL, JSON.stringify(h) + "\n", "utf-8");
}

async function monitor(page: Page) {
  const errores: string[] = [];
  const handler = (e: Error) => errores.push("PAGEERROR: " + String(e.message).slice(0, 150));
  const resp = (r: { status: () => number; url: () => string }) => {
    if (r.status() >= 400) errores.push(`RED ${r.status()} ${r.url()}`);
  };
  page.on("pageerror", handler);
  page.on("response", resp);
  return () => {
    page.off("pageerror", handler);
    page.off("response", resp);
    return errores;
  };
}

test.describe.serial("Auditoría continuación", () => {
  let page: Page;
  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto("/");
    await page.getByRole("button", { name: "Entrar en modo demo" }).click();
    await page.waitForURL(/\/fuentes/);
  });

  test("detalle de noticia (aprobada)", async () => {
    const fin = monitor(page);
    await page.goto("/noticias");
    await page.waitForTimeout(1500);
    // abrir una aprobada desde la vista rápida
    const enlace = page.getByRole("link", { name: /Radar|Acme|Noticia|Cortexa/i }).first();
    await enlace.click();
    await page.waitForURL(/\/noticias\/\d+/);
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${DIR}/escritorio-noticia-detalle.png` });
    registrar({
      vista: "detalle-noticia",
      url: page.url(),
      headings: (await page.locator("h1, h2").allInnerTexts()).slice(0, 10),
      botones: (await page.locator("main button").allInnerTexts()).slice(0, 16),
      errores: fin(),
    });
  });

  test("detalle móvil 390px", async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/noticias");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/movil-noticias.png` });
    await page.goto("/fuentes");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${DIR}/movil-fuentes.png` });
    await page.goto("/estudio");
    await page.waitForTimeout(3500);
    await page.screenshot({ path: `${DIR}/movil-estudio.png` });
    registrar({ vista: "movil-390", paginas: ["noticias", "fuentes", "estudio"], errores: fin() });
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test("Studio: recorrer las 8 secciones del iframe", async () => {
    const fin = monitor(page);
    await page.goto("/estudio");
    await page.waitForTimeout(4000);
    const marco = page.frameLocator("iframe[title*='Studio']");
    const tabs = [
      ["Noticias", "noticias"],
      ["Personaje", "personaje"],
      ["Fondo CRT", "fondo"],
      ["Guion y Escenas", "guion"],
      ["Voz Algenib", "voz"],
      ["Movimiento", "movimiento"],
      ["Referencias", "referencias"],
      ["Producción y Vídeo", "resultado"],
    ];
    for (const [label, slug] of tabs) {
      // En escritorio las pestañas son botones; buscar dentro del iframe.
      const boton = marco.getByRole("button", { name: new RegExp(label.replace(/[.*+?^${}()|[\]\]/g, "\$&")) }).first();
      if (await boton.count()) {
        await boton.click();
        await page.waitForTimeout(1200);
        await page.screenshot({ path: `${DIR}/studio-tab-${slug}.png` });
        registrar({ vista: `studio-${slug}`, capturado: true });
      } else {
        registrar({ vista: `studio-${slug}`, capturado: false, motivo: "botón no encontrado" });
      }
    }
    registrar({ vista: "studio-errores-consola", errores: fin() });
  });
});
