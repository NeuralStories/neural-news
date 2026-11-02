# TAREAS — cola operativa de neural.news

Cola corta de lo que **queda por hacer**. El plan completo (89 tareas, todas completadas) está en
`PLAN_MAESTRO.md`; su espejo con casillas —el que valida el supervisor externo— está en `PLAN.md`
(generado por `tools/generar_plan_casillas.py`).

## Estado de la cola

| id | estado | qué hace falta | evidencia |
|---|---|---|---|
| `DEC-01` | **PENDIENTE (decisión humana)** | Autorizar mover `newsV2/` al control de versiones (riesgo **R-26**). Dos caminos: (a) moverlo a `neural-news/docs/governance/` y redirigir las rutas documentadas, o (b) versionarlo como repositorio propio. Es una acción que cambia el alcance de rutas ya documentadas → **no se ejecuta sin autorización** | `docs/agente/ESTADO.md` → «autorizaciones_pendientes» · `REGISTRO.md` (R-26) |
| `DEC-02` | **PENDIENTE (decisión humana)** | Autorizar crear un **remoto remoto** de git (GitHub/GitLab) con credenciales. El remoto actual es local (`.remotes/neural-news.git`). Acción externa → **no se ejecuta sin autorización** | `docs/agente/ESTADO.md` → «autorizaciones_pendientes» |
| `SUP-01` | **PENDIENTE (decisión humana)** | Rellenar `AGENTE_CMD` en `supervisor.sh` con el comando real que lanza el agente en esta máquina. La línea viene como marcador (`tu_comando_de_agente_aqui --prompt PROMPT.md`): sin ella el supervisor no ejecuta nada | `supervisor.sh:5` |
| `SUP-02` | **PENDIENTE (entorno)** | El `supervisor.sh` es **Bash** (Linux/macOS) y usa `crontab`. En esta máquina (Windows) hace falta WSL o Git Bash con cron: no se ha configurado ningún `crontab` porque **no hay un planificador real verificado en este sistema** | `supervisor.sh` (encabezado «CONFIGURACIÓN») |

## Por qué estas cuatro no son `[ ]` en `PLAN.md`

`PLAN.md` es la lista que el supervisor valida con `grep -q "\[ \]"`: si hay una casilla pendiente,
el supervisor **nunca** da el proyecto por terminado y sigue relanzando el agente. Las cuatro
entradas de arriba **no son tareas ejecutables**: dos necesitan una decisión humana y dos dependen
del entorno. Por eso viven aquí (y en `ESTADO.md`), no como casillas.

Si en algún momento se autoriza `DEC-01` o `DEC-02`, la fila correspondiente **pasa a ser una
tarea** y se refleja en `PLAN_MAESTRO.md` → `PLAN.md` con su casilla `[ ]`.

## Comprobación de sincronía

`PLAN.md` se genera desde `PLAN_MAESTRO.md`; si se desfasan, falla
`tests/test_plan_casillas.py` (y el paso de CI `tools/generar_plan_casillas.py --check`).
