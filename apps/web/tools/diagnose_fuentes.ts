/**
 * Reproduce el error de cliente en /fuentes y volcar la consola del navegador.
 * Uso: npx tsx tools/diagnose_fuentes.ts
 */
import { chromium, devices } from "@playwright/test";

async function main() {
  const errores: string[] = [];
  const navegador = await chromium.launch({ channel: "msedge" });
  const contexto = await navegador.newContext({ ...devices["Desktop Edge"], locale: "es-ES" });
  const pagina = await contexto.newPage();

  pagina.on("console", (m) => {
    if (m.type() === "error") errores.push(`[console] ${m.text()}`);
  });
  pagina.on("pageerror", (e) => errores.push(`[pageerror] ${e.message}\n${e.stack ?? ""}`));

  await pagina.goto("http://localhost:3000/", { waitUntil: "domcontentloaded" });
  console.log("home cargada");
  await pagina.getByRole("button", { name: "Entrar en modo demo" }).click();
  await pagina.waitForTimeout(5000);
  console.log("url actual:", pagina.url());
  console.log("--- errores ---");
  for (const e of errores) console.log(e);
  if (!errores.length) console.log("(sin errores de consola)");
  await navegador.close();
}

main().catch((e) => {
  console.error("FALLO:", e);
  process.exit(1);
});
