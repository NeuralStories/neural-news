// Diagnóstico: ¿se pierde la sesión tras el acceso demo?
import playwright from "../../apps/web/node_modules/@playwright/test/index.js";

const { chromium } = playwright;
const BASE = process.env.NEURAL_WEB_URL || "http://localhost:3000";

const navegador = await chromium.launch({ channel: "msedge" });
const contexto = await navegador.newContext();
const pagina = await contexto.newPage();

const respuestas = [];
pagina.on("response", (r) => {
  if (r.url().includes("/api/")) respuestas.push(`${r.status()} ${r.request().method()} ${r.url()}`);
});

await pagina.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
const boton = pagina.getByRole("button", { name: "Entrar en modo demo" });
console.log("boton de acceso:", await boton.count());
await boton.click();
await pagina.waitForURL(/\/fuentes/, { timeout: 30000 }).catch(() => console.log("no navegó a /fuentes"));
await pagina.waitForTimeout(1500);

const cookies = await contexto.cookies();
console.log("cookies:", cookies.map((c) => `${c.name} (path=${c.path}, httpOnly=${c.httpOnly})`));
console.log("me desde la página:", await pagina.evaluate(async () => {
  const r = await fetch("/api/v1/auth/me", { credentials: "include" });
  return `${r.status} ${(await r.text()).slice(0, 120)}`;
}));
console.log("respuestas de la API:");
for (const linea of respuestas) console.log("  ", linea);

await navegador.close();
