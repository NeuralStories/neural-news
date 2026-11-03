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

/**
 * Lista los procesos vivos con su línea de comandos.
 * @returns {{pid: number, cmd: string}[]}
 */
function listarProcesos() {
  if (WINDOWS) {
    const powershell =
      "Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress";
    const r = spawnSync('powershell.exe', ['-NoProfile', '-Command', powershell], {
      encoding: 'utf-8',
    });
    if (r.status !== 0 || !r.stdout) return [];
    let datos;
    try {
      datos = JSON.parse(r.stdout);
    } catch {
      return [];
    }
    if (!Array.isArray(datos)) datos = datos ? [datos] : [];
    return datos
      .filter((p) => p && p.CommandLine)
      .map((p) => ({ pid: Number(p.ProcessId), cmd: String(p.CommandLine) }));
  }
  const r = spawnSync('ps', ['-eo', 'pid=,args='], { encoding: 'utf-8' });
  if (r.status !== 0 || !r.stdout) return [];
  return r.stdout
    .split('\n')
    .map((linea) => linea.trim())
    .filter(Boolean)
    .map((linea) => {
      const corte = linea.indexOf(' ');
      return {
        pid: Number(linea.slice(0, corte)),
        cmd: linea.slice(corte + 1),
      };
    })
    .filter((p) => Number.isFinite(p.pid));
}

/**
 * ¿Es un proceso de **este** proyecto?
 *
 * Se reconoce por los módulos propios (`neuralnews.main:app`,
 * `neuralnews.worker`) y, para el servidor de Next, por que su línea de
 * comandos contenga la ruta de `apps/web` de este repositorio. No se busca por
 * nombre de proceso genérico: no se puede parar nada ajeno.
 */
function esDelProyecto({ cmd }) {
  if (/neuralnews\.main:app/.test(cmd)) return true;
  if (/-m\s+neuralnews\.worker/.test(cmd)) return true;
  const web = join(RAIZ, 'apps', 'web').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`${web}[\\\\/]`).test(cmd);
}

function detener(pid) {
  if (WINDOWS) {
    spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { encoding: 'utf-8' });
    return true;
  }
  try {
    process.kill(pid, 'SIGTERM');
    return true;
  } catch {
    return false;
  }
}

if (!existsSync(PIDS)) {
  console.log('[beta] No hay PIDs registrados: se barre lo que quede en marcha.');
} else {
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
  console.log(`[beta] Pila parada (${parados} proceso(s)).`);
}

try { unlinkSync(PIDS); } catch { /* da igual */ }

// Barrido de seguridad: un proceso que se quedó huérfano (por ejemplo, si la
// pila se arrancó con `scripts/start.ps1` en vez de con este script) no debe
// sobrevivir a la parada ni dejar el puerto ocupado.
const huerfanos = listarProcesos().filter(esDelProyecto);
if (huerfanos.length > 0) {
  for (const { pid, cmd } of huerfanos) {
    console.log(`[beta] Huérfano detectado (PID ${pid}): ${cmd.slice(0, 120)}`);
    detener(pid);
  }
  console.log(`[beta] ${huerfanos.length} proceso(s) huérfano(s) detenido(s).`);
} else {
  console.log('[beta] Sin procesos huérfanos.');
}
