import { expect, test, type Page } from "@playwright/test";

/**
 * Sistema visual: todas las rutas migradas se tienen que ver **en oscuro y en
 * claro**, sin desbordar la ventana y sin errores de consola.
 *
 * Lo que se comprueba en cada ruta:
 *   1. la página carga y responde (hay contenido del sistema visible);
 *   2. no hay desbordamiento horizontal (las rejillas densas no rompen el
 *      maquetado en el ancho del navegador);
 *   3. el conmutador de tema cambia la base (atributo `data-tema` y color de
 *      fondo real: si los tokens no se aplicaran, el fondo no cambiaría);
 *   4. no se acumulan errores de consola.
 */
const RUTAS = [
  { ruta: "/", nombre: "acceso" },
  { ruta: "/fuentes", nombre: "fuentes" },
  { ruta: "/noticias", nombre: "noticias" },
  { ruta: "/estudio", nombre: "estudio" },
  { ruta: "/lotes", nombre: "lotes" },
  { ruta: "/configuracion", nombre: "configuración" },
  { ruta: "/ops", nombre: "operación" },
];

async function entrarEnDemo(page: Page) {
  await page.goto("/");
  // El botón aparece cuando la app resuelve la sesión (o comprueba que no la
  // hay): hay que **esperarlo**, no contarlo al principio. Contarlo daba 0, la
  // prueba se quedaba sin sesión y todas las peticiones de la API respondían
  // 401 (que el propio test cuenta como error de consola).
  const boton = page.getByRole("button", { name: "Entrar en modo demo" });
  const visible = await boton
    .waitFor({ state: "visible", timeout: 20_000 })
    .then(() => true)
    .catch(() => false);
  if (visible) {
    await boton.click();
    await page.waitForURL(/\/(fuentes|noticias|estudio|operacion|ops)/, { timeout: 30_000 });
  }
}

async function fondoDeFondo(page: Page): Promise<string> {
  return page.evaluate(() => getComputedStyle(document.body).backgroundColor);
}

test.describe("sistema visual: rutas migradas en oscuro y claro", () => {
  for (const { ruta, nombre } of RUTAS) {
    test(`${nombre} (${ruta}): responde, no desborda y cambia con el tema`, async ({ page }) => {
      const errores: string[] = [];
      page.on("console", (mensaje) => {
        if (mensaje.type() === "error") errores.push(mensaje.text());
      });
      page.on("pageerror", (fallo) => errores.push(fallo.message));

      await entrarEnDemo(page);
      await page.goto(ruta);
      await page.waitForLoadState("domcontentloaded");

      // 1) La vista responde: hay contenido del sistema visible.
      await expect(
        page.locator(".ops-panel, .card, .btn, .btn-sm, .btn-sm-primary").first(),
      ).toBeVisible({ timeout: 30_000 });

      // 2) Sin desbordamiento horizontal.
      const desborde = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(desborde, `la ruta ${ruta} desborda horizontalmente`).toBeLessThanOrEqual(2);

      // 3) El tema cambia de verdad (atributo y color de fondo).
      const conmutador = page.getByRole("button", { name: /Cambiar a tema/ });
      await expect(conmutador).toBeVisible();
      const antes = await fondoDeFondo(page);
      const temaAntes = await page.evaluate(() => document.documentElement.dataset.tema ?? "oscuro");

      await conmutador.click();
      await expect
        .poll(async () => page.evaluate(() => document.documentElement.dataset.tema ?? "oscuro"))
        .not.toBe(temaAntes);
      const despues = await fondoDeFondo(page);
      expect(despues, `el tema no cambia el fondo en ${ruta}`).not.toBe(antes);

      // Y se vuelve al tema original.
      await page.getByRole("button", { name: /Cambiar a tema/ }).click();
      await expect
        .poll(async () => page.evaluate(() => document.documentElement.dataset.tema ?? "oscuro"))
        .toBe(temaAntes);

      // 4) Sin errores de consola.
      expect(errores, `errores de consola en ${ruta}`).toEqual([]);
    });
  }
});
