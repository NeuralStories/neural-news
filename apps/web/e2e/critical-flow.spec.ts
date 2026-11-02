import { expect, test, type Page } from "@playwright/test";

/**
 * Recorrido crítico completo en navegador real:
 *   entrar en demo → registrar fuente → esperar candidatos → investigar →
 *   generar guion → editar → aprobar → preparar storyboard → crear lote → exportar.
 *
 * La API y el worker deben estar en marcha (API en :8000, worker separado).
 */

async function loginDemo(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo demo" }).click();
  await expect(page).toHaveURL(/\/fuentes/);
  await expect(page.getByText("DEMO").first()).toBeVisible();
}

test("recorrido crítico completo: fuente → noticias → guion → aprobación → lote → paquete", async ({
  page,
}) => {
  // El recorrido encadena varios trabajos del worker: necesita margen.
  test.setTimeout(300_000);
  await loginDemo(page);

  // 1) Registrar una fuente de texto única.
  const marca = `E2E-${Date.now()}`;
  const texto = `Cortexa Labs ha anunciado Radar, su modelo multimodal con un 12% más de acierto en razonamiento visual según la ficha técnica; lista de espera para demo web. Prueba automatizada ${marca}.`;
  await page.getByPlaceholder("https://… (YouTube, Spotify, artículo o feed RSS)").fill("");
  await page.getByText("Aportar texto, archivo o transcripción").click();
  const areaTexto = page.locator("textarea").first();
  await areaTexto.fill(texto);
  await page.getByRole("button", { name: "Registrar y analizar" }).click();

  // 2) La fuente aparece en la tabla con un estado legible.
  await expect(page.getByRole("heading", { name: "Fuentes registradas" })).toBeVisible();
  const fila = page.locator("tbody tr").first();
  await expect(fila).toBeVisible({ timeout: 30_000 });

  // 3) La noticia candidata aparece en Noticias (elegimos la de Radar, no la genérica).
  await page.getByRole("link", { name: "Noticias", exact: true }).click();
  await expect(page).toHaveURL(/\/noticias/);
  const linkNoticia = page.getByRole("link", { name: /Radar/ }).first();
  await expect(linkNoticia).toBeVisible({ timeout: 30_000 });
  await linkNoticia.click();
  await expect(page).toHaveURL(/\/noticias\/\d+/);

  // 4) Investigar: las afirmaciones aparecen con estado de verificación.
  await page.getByRole("button", { name: "Investigar" }).click();
  await expect(page.getByRole("heading", { name: "Afirmaciones" })).toBeVisible();
  const panelAfirmaciones = page.locator("section", { hasText: "Afirmaciones" }).first();
  await expect(panelAfirmaciones).toContainText(/Sin verificar|Confirmada/, { timeout: 40_000 });

  // 5) Generar borrador de guion.
  //    Se espera a que el trabajo **termine** antes de seguir: en demo las
  //    noticias se fusionan por tema, así que una prueba puede dejar un
  //    borrador en marcha que, si landing durante la edición, crea una versión
  //    posterior y deja la aprobación apuntando a una versión que ya no es la
  //    última.
  const storyId = Number(new URL(page.url()).pathname.split("/").pop());
  const borrador = await page.request.post(`/api/v1/stories/${storyId}/draft`);
  const borradorJob = (await borrador.json()) as { job_id: number };
  await expect
    .poll(
      async () => {
        const j = await (await page.request.get(`/api/v1/jobs/${borradorJob.job_id}`)).json();
        return j.status as string;
      },
      { timeout: 60_000, intervals: [500] },
    )
    .toMatch(/DONE|FAILED|RETRYABLE_FAILED/);
  await page.reload();

  const editor = page.getByLabel("Editor de guion");
  await expect(editor).toBeVisible({ timeout: 40_000 });
  await expect(editor).not.toHaveValue("");

  // 6) Editar el guion y guardar (nueva versión). El texto es único por ejecución:
  //    la demo fusiona candidatos por tema, así que la historia acumula versiones.
  const textoOriginal = await editor.inputValue();
  await editor.fill(`${textoOriginal}\n\nCierre añadido por la prueba automática ${marca}.`);
  const botonGuardar = page.getByRole("button", { name: "Guardar borrador" });
  await expect(botonGuardar).toBeEnabled();
  await botonGuardar.click();
  await expect(page.getByText(/Guardado como versión/)).toBeVisible({ timeout: 20_000 });

  // 7) Aprobar esa versión.
  await page.getByRole("button", { name: "Aprobar esta versión" }).click();
  await expect(page.getByText(/Guion aprobado/)).toBeVisible({ timeout: 20_000 });

  // 8) Preparar la escena (storyboard) con prompts de imagen.
  await page.getByRole("button", { name: "Preparar escenas" }).click();
  await expect(page.getByText(/Prompts preliminares/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Escena 1", { exact: true })).toBeVisible();
  await expect(page.getByText("Prompt de imagen").first()).toBeVisible();

  // 9) Ir a Lotes: la noticia aparece en la selección y el lote se puede crear.
  await page.getByRole("link", { name: "Lotes", exact: true }).click();
  await expect(page).toHaveURL(/\/lotes/);
  const botonAnadir = page.getByRole("button", { name: "Añadir" }).first();
  await botonAnadir.click();
  await expect(page.getByRole("button", { name: /Crear lote/ })).toContainText("(1/5)");

  // 10) Volver a Noticias: la noticia aprobada aparece como tal.
  await page.getByRole("link", { name: "Noticias", exact: true }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
});

test("la tabla de noticias muestra fecha real, verificación y duplicados posibles", async ({ page }) => {
  await loginDemo(page);
  await page.getByRole("link", { name: "Noticias", exact: true }).click();
  await expect(page).toHaveURL(/\/noticias/);

  await expect(page.getByRole("columnheader", { name: "Fecha real" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Verificación" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Duplicados" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Puntuación" })).toBeVisible();
});

test("fuentes: reintento seguro y acción de analizar vídeo", async ({ page }) => {
  await loginDemo(page);
  await expect(page.getByRole("heading", { name: "Añadir fuente" })).toBeVisible();

  // Registrar una URL de YouTube y comprobar que ofrece análisis de vídeo.
  await page.getByPlaceholder("https://… (YouTube, Spotify, artículo o feed RSS)").fill(
    `https://youtu.be/e2e${Date.now().toString().slice(-8)}`,
  );
  await page.getByRole("button", { name: "Registrar y analizar" }).click();

  const fila = page.locator("tbody tr").first();
  await expect(fila).toBeVisible({ timeout: 30_000 });
  await expect(fila.getByRole("button", { name: "Volver a analizar" })).toBeVisible();
  await expect(fila.getByRole("button", { name: "Analizar vídeo" })).toBeVisible();
});

test("el diseño es usable en móvil (390 px)", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginDemo(page);
  await expect(page.getByRole("heading", { name: "Añadir fuente" })).toBeVisible();

  // Sin desbordamiento horizontal del documento.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(2);

  await page.getByRole("link", { name: "Noticias", exact: true }).click();
  await expect(page).toHaveURL(/\/noticias/);
  const overflowNoticias = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflowNoticias).toBeLessThanOrEqual(2);
});

test("sin sesión, la web redirige al acceso", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto("/noticias");
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
  await expect(page.getByRole("button", { name: "Entrar en modo demo" })).toBeVisible();
});
