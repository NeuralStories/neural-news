/**
 * Arranque de la beta en modo producción — multiplataforma (Node 20+).
 *
 * Levanta los tres procesos del producto, **desacoplados** (el lanzador termina
 * y los servicios siguen en marcha), y espera a que respondan:
 *   1. API    → http://127.0.0.1:8000   (salud en /api/v1/health)
 *   2. worker → cola de trabajos (sin URL)
 *   3. web    → http://localhost:3000    (build de producción)
 *
 * No depende de Bash, WSL ni cron: solo de `node`, `python` y `npm`, que ya
 * hacen falta para construir el proyecto.
 *
 * Uso:
 *   node scripts/beta_start.mjs      # arranca y termina
 *   node scripts/beta_stop.mjs       # para lo que arrancó
 *
 * Los PIDs quedan en `storage/logs/beta.pids.json` y los registros en
 * `storage/logs/`.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, openSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const LOGS = join(RAIZ, 'storage', 'logs');
const PIDS = join(LOGS, 'beta.pids.json');
const API_URL = process.env.NEURAL_BETA_API_URL || 'http://127.0.0.1:8000';
const WEB_URL = process.env.NEURAL_BETA_WEB_URL || 'http://localhost:3000';
const WINDOWS = process.platform === 'win32';

mkdirSync(LOGS, { recursive: true });

const log = (mensaje) => console.log(`[beta] ${mensaje}`);

/**
 * Lanza un proceso **desacoplado** con su salida en un fichero.
 *
 * Detalles que importan en Windows:
 *  - `npm` es un script de consola (`npm.cmd`): `spawn` sin shell falla con
 *    EINVAL, así que se invoca a través de `cmd.exe`;
 *  - la salida se encauza con el **descriptor del fichero** (un `pipe` con
 *    `detached` se rompe al salir el lanzador);
 *  - `detached: true` + `unref()`: el servicio sobrevive a la salida de este
 *    lanzador, que termina tras comprobar que todo responde.
 */
function lanzar(nombre, comando, argumentos, cwd) {
  const ruta = join(LOGS, `${nombre}.log`);
  const fd = openSync(ruta, 'a');
  const hijo = spawn(comando, argumentos, {
    cwd,
    env: { ...process.env, NEURAL_ENV: process.env.NEURAL_ENV || 'local' },
    detached: true,
    stdio: ['ignore', fd, fd],
    windowsHide: true,
  });
  hijo.unref();
  log(`${nombre} → PID ${hijo.pid} (registro: storage/logs/${nombre}.log)`);
  return hijo.pid;
}

/** `npm` en Windows es `npm.cmd`: se invoca a través de `cmd.exe`. */
function lanzarNpm(nombre, argumentos, cwd) {
  if (WINDOWS) {
    return lanzar(nombre, 'cmd.exe', ['/c', process.env.NEURAL_BETA_NPM || 'npm.cmd', ...argumentos], cwd);
  }
  return lanzar(nombre, process.env.NEURAL_BETA_NPM || 'npm', argumentos, cwd);
}

async function esperar(url, intentos = 60, pausaMs = 1000) {
  for (let i = 0; i < intentos; i += 1) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (r.ok) return true;
    } catch {
      /* todavía no responde */
    }
    await new Promise((r) => setTimeout(r, pausaMs));
  }
  return false;
}

const pids = {
  api: lanzar(
    'api',
    process.env.NEURAL_BETA_PYTHON || 'python',
    ['-m', 'uvicorn', 'neuralnews.main:app', '--host', '127.0.0.1', '--port', '8000'],
    join(RAIZ, 'apps', 'api'),
  ),
  worker: lanzar(
    'worker',
    process.env.NEURAL_BETA_PYTHON || 'python',
    ['-m', 'neuralnews.worker'],
    join(RAIZ, 'apps', 'api'),
  ),
  web: lanzarNpm(
    'web',
    ['run', 'start'],
    join(RAIZ, 'apps', 'web'),
  ),
};
writeFileSync(PIDS, JSON.stringify(pids, null, 2));

log('Esperando a que respondan…');
const apiArriba = await esperar(`${API_URL}/api/v1/health`);
const webArriba = await esperar(WEB_URL);

log(`API: ${apiArriba ? 'respondiendo' : 'SIN RESPONDER'} → ${API_URL}`);
log(`Web: ${webArriba ? 'respondiendo' : 'SIN RESPONDER'} → ${WEB_URL}`);
log(`PIDs: ${PIDS}`);
log('Para parar: node scripts/beta_stop.mjs');

if (!apiArriba || !webArriba) {
  log('Algún servicio no responde: revisa storage/logs/.');
  process.exitCode = 1;
}
