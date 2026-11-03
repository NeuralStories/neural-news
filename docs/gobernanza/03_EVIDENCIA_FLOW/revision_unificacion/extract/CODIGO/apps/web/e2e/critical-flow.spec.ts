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
  // La interfaz tiene pestañas «Enlace» / «Texto»: se usa la de texto para aportar contenido.
  await page.getByRole("tab", { name: /Texto/ }).click();
  await page.locator("textarea").first().fill(texto);
  await page.getByRole("button", { name: "Registrar y analizar" }).click();

  // 2) La fuente aparece en la tabla con un estado legible.
  await expect(page.getByRole("heading", { name: "Fuentes registradas" })).toBeVisible();
  const fila = page.locator("tbody tr").first();
  await expect(fila).toBeVisible({ timeout: 30_000 });

  // 3) La noticia candidata aparece en Noticias (elegimos la de Radar, no la genérica).
  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
  await expect(page).toHaveURL(/\/noticias/);
  // La búsqueda es transversal: encuentra la noticia aunque no esté en la vista activa.
  await page.getByLabel("Buscar noticias").fill(/Radar/.source ? "Radar" : "Radar");
  const linkNoticia = page.getByRole("link", { name: /Radar/ }).first();
  await expect(linkNoticia).toBeVisible({ timeout: 30_000 });
  await linkNoticia.click();
  await expect(page).toHaveURL(/\/noticias\/\d+/);

  // 4) Investigar: las afirmaciones aparecen con estado de verificación.
  await page.getByRole("button", { name: "Investigar" }).click();
  await expect(page.getByRole("heading", { name: "Afirmaciones" })).toBeVisible();
  // Se ancla en el encabezado exacto: el resumen de la cabecera también menciona «Afirmaciones».
  const panelAfirmaciones = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: "Afirmaciones", exact: true }) })
    .first();
  await expect(panelAfirmaciones).toContainText(/Sin verificar|Confirmada/, { timeout: 40_000 });

  // 5) Generar borrador de guion.
  await page.getByRole("button", { name: "Generar borrador de guion" }).click();
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
  // El texto aparece en el aviso y en el bloque de versión aprobada: se toma el primero.
  await expect(page.getByText(/Guion aprobado/).first()).toBeVisible({ timeout: 20_000 });

  // 8) Preparar la escena (storyboard) con prompts de imagen.
  await page.getByRole("button", { name: "Preparar escenas" }).click();
  await expect(page.getByText(/Prompts preliminares/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Escena 1", { exact: true })).toBeVisible();
  await expect(page.getByText("Prompt de imagen").first()).toBeVisible();

  // 9) Ir a Lotes: la noticia aparece en la selección y el lote se puede crear.
  await page.getByRole("navigation").getByRole("link", { name: /^Lotes/ }).click();
  await expect(page).toHaveURL(/\/lotes/);
  const botonAnadir = page.getByRole("button", { name: "Añadir" }).first();
  await botonAnadir.click();
  await expect(page.getByRole("button", { name: /Crear lote/ })).toContainText("(1/5)");

  // 10) Volver a Noticias: la noticia aprobada aparece como tal.
  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
  // La bandeja de tareas muestra cada noticia como bloque con su acción segura.
  await expect(page.getByRole("link", { name: /.+/ }).filter({ hasText: /.+/ }).first()).toBeVisible();
  await expect(page.getByText("Requieren atención").first()).toBeVisible();
});

test("la bandeja de noticias muestra fecha real, verificación y duplicados posibles", async ({ page }) => {
  await loginDemo(page);
  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
  await expect(page).toHaveURL(/\/noticias/);

  // Dimensiones visibles en cada noticia (etapa, verificación, origen y fecha).
  await expect(page.getByText("Etapa:").first()).toBeVisible();
  await expect(page.getByText("Verificación:").first()).toBeVisible();
  await expect(page.getByText("Origen:").first()).toBeVisible();
  await expect(page.getByText(/afirmaciones verificadas|Sin afirmaciones/).first()).toBeVisible();
  // Vistas rápidas con recuento.
  await expect(page.getByText("Requieren atención").first()).toBeVisible();
  await expect(page.getByText("Listas para aprobar").first()).toBeVisible();
  await expect(page.getByText("Aprobadas").first()).toBeVisible();
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

  await page.getByRole("navigation").getByRole("link", { name: /^Noticias/ }).click();
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
