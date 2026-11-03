/**
 * Auditoría de la entrega: comprueba una por una las condiciones del encargo.
 *
 * No se fía de lo que dice el informe: lo comprueba contra el estado real
 * (el repositorio, los ficheros y la instancia en marcha).
 *
 * Uso:
 *   node scripts/auditar_entrega.mjs
 *
 * Salida: una línea por comprobación con PASA/FALLA y el detalle; al final, el
 * veredicto global. Código de salida 0 si todo pasa.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const VERSION = '1.0.0-beta.1';
const WEB = process.env.NEURAL_BETA_WEB_URL || 'http://localhost:3000';
const API = process.env.NEURAL_BETA_API_URL || 'http://127.0.0.1:8000';

const resultados = [];
function comprobar(nombre, ok, detalle = '') {
  resultados.push({ nombre, ok, detalle });
  console.log(`${ok ? 'PASA' : 'FALLA'}  ${nombre}${detalle ? ` — ${detalle}` : ''}`);
}

function git(...args) {
  return execFileSync('git', args, { cwd: RAIZ, encoding: 'utf-8' }).trim();
}

// --- Condición 1: «proyecto final» es la raíz real del repositorio Git -------
const toplevel = git('rev-parse', '--show-toplevel');
comprobar(
  'la raíz del repositorio es «proyecto final»',
  toplevel.replace(/\\/g, '/').endsWith('/proyecto final'),
  toplevel,
);
comprobar(
  '.git es un repositorio normal (no worktree ni submódulo)',
  existsSync(join(RAIZ, '.git')) && !existsSync(join(RAIZ, '.gitmodules')),
);
comprobar(
  'no existe «proyecto final/proyecto final»',
  !existsSync(join(RAIZ, 'proyecto final', 'proyecto final')),
);

// --- Condición 2: versión, commit y tag locales ------------------------------
const pkg = JSON.parse(readFileSync(join(RAIZ, 'apps', 'web', 'package.json'), 'utf-8'));
const pyproject = readFileSync(join(RAIZ, 'apps', 'api', 'pyproject.toml'), 'utf-8');
const initPy = readFileSync(join(RAIZ, 'apps', 'api', 'src', 'neuralnews', '__init__.py'), 'utf-8');
const versionWeb = readFileSync(join(RAIZ, 'apps', 'web', 'lib', 'version.ts'), 'utf-8');
const openapi = JSON.parse(readFileSync(join(RAIZ, 'docs', 'openapi.json'), 'utf-8'));
const versiones = {
  'apps/web/package.json': pkg.version,
  'apps/api/pyproject.toml': (pyproject.match(/^version\s*=\s*"([^"]+)"/m) || [])[1],
  'neuralnews/__init__.py': (initPy.match(/__version__\s*=\s*"([^"]+)"/) || [])[1],
  'apps/web/lib/version.ts': (versionWeb.match(/VERSION\s*=\s*"([^"]+)"/) || [])[1],
  'docs/openapi.json': openapi.info.version,
};
const distintas = Object.entries(versiones).filter(([, v]) => v !== VERSION);
comprobar(
  `la versión ${VERSION} es coherente en todo el repositorio`,
  distintas.length === 0,
  distintas.length ? JSON.stringify(distintas) : 'package.json · pyproject · __version__ · version.ts · openapi',
);

const rama = git('rev-parse', '--abbrev-ref', 'HEAD');
comprobar('existe la rama de release', rama === `release/${VERSION}`, rama);

const etiquetas = git('tag', '-l', `v${VERSION}`);
const anotado = git('cat-file', '-t', `v${VERSION}`) === 'tag';
comprobar(`existe el tag anotado v${VERSION}`, etiquetas === `v${VERSION}` && anotado, `tipo: ${anotado ? 'tag' : '?'}`);

const enRemoto = git('ls-remote', '--tags', 'origin', `v${VERSION}`);
comprobar('el tag NO se ha publicado (sin push)', enRemoto === '', enRemoto || 'no está en el remoto');

// --- Condición 3: la aplicación se lanza en local y responde ------------------
try {
  const r = await fetch(`${API}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
  const salud = await r.json();
  comprobar(
    'la API responde 200 con la versión de la beta',
    r.ok && salud.version === VERSION,
    `HTTP ${r.status} · v${salud.version} · ok=${salud.ok}`,
  );
} catch (e) {
  comprobar('la API responde 200 con la versión de la beta', false, String(e.message || e));
}
try {
  const r = await fetch(WEB, { signal: AbortSignal.timeout(5000) });
  comprobar('la web responde 200 en modo producción', r.ok, `HTTP ${r.status}`);
} catch (e) {
  comprobar('la web responde 200 en modo producción', false, String(e.message || e));
}

// --- Condición 4: resumen, documentación e informe dentro del proyecto -------
const documentos = [
  'README.md',
  'CHANGELOG.md',
  '.env.example',
  'docs/entrega/RESUMEN_COMPLETO.md',
  'docs/entrega/NOTAS_BETA.md',
  'docs/entrega/GUIA_PRUEBAS_BETA.md',
  'docs/entrega/INFORME_FINAL.md',
  'docs/entrega/RESUMEN_VERIFICACIONES.md',
  'docs/entrega/verificar.ps1',
  'docs/agente/ESTADO.md',
  'docs/agente/PLAN_MAESTRO.md',
  'docs/agente/PLAN.md',
  'docs/agente/TAREAS.md',
  'docs/agente/REGISTRO.md',
  'docs/entrega/evidencias/F1_linea_base.md',
  'docs/entrega/evidencias/F6_lanzamiento.md',
];
const faltan = documentos.filter((d) => !existsSync(join(RAIZ, d)));
comprobar(
  'la documentación de la entrega está dentro del proyecto',
  faltan.length === 0,
  faltan.length ? `faltan: ${faltan.join(', ')}` : `${documentos.length} documentos`,
);

// --- Verificación: 14 comprobaciones con veredicto y log ----------------------
const rutaResumen = join(RAIZ, 'docs', 'entrega', 'RESUMEN_VERIFICACIONES.md');
if (!existsSync(rutaResumen)) {
  comprobar('el resumen de verificaciones existe', false, rutaResumen);
  filas = [];
} else {
  const resumen = readFileSync(rutaResumen, 'utf-8');
  const filas = resumen.split('\n').filter((l) => l.startsWith('| ') && l.includes('**PASA**'));
  const conFallo = resumen.split('\n').filter((l) => l.startsWith('| ') && (l.includes('**FALLA**') || l.includes('**BLOQUEADA**')));
  comprobar(
    'las 14 comprobaciones de la entrega dan PASA',
    filas.length === 14 && conFallo.length === 0,
    `${filas.length} PASA · ${conFallo.length} con fallo`,
  );
}
const logs = ['pytest', 'tsc', 'eslint', 'build', 'playwright', 'check_clases', 'check_a11y',
  'scan_secrets', 'generate_estados', 'generar_manifiesto_studio', 'generar_plan_casillas',
  'exportar_openapi', 'auditar_evidencias', 'git_diff_check'];
const sinLog = logs.filter((n) => !existsSync(join(RAIZ, 'docs', 'entrega', 'evidencias', `${n}.log`)));
comprobar('cada comprobación tiene su log íntegro', sinLog.length === 0, sinLog.length ? sinLog.join(', ') : `${logs.length} logs`);

// --- Plan: fases completadas y aplazadas declaradas --------------------------
const plan = readFileSync(join(RAIZ, 'docs', 'agente', 'PLAN_MAESTRO.md'), 'utf-8');
const fases = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8'];
const fasesOk = fases.every((f) => new RegExp(`\\*\\*${f}\\*\\*.*\\| \\*\\*COMPLETADA\\*\\*`).test(plan));
comprobar('las ocho fases de la entrega están COMPLETADAS en el plan', fasesOk);
const aplazadas = ['DEC-02', 'SUP-01', 'SUP-02'];
const aplazadasOk = aplazadas.every((d) => new RegExp(`\\*\\*${d}\\*\\*.*\\| \\*\\*APLAZADA\\*\\*`).test(plan));
comprobar('DEC-02, SUP-01 y SUP-02 están APLAZADAS (no COMPLETADAS)', aplazadasOk);
const sinPendientes = !/\|\s*PENDIENTE\s*\|/.test(plan);
comprobar('el plan no tiene ninguna fila PENDIENTE', sinPendientes);

// --- El checkpoint tiene los dos juegos de campos ----------------------------
const estado = readFileSync(join(RAIZ, 'docs', 'agente', 'ESTADO.md'), 'utf-8');
const titulos = ['Última actualización', 'Capacidades disponibles', 'Tarea actual y estado',
  'Último punto verificado', 'Trabajo a medias sin verificar', 'Archivos modificados desde el último checkpoint',
  'Bloqueos', 'Autorizaciones pendientes', 'Cuota', 'Estado beta', 'PRÓXIMA ACCIÓN EXACTA'];
const faltanTitulos = titulos.filter((t) => !estado.includes(t));
const alias = ['ultima_actualizacion', 'capacidades', 'tarea_actual', 'ultimo_punto_verificado',
  'trabajo_sin_verificar', 'archivos_modificados', 'bloqueos', 'autorizaciones_pendientes',
  'cuota', 'estado_beta', 'proxima_accion_exacta'];
const faltanAlias = alias.filter((a) => !estado.includes(a));
comprobar(
  'el checkpoint tiene los títulos en español y los alias en snake_case',
  faltanTitulos.length === 0 && faltanAlias.length === 0,
  [...faltanTitulos, ...faltanAlias].join(', ') || 'los 11 campos',
);
// El estado beta se declara una sola vez (con el alias en snake_case, que en
// markdown va entre acentos graves: «`estado_beta`: BETA_LISTA»).
const declaraciones = estado.match(/estado_beta`?\s*:\s*`?\s*(BETA_[A-Z_]+)/g) || [];
comprobar(
  'el checkpoint declara un único estado beta',
  declaraciones.length === 1 && /estado_beta`?\s*:\s*`?\s*BETA_LISTA/.test(estado),
  declaraciones.join(', ') || 'sin declaración',
);

const fallos = resultados.filter((r) => !r.ok);
console.log(`\n${resultados.length - fallos.length}/${resultados.length} comprobaciones PASA.`);
if (fallos.length) {
  console.log('FALLA la auditoría de la entrega.');
  process.exit(1);
}
console.log('PASA la auditoría de la entrega.');
