// Diagnóstico: qué peticiones fallan (404/500) en cada vista.
import playwright from "../../apps/web/node_modules/@playwright/test/index.js";

const { chromium } = playwright;

const BASE = process.env.NEURAL_WEB_URL || "http://localhost:3000";
const RUTAS = ["/", "/fuentes", "/noticias", "/estudio", "/lotes", "/configuracion", "/ops"];

const navegador = await chromium.launch({ channel: "msedge" });
const pagina = await navegador.newPage();

await pagina.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
const entrar = pagina.getByRole("button", { name: "Entrar en modo demo" });
const visible = await entrar
  .waitFor({ state: "visible", timeout: 20_000 })
  .then(() => true)
  .catch(() => false);
if (visible) {
  await entrar.click();
  await pagina.waitForURL(/\/(fuentes|noticias|estudio|ops)/, { timeout: 30000 });
}

for (const ruta of RUTAS) {
  const fallos = [];
  const listener = (respuesta) => {
    if (respuesta.status() >= 400) fallos.push(`${respuesta.status()} ${respuesta.url()}`);
  };
  pagina.on("response", listener);
  await pagina.goto(`${BASE}${ruta}`, { waitUntil: "domcontentloaded" });
  await pagina.waitForTimeout(1500);
  pagina.off("response", listener);
  console.log(`${ruta.padEnd(16)} ${fallos.length ? fallos.join(" | ") : "sin fallos"}`);
}

await navegador.close();
