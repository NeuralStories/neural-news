# TAREAS — cola operativa de neural.news

Cola corta de lo que **queda por hacer** tras la beta `1.0.0-beta.1`. El plan completo
(89 tareas de producto, todas completadas) está en `PLAN_MAESTRO.md`; su espejo con
casillas —el que valida el supervisor externo— está en `PLAN.md` (generado por
`tools/generar_plan_casillas.py`).

## Estado de la cola

| id | estado | qué hace falta | evidencia |
|---|---|---|---|
| `DEC-01` | **COMPLETADA** | La gobernanza (`newsV2/`) dentro de Git, solo si cumplía las 4 condiciones | `docs/gobernanza/` (328 ficheros, 15,2 MB): 0 hallazgos de secretos, ningún fichero > 50 MB, sin artefactos generados. Lo que no cumplía (`newsV2/neural-news/`, copia duplicada con su propio `.git`; `newsV2/flow-recovery/node_modules`, con un `.node` de 105 MB) queda **fuera y anotado** en el plan y en el informe final |
| `DEC-02` | **APLAZADA** (post-beta) | Crear un remoto remoto de git (GitHub/GitLab). El remoto actual es local (`.remotes/neural-news.git`): es una acción externa | Sección 0 del `/goal` |
| `SUP-01` | **APLAZADA** (post-beta) | Rellenar `AGENTE_CMD` en `supervisor.sh:5` con el comando real que lanza el agente en esta máquina. Sigue siendo un marcador de posición | Sección 0 del `/goal` |
| `SUP-02` | **APLAZADA** (post-beta) | Configurar el relanzamiento automático (`crontab` + WSL/Git Bash). En esta máquina WSL no arranca (virtualización desactivada) | Sección 0 del `/goal` |

## Por qué estas filas no son `[ ]` en `PLAN.md`

`PLAN.md` es la lista que el supervisor valida con `grep -q "\[ \]"`: si hay una casilla
pendiente, el supervisor **nunca** da el proyecto por terminado y sigue relanzando el
agente. Estas entradas **no son tareas ejecutables**: dos necesitan una decisión humana y
dos dependen del entorno. Por eso viven aquí (y en `ESTADO.md`), no como casillas.

Si en algún momento se autoriza `DEC-02` o `SUP-01`/`SUP-02`, la fila correspondiente
**pasa a ser una tarea** y se refleja en `PLAN_MAESTRO.md` → `PLAN.md` con su casilla `[ ]`.

## Cola de la entrega (cerrada)

| fase | estado |
|---|---|
| F1 · diagnóstico | COMPLETADA (`docs/entrega/evidencias/F1_linea_base.md`) |
| F2 · reubicación a `proyecto final` | COMPLETADA |
| F3 · verificación técnica | COMPLETADA (14/14, `docs/entrega/RESUMEN_VERIFICACIONES.md`) |
| F4 · preparación de la beta | COMPLETADA (versión, CHANGELOG, `.env.example`, auditorías, DEC-01) |
| F5 · documentación | COMPLETADA |
| F6 · lanzamiento local | COMPLETADA (`docs/entrega/evidencias/F6_lanzamiento.md`) |
| F7 · rama, commit y tag | COMPLETADA |
| F8 · cierre | COMPLETADA (`docs/entrega/INFORME_FINAL.md`) |

## Comprobación de sincronía

`PLAN.md` se genera desde `PLAN_MAESTRO.md`; si se desfasan, falla
`tests/test_plan_casillas.py` (y el paso de CI `tools/generar_plan_casillas.py --check`).
