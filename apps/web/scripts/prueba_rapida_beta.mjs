/**
 * Prueba rápida de la beta **contra una instancia ya levantada**.
 *
 * El E2E completo (`npx playwright test`) levanta su propia pila. Esta prueba
 * es la otra mitad de la comprobación de F6: verifica que la instancia que se
 * dejó en marcha (arrancada con `scripts/beta_start.mjs` o `scripts/start.ps1`)
 * **responde de verdad** en un navegador real.
 *
 * Uso:
 *   node scripts/prueba_rapida_beta.mjs [URL]      (por defecto http://localhost:3000)
 *
 * Salida: una línea por comprobación y `PASA`/`FALLA` al final. Código de
 * salida 0 si todo pasa.
 */
import { chromium } from 'playwright';

const URL_BASE = process.argv[2] || 'http://localhost:3000';
const API_URL = process.env.NEURAL_BETA_API_URL || 'http://127.0.0.1:8000';

const comprobaciones = [];
function registrar(nombre, ok, detalle = '') {
  comprobaciones.push({ nombre, ok, detalle });
  console.log(`${ok ? 'PASA' : 'FALLA'}  ${nombre}${detalle ? ` — ${detalle}` : ''}`);
}

const navegador = await chromium.launch({ channel: 'msedge' });
try {
  const pagina = await navegador.newPage();
  const errores = [];
  const recursosFallidos = [];
  pagina.on('pageerror', (e) => errores.push(String(e)));
  pagina.on('console', (m) => {
    if (m.type() === 'error') {
      const lugar = m.location();
      errores.push(`${m.text()} @ ${lugar ? lugar.url : '?'}`);
    }
  });
  pagina.on('response', (r) => {
    if (r.status() >= 400) recursosFallidos.push(`${r.status()} ${r.url()}`);
  });

  // 1. La web responde y es la de neural.news.
  const respuesta = await pagina.goto(URL_BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
  registrar('la web responde', Boolean(respuesta && respuesta.ok()), `HTTP ${respuesta ? respuesta.status() : '—'}`);

  // 2. Se ve la pantalla de acceso.
  await pagina.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  const hayBotonDemo = await pagina.getByRole('button', { name: 'Entrar en modo demo' }).isVisible().catch(() => false);
  registrar('la pantalla de acceso ofrece el modo demo', hayBotonDemo);

  // 3. Se entra y aparece el producto.
  if (hayBotonDemo) {
    await pagina.getByRole('button', { name: 'Entrar en modo demo' }).click();
    const nav = pagina.getByRole('link', { name: 'Fuentes' }).first();
    await nav.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
    registrar('el modo demo abre el producto', await nav.isVisible().catch(() => false));
  }

  // 4. La versión de la beta aparece en el pie.
  const pie = await pagina.locator('footer').innerText().catch(() => '');
  registrar('el pie declara la versión de la beta', pie.includes('1.0.0-beta.1'), pie.replace(/\s+/gu, ' ').slice(0, 80));

  // 5. Sin errores de JavaScript ni recursos rotos en el navegador.
  registrar('sin errores de JavaScript en el navegador', errores.length === 0, errores.slice(0, 2).join(' | '));
  registrar('sin recursos rotos (404/500)', recursosFallidos.length === 0, recursosFallidos.slice(0, 3).join(' | '));

  // 6. La API responde con la misma versión.
  const salud = await fetch(`${API_URL}/api/v1/health`).then((r) => r.json()).catch(() => null);
  registrar('la API responde con la versión de la beta', salud?.version === '1.0.0-beta.1', salud ? `v${salud.version}` : 'sin respuesta');
} finally {
  await navegador.close();
}

const fallos = comprobaciones.filter((c) => !c.ok);
console.log(`\n${comprobaciones.length - fallos.length}/${comprobaciones.length} comprobaciones PASA.`);
if (fallos.length) {
  console.log('FALLA la prueba rápida de la beta.');
  process.exit(1);
}
console.log('PASA la prueba rápida de la beta.');
