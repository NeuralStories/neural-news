import { expect, test, type Page } from "@playwright/test";

/**
 * NN-107 F3 — Recorrido vertical de producción audiovisual en la interfaz:
 *   noticia real → guion → director determinista → tomas → prompt versionado →
 *   FlowManualPackage descargable → importación de MP4 externo → revisión y
 *   aprobación humana, todo persistido en la base de datos.
 *
 * No simula generación ni conexión con Flow: la toma se importa de un archivo
 * externo (como hará el operador tras generar en Flow).
 */

const GUION = (
  "Cortexa Labs presenta Radar con un 12 por ciento más de acierto en razonamiento visual. " +
  "La compañía atribuye el salto a su nuevo motor de atención. " +
  "Los centros de datos europeos ya prueban el modelo con cargas reales. " +
  "Radar llegará a producción general el próximo trimestre."
);

async function loginDemo(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await expect(page).toHaveURL(/\/fuentes/);
}

test("producción vertical: director → prompt → paquete Flow → importar MP4 → aprobar", async ({
  page,
}) => {
  test.setTimeout(300_000);
  await loginDemo(page);

  // Noticia real del motor editorial.
  const marca = `F3-${Date.now()}`;
  const src = await page.request.post("/api/v1/sources", {
    data: { text: `Prueba automatizada ${marca}. ${GUION}` },
  });
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

  // Proyecto con la noticia vinculada y guion propio (paso Guion vía API).
  const project = await (
    await page.request.post("/api/v1/projects", {
      data: { name: `Vertical ${marca}`, ratio: "16:9", story_id: storyId },
    })
  ).json();
  const pid = project.id as number;
  const saved = await page.request.put(`/api/v1/projects/${pid}/studio/guion`, {
    data: { payload: { scriptText: GUION }, expected_revision: 0 },
  });
  expect(saved.ok()).toBeTruthy();

  // Abrir el Studio en el proyecto y ir a Producción y Vídeo.
  await page.goto(`/estudio?project=${pid}`);
  await expect(page.getByText(/Estado sincronizado|Guardado ✓/)).toBeVisible();
  await page.getByRole("button", { name: /Producción y Vídeo/ }).first().click();

  // Director determinista: crea beats + tomas persistidas.
  await page.getByRole("button", { name: /Ejecutar director audiovisual/ }).click();
  await expect(page.getByText(/Plan determinista: \d+ beats de locución continua/)).toBeVisible();
  await expect(page.getByText(/Gráfico programático/).first()).toBeVisible(); // cifra → DATA_GRAPHIC
  await expect(page.getByText(/maxDotAi \(Flow\)/).first()).toBeVisible(); // apertura/cierre
  const takesPanel = page.locator("li", { hasText: "Toma 1 ·" }).first();
  await expect(takesPanel).toContainText("PLANIFICADA");

  // Prompt versionado de la toma 1.
  await takesPanel.getByRole("button", { name: /Generar prompt de la toma/ }).click();
  await expect(takesPanel.getByText(/estado: PROMPT_LISTO/)).toBeVisible();

  // FlowManualPackage descargable.
  const downloadPromise = page.waitForEvent("download");
  await takesPanel.getByRole("button", { name: /Descargar FlowManualPackage/ }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/flow_manual_package_take_1\.json$/);

  // Importación del MP4 generado externamente (archivo de prueba local).
  await takesPanel.locator('input[type="file"]').setInputFiles({
    name: "toma1.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("mp4-content-for-vertical-e2e"),
  });
  await takesPanel.getByRole("button", { name: /Importar y asociar a la toma/ }).click();
  await expect(takesPanel.getByText(/MP4 importado · sha256/)).toBeVisible();
  await expect(takesPanel.locator("video")).toHaveCount(1);

  // Aprobación humana de la toma importada.
  await takesPanel.getByRole("button", { name: /Aprobar toma/ }).click();
  await expect(takesPanel.getByText(/Toma aprobada por revisión humana/)).toBeVisible();

  // Persistencia: recargar y recuperar el estado completo del proyecto.
  await page.reload();
  await expect(page.getByText(/Estado sincronizado|Guardado ✓/)).toBeVisible();
  await page.getByRole("button", { name: /Producción y Vídeo/ }).first().click();
  const takesAfter = page.locator("li", { hasText: "Toma 1 ·" }).first();
  await expect(takesAfter.getByText(/estado: APROBADA/)).toBeVisible();
  await expect(takesAfter.locator("video")).toHaveCount(1);

  // El backend confirma el estado final (toma aprobada, prompt versionado, ratio intacto).
  const state = await (await page.request.get(`/api/v1/projects/${pid}`)).json();
  expect(state.ratio).toBe("16:9");
  expect(state.takes[0].status).toBe("APROBADA");
  expect(state.takes[0].imported_media).not.toBeNull();
  expect(state.takes[0].prompt_versions).toBeGreaterThanOrEqual(1);
  expect(state.shots.length).toBeGreaterThanOrEqual(2);
});
