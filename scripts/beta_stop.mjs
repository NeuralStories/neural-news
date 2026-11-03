/**
 * Parada de la beta — multiplataforma (Node 20+).
 *
 * Lee los PIDs que dejó `scripts/beta_start.mjs` y detiene **solo** esos
 * procesos, incluidos sus hijos (`cmd.exe` → `python`/`node`): no busca por
 * nombre de proceso, así que no puede parar nada ajeno.
 *
 * Uso:
 *   node scripts/beta_stop.mjs
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync, unlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const PIDS = join(RAIZ, 'storage', 'logs', 'beta.pids.json');
const WINDOWS = process.platform === 'win32';

if (!existsSync(PIDS)) {
  console.log('[beta] No hay PIDs registrados: no hay nada que parar.');
  process.exit(0);
}

let pids = {};
try {
  pids = JSON.parse(readFileSync(PIDS, 'utf-8'));
} catch (err) {
  console.error(`[beta] No se pudo leer ${PIDS}: ${err.message}`);
  process.exit(1);
}

let parados = 0;
for (const [nombre, pid] of Object.entries(pids)) {
  try {
    if (WINDOWS) {
      // /T mata también los hijos (cmd.exe → python / node).
      const r = spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { encoding: 'utf-8' });
      if (r.status !== 0) {
        console.log(`[beta] ${nombre} (PID ${pid}) ya no estaba en marcha.`);
        continue;
      }
    } else {
      // El proceso se lanzó desacoplado: es líder de su grupo de procesos.
      process.kill(-Number(pid), 'SIGTERM');
    }
    console.log(`[beta] Detenido ${nombre} (PID ${pid}).`);
    parados += 1;
  } catch (err) {
    console.log(`[beta] ${nombre} (PID ${pid}) ya no estaba en marcha.`);
  }
}

try { unlinkSync(PIDS); } catch { /* da igual */ }
console.log(`[beta] Pila parada (${parados} proceso(s)).`);
