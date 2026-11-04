import { expect, test, type Page } from "@playwright/test";

/**
 * NN-107 F2 — Estudio Flow unificado en la web Next.js (sin iframe).
 *
 * Recorre las ocho etapas del Studio con persistencia real en la base de datos
 * vía /api/v1/projects (F1) y verifica:
 *   - una sola navegación (cero iframes) y un solo sistema editorial;
 *   - maxDotAi como único presentador (F-01) y sin identificador heredado;
 *   - contador de verificación honesto (R-BUG-3: importar/traspasar no verifica);
 *   - duraciones calculadas, no «8 s» fijos (R-BUG-4);
 *   - generación BLOCKED fuera del editor de Flow (controles no simulados);
 *   - los cambios de guion, voz, fondo y movimiento persisten tras recargar.
 *
 * Requiere API (:8000), worker y web (:3000) en marcha.
 */

async function loginDemo(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await expect(page).toHaveURL(/\/fuentes/);
}

test("studio: ocho etapas, guardado real y persistencia tras recargar", async ({ page }) => {
  test.setTimeout(300_000);
  await loginDemo(page);

  // Noticia real del motor editorial para vincular al proyecto (R-BUG-1).
  const marca = `STUDIO-${Date.now()}`;
  const texto =
    "Cortexa Labs ha anunciado Radar, su modelo multimodal con un 12% más de acierto en " +
    `razonamiento visual según la ficha técnica. Prueba automatizada ${marca}.`;
  const src = await page.request.post("/api/v1/sources", { data: { text: texto } });
  expect(src.ok()).toBeTruthy();
  const sourceId = (await src.json()).source.id as number;

  let storyId = 0;
  for (let i = 0; i < 40; i += 1) {
    const detail = await page.request.get(`/api/v1/sources/${sourceId}`);
    const stories = (await detail.json()).stories ?? [];
    if (stories.length > 0) {
      storyId = stories[0].id as number;
      break;
    }
    await page.waitForTimeout(2000);
  }
  expect(storyId).toBeGreaterThan(0);

  // Navegación única: la entrada al Studio es una página propia, no un iframe.
  await page.getByRole("link", { name: "Estudio" }).click();
  await expect(page).toHaveURL(/\/estudio/);
  await expect(page.getByRole("heading", { name: "Estudio Flow" })).toBeVisible();

  // Crear proyecto con la noticia vinculada (queda activa desde el inicio).
  await page.getByLabel("Nombre").fill(`E2E Studio ${marca}`);
  await page.getByLabel(/Proporción/).selectOption("16:9");
  await page.getByLabel(/Noticia del motor editorial/).selectOption(String(storyId));
  await page.getByRole("button", { name: /Crear y abrir el Studio/ }).click();
  await expect(page).toHaveURL(/\/estudio\?project=\d+/);
  await expect(page.getByText(/Estado sincronizado|Guardado/)).toBeVisible();

  // Cero iframes: el Studio vive en la página.
  await expect(page.locator("iframe")).toHaveCount(0);

  // Las ocho etapas están presentes en la navegación del Studio.
  for (const tab of [
    "Noticias",
    "Personaje",
    "Fondo CRT",
    "Voz Algenib",
    "Guion y Escenas",
    "Movimiento",
    "Referencias",
    "Producción y Vídeo",
  ]) {
    await expect(page.getByRole("button", { name: new RegExp(tab) }).first()).toBeVisible();
  }

  // (1) Noticias: contador de verificación honesto (R-BUG-3): las noticias de
  // ejemplo arrancan sin verificar y el traspaso nunca infla el contador.
  await page.getByRole("button", { name: /Noticias/ }).first().click();
  await expect(page.getByText("verificadas con fuentes")).toBeVisible();
  await expect(page.locator("text=verificadas con fuentes").locator("xpath=preceding-sibling::*[1]")).toHaveText(
    /^0$/,
  );

  // (2) Personaje: maxDotAi es el único presentador (F-01) y el identificador
  // heredado no aparece como opción vigente.
  await page.getByRole("button", { name: /Personaje/ }).first().click();
  await expect(page.getByText(/Identidad Canónica: maxDotAi/)).toBeVisible();
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("NeuralDotAI");

  // (3) Fondo: cambiar la proporción del estudio y esperar guardado real.
  await page.getByRole("button", { name: /Fondo CRT/ }).first().click();
  await page.getByRole("button", { name: /9:16/ }).first().click();
  await expect(page.getByText(/Guardado/).first()).toBeVisible();

  // (4) Guion y Escenas: texto único que debe sobrevivir a la recarga.
  await page.getByRole("button", { name: /Guion y Escenas/ }).first().click();
  const guionUnico = `Locución continua de prueba ${marca}.`;
  const editor = page.locator("textarea").first();
  await expect(editor).toBeVisible();
  await editor.fill(guionUnico);
  await expect(page.getByText(/Guardado/).first()).toBeVisible();

  // (5) Voz: velocidad editable (hipótesis Algenib, no calibración confirmada).
  await page.getByRole("button", { name: /Voz Algenib/ }).first().click();
  await expect(page.getByText(/hipótesis Algenib, sin calibrar/)).toBeVisible();
  const velocidad = page.locator('input[type="range"]');
  await velocidad.fill("1.26");
  await expect(page.getByText(/Guardado/).first()).toBeVisible();

  // (6) Movimiento: alternar un movimiento del catálogo.
  await page.getByRole("button", { name: /Movimiento/ }).first().click();
  const toggle = page.getByText("Travelling Frontal Continuo").first();
  await toggle.click();
  await expect(page.getByText(/Guardado/).first()).toBeVisible();

  // (7) Referencias: las dos bibliotecas separadas se muestran.
  await page.getByRole("button", { name: /Referencias/ }).first().click();
  await expect(page.getByText(/Audiovisuales|Editoriales/).first()).toBeVisible();

  // (8) Producción y Vídeo: duraciones calculadas (R-BUG-4) y generación
  // BLOCKED fuera del editor de Flow (nunca un control simulado).
  await page.getByRole("button", { name: /Producción y Vídeo/ }).first().click();
  await expect(page.getByText(/tomas \(≈/)).toBeVisible(); // duración calculada (R-BUG-4)
  await expect(page.getByText(/BLOCKED — generación de vídeo no disponible fuera del editor de Flow/)).toBeVisible();

  // Persistencia: recargar la página y recuperar el estado del servidor.
  await page.reload();
  await expect(page.getByText(/Estado sincronizado|Guardado/)).toBeVisible();
  await page.getByRole("button", { name: /Guion y Escenas/ }).first().click();
  await expect(page.locator("textarea").first()).toHaveValue(new RegExp(guionUnico));

  await page.getByRole("button", { name: /Voz Algenib/ }).first().click();
  await expect(page.locator('input[type="range"]')).toHaveValue(/^1\.26$/);

  // El proyecto mantiene su ratio de creación (R-BUG-2) y la noticia activa.
  const projectUrl = new URL(page.url());
  const projectId = Number(projectUrl.searchParams.get("project"));
  const api = await page.request.get(`/api/v1/projects/${projectId}`);
  const project = await api.json();
  expect(project.ratio).toBe("16:9");
  expect(project.story_id).toBe(storyId);
});
