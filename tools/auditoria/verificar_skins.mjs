// Verificación del selector de skins: cambia `data-skin` y el fondo real.
import playwright from "../../apps/web/node_modules/@playwright/test/index.js";

const { chromium } = playwright;
const BASE = process.env.NEURAL_WEB_URL || "http://localhost:3000";

const navegador = await chromium.launch({ channel: "msedge" });
const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
await pagina.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });

const selector = pagina.locator("select").first();
await selector.waitFor({ state: "visible", timeout: 20_000 });

const opciones = await selector.locator("option").allTextContents();
console.log("skins en el selector:", opciones.join(" · "));

const fondos = {};
for (const skin of opciones) {
  const valor = await selector.locator("option", { hasText: skin }).first().getAttribute("value");
  await selector.selectOption(valor);
  await pagina.waitForTimeout(400);
  const estado = await pagina.evaluate(() => ({
    skin: document.documentElement.dataset.skin ?? "base",
    fondo: getComputedStyle(document.body).backgroundColor,
    guardado: localStorage.getItem("neural.skin"),
  }));
  fondos[skin] = estado;
  console.log(
    `${skin.padEnd(20)} data-skin=${String(estado.skin).padEnd(10)} fondo=${estado.fondo} localStorage=${estado.guardado}`,
  );
}

// La skin debe sobrevivir a una recarga (aplicada antes del primer pintado).
await selector.selectOption("fosforo");
await pagina.reload({ waitUntil: "domcontentloaded" });
const trasRecarga = await pagina.evaluate(() => ({
  skin: document.documentElement.dataset.skin ?? "base",
  fondo: getComputedStyle(document.body).backgroundColor,
}));
console.log("tras recargar con «fosforo»:", JSON.stringify(trasRecarga));

const distintos = new Set(Object.values(fondos).map((f) => f.fondo));
console.log(`\n${opciones.length} skins · ${distintos.size} fondos distintos`);
await navegador.close();
process.exit(distintos.size >= 2 && trasRecarga.skin === "fosforo" ? 0 : 1);
