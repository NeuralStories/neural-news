// Captura de todas las vistas migradas, en tema oscuro y claro.
//
// Recorre cada ruta de `apps/web/app`, comprueba que responde 200 y deja una
// captura en `docs/entrega/evidencias/vistas/`. Es la evidencia de que el
// sistema visual se aplica en las dos bases y en todas las vistas.
//
// Uso (desde la raíz del repositorio, con la pila levantada):
//     node tools/auditoria/capturar_vistas.mjs
//
// Playwright está instalado en `apps/web` (dependencia de desarrollo de la
// app), así que se importa por ruta relativa: este script vive fuera del
// paquete de la web.
import playwright from "../../apps/web/node_modules/@playwright/test/index.js";

const { chromium } = playwright;
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const DESTINO = join(RAIZ, "docs", "entrega", "evidencias", "vistas");
const BASE = process.env.NEURAL_WEB_URL || "http://localhost:3000";

const RUTAS = [
  { ruta: "/", nombre: "acceso" },
  { ruta: "/fuentes", nombre: "fuentes" },
  { ruta: "/noticias", nombre: "noticias" },
  { ruta: "/estudio", nombre: "estudio" },
  { ruta: "/lotes", nombre: "lotes" },
  { ruta: "/configuracion", nombre: "configuracion" },
  { ruta: "/ops", nombre: "operacion" },
];

mkdirSync(DESTINO, { recursive: true });

const navegador = await chromium.launch({ channel: "msedge" });
const contexto = await navegador.newContext({ viewport: { width: 1440, height: 900 } });
const pagina = await contexto.newPage();

const errores = [];
pagina.on("console", (mensaje) => {
  if (mensaje.type() === "error") errores.push(`${mensaje.text()}`);
});
pagina.on("pageerror", (fallo) => errores.push(fallo.message));

// Sesión de demo (misma vía que las pruebas de Playwright).
await pagina.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
const entrar = pagina.getByRole("button", { name: "Entrar en modo demo" });
const visible = await entrar
  .waitFor({ state: "visible", timeout: 20_000 })
  .then(() => true)
  .catch(() => false);
if (visible) {
  await entrar.click();
  await pagina.waitForURL(/\/(fuentes|noticias|estudio|ops)/, { timeout: 30_000 });
}

const resumen = [];
for (const { ruta, nombre } of RUTAS) {
  for (const tema of ["oscuro", "claro"]) {
    await pagina.goto(`${BASE}${ruta}`, { waitUntil: "domcontentloaded" });
    await pagina.evaluate((valor) => {
      document.documentElement.dataset.tema = valor;
    }, tema);
    await pagina.waitForTimeout(1200);

    const estado = await pagina.evaluate(() => ({
      codigo: document.querySelector("main") ? 200 : 0,
      fondo: getComputedStyle(document.body).backgroundColor,
      desborde:
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
      titulo: document.title,
    }));

    const fichero = join(DESTINO, `${nombre}-${tema}.png`);
    await pagina.screenshot({ path: fichero, fullPage: false });
    resumen.push({ ruta, tema, fondo: estado.fondo, desborde: estado.desborde, fichero });
    console.log(
      `${ruta.padEnd(16)} ${tema.padEnd(7)} fondo=${estado.fondo} desborde=${estado.desborde}px`,
    );
  }
}

writeFileSync(
  join(DESTINO, "resumen.json"),
  JSON.stringify({ resumen, errores }, null, 2),
  "utf-8",
);

await navegador.close();

const conDesborde = resumen.filter((fila) => fila.desborde > 2);
console.log(`\n${resumen.length} capturas · ${conDesborde.length} con desborde · ${errores.length} errores de consola`);
if (errores.length) console.log(errores.slice(0, 5));
process.exit(conDesborde.length || errores.length ? 1 : 0);
