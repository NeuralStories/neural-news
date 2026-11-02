import { expect, test, type Page } from "@playwright/test";

/**
 * NN-110.f — Gate G1: recorrido completo de la beta en navegador real.
 *
 * Un editor entra, crea una fuente, pide la transcripción, encuentra la
 * noticia, redacta y aprueba el guion, entra en el Studio y lanza el montaje.
 *
 * Lo que se verifica aquí y en ningún otro sitio:
 *   - el trabajo pesado **no bloquea** la interfaz: la transcripción y el
 *     montaje se piden y la página responde al instante;
 *   - el resultado llega **por el trabajo**, no porque el handler lo hiciera;
 *   - cuando no hay transcripción, la interfaz lo dice con claridad (aviso),
 *     no lo disfraza de éxito.
 *
 * Requiere API (:8000), worker y web (:3000) en marcha.
 */

async function loginDemo(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await expect(page).toHaveURL(/\/fuentes/);
}

test("beta: fuente → transcripción en cola → noticia → guion → estudio → montaje en cola", async ({
  page,
}) => {
  test.setTimeout(300_000);
  await loginDemo(page);

  const marca = `BETA-${Date.now()}`;
  const texto =
    "Cortexa Labs ha anunciado Radar, su modelo multimodal con un 12% más de acierto en " +
    `razonamiento visual según la ficha técnica. Prueba automatizada ${marca}.`;

  // 1) Alta de fuente con texto propio.
  await page.getByText("Aportar texto, archivo o transcripción").click();
  await page.locator("textarea").first().fill(texto);
  await page.getByRole("button", { name: "Registrar y analizar" }).click();
  await expect(page.getByRole("heading", { name: "Fuentes registradas" })).toBeVisible();
  const fila = page.locator("tbody tr").first();
  await expect(fila).toBeVisible({ timeout: 30_000 });

  // 2) La transcripción se pide en segundo plano: la interfaz responde enseguida
  //    y avisa de que está en cola.
  await fila.getByRole("button", { name: /Buscar transcripción/ }).click();
  await expect(page.getByText(/Buscando transcripción|Transcripción almacenada|No se ha encontrado transcripción/)).toBeVisible({
    timeout: 30_000,
  });
  // El aviso nunca se disfraza de error si no hay transcripción.
  await expect(page.getByText(/Traceback|has no attribute/)).toHaveCount(0);

  // 3) El trabajo se completa y su resultado es consultable por la API.
  const fuentes = await page.request.get("/api/v1/sources");
  const sourceId = ((await fuentes.json()).items[0] as { id: number }).id;
  await expect
    .poll(async () => {
      const jobs = await page.request.get("/api/v1/jobs");
      const items = (await jobs.json()).items as Array<{
        type: string;
        status: string;
      }>;
      const trabajo = items.find((j) => j.type === "transcribe_source");
      return trabajo?.status ?? "NINGUNO";
    }, { timeout: 60_000, intervals: [500] })
    .toMatch(/DONE|FAILED|RETRYABLE_FAILED/);

  // 4) La noticia candidata de ESTA fuente aparece y se puede investigar.
  //    Se busca por identificador, no por texto: en modo demo las noticias se
  //    fusionan por tema y puede haber noticias antiguas con el mismo titular.
  let storyId = 0;
  for (let i = 0; i < 40; i += 1) {
    const detalle = await page.request.get(`/api/v1/sources/${sourceId}`);
    const stories = ((await detalle.json()).stories ?? []) as Array<{ id: number }>;
    if (stories.length > 0) {
      storyId = stories[0].id;
      break;
    }
    await page.waitForTimeout(1000);
  }
  expect(storyId).toBeGreaterThan(0);

  await page.goto(`/noticias/${storyId}`);
  await expect(page).toHaveURL(new RegExp(`/noticias/${storyId}$`));
  await page.getByRole("button", { name: "Investigar" }).click();
  await expect(page.getByRole("heading", { name: "Afirmaciones" })).toBeVisible();

  // 5) Guion: generar, editar y guardar (la versión persiste).
  await page.getByRole("button", { name: "Generar borrador de guion" }).click();
  const editor = page.getByLabel("Editor de guion");
  await expect(editor).toBeVisible({ timeout: 40_000 });
  await expect(editor).not.toHaveValue("");
  await editor.fill(`${await editor.inputValue()}\n\nCierre de la prueba beta ${marca}.`);
  await page.getByRole("button", { name: "Guardar borrador" }).click();
  await expect(page.getByText(/Guardado como versión/)).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Aprobar esta versión" }).click();
  await expect(page.getByText(/Guion aprobado/)).toBeVisible({ timeout: 20_000 });

  // 6) Studio: el proyecto se crea y el estado se sincroniza.
  await page.getByRole("link", { name: "Estudio" }).click();
  await expect(page).toHaveURL(/\/estudio/);
  await page.getByLabel("Nombre").fill(`E2E Beta ${marca}`);
  await page.getByLabel(/Noticia del motor editorial/).selectOption(String(storyId));
  await page.getByRole("button", { name: /Crear y abrir el Studio/ }).click();
  await expect(page).toHaveURL(/\/estudio\?project=\d+/);
  await expect(page.getByText(/Estado sincronizado|Guardado ✓/)).toBeVisible();

  // 7) Producción: el montaje se PIDE en cola; la interfaz no se queda colgada.
  await page.getByRole("button", { name: /Producción y Vídeo/ }).first().click();
  await expect(page.getByText(/Validar y montar lo disponible/)).toBeVisible();
  const botonMontar = page.getByRole("button", { name: /Validar y montar lo disponible/ });
  await botonMontar.click();
  // El botón vuelve a estar disponible: el handler no ha esperado al render.
  await expect(botonMontar).toBeEnabled({ timeout: 20_000 });
  // Y el motivo está a la vista (aquí faltará material, y se dice).
  await expect(
    page.getByText(/No hay ningún segmento renderizable|no puede construirse|Falta material|material/i).first(),
  ).toBeVisible({ timeout: 40_000 });
});
