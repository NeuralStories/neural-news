# ESTADO — checkpoint de neural.news

> Checkpoint del plan maestro. Cada campo obligatorio aparece con su nombre
> **exacto**; los dos contratos de `/goal` que se han usado en el proyecto
> nombran los campos de forma distinta, así que se dan **los dos_alias**
> (`ultima_actualizacion` = «Última actualización», etc.). Sin secretos ni
> credenciales.

## Última actualización

**2026-11-02 23:56 (Europe/Madrid)** — Plan maestro **cerrado**: las 89 filas de tarea están
**COMPLETADAS** (0 PENDIENTES, 0 BLOQUEADAS). HEAD `0034bc9` en `beta/v1`, empujado a
`origin beta/v1`, árbol de trabajo limpio.

- `ultima_actualizacion`: 2026-11-02 23:56 (Europe/Madrid)
- `plan_actual`: `neural-news/docs/agente/PLAN_MAESTRO.md` (89 filas de tarea, todas
  COMPLETADAS) · espejo con casillas en `docs/agente/PLAN.md` (89/89 `[x]`) · cola operativa en
  `docs/agente/TAREAS.md` · decisiones y hallazgos en `docs/agente/REGISTRO.md`

## Capacidades disponibles

- **archivos persistentes:** ✓ (repositorio, `docs/agente/` y `evidence/` en disco)
- **internet:** ✓ (disponible; no ha hecho falta en este tramo)
- **cuota consultable:** **NO** — no existe herramienta de consulta de cuota ni de saldo
- **programador (tareas programadas):** ✓ (`cron_create` verificado; `cron_read list` → **0
  tareas**, nada pendiente de cancelar) · **pero** el `supervisor.sh` es Bash con `crontab` y en
  esta máquina **WSL no arranca** (virtualización desactivada): **no hay ningún `crontab`
  configurado**

- `capacidades_disponibles`: archivos ✓ · internet ✓ · cuota **no consultable** ·
  programador externo ✓ (sin tareas activas) · Bash/WSL **parcial** (WSL no arranca)

## Tarea actual y estado

**Ninguna: PLAN COMPLETADO.** Las 89 filas de `PLAN_MAESTRO.md` están COMPLETADAS con evidencia y
las 89 casillas de `PLAN.md` están marcadas `[x]`.

- `task_actual`: ninguna — plan completado (0 PENDIENTES, 0 BLOQUEADAS), commit `0034bc9`

## Último punto verificado

**Verificación final completa, ejecutada sobre el árbol limpio en `0034bc9`:**

- `python -m pytest tests -q` → **exit 0** (**343 tests**, 1 skip)
- `npx tsc --noEmit` → **0 errores** · `npx eslint .` → **0 problemas** · `npm run build` → compila
- `npx playwright test` → **8 passed** (la pila la levanta el propio Playwright:
  `reuseExistingServer: false`)
- `python tools/check_clases.py` → **0 reimplementaciones en línea**, 0 clases inexistentes
- `python tools/check_a11y.py` → **0 bloqueantes · 0 avisos**
- `python tools/scan_secrets.py .` → **0 hallazgos de secretos**
- `python tools/generate_estados.py --check`, `tools/generar_manifiesto_studio.py --check` y
  `tools/generar_plan_casillas.py --check` → **al día**
- `python tools/exportar_openapi.py --check` → el contrato exportado coincide con el servido
- `python tools/auditar_evidencias.py` → **84 referencias de evidencia comprobadas y existentes**,
  9 fuera del repositorio (artefactos sellados), 3 que no son rutas, **0 desfasadas**: ninguna fila
  completada cita un fichero que ya no exista
- `scripts\bootstrap.ps1` ejecutado de extremo a extremo → **exit 0** (requisitos → backend → `.env`
  → migraciones → web → suite verde) y `scripts\start.ps1` levanta API+worker+web (web 200)

- `ultimo_punto_verificado`: lo anterior, todo ejecutado en esta sesión sobre `0034bc9`

## Trabajo a medias sin verificar

**Nada.** El árbol de trabajo está limpio (0 ficheros modificados) y todo lo verificado está
commiteado y empujado.

- `trabajo_parcial_sin_verificar`: ninguno

## Archivos modificados desde el último checkpoint

Ninguno desde `0034bc9`. En los lotes anteriores: `docs/agente/{PLAN_MAESTRO,PLAN,REGISTRO,
ESTADO,TAREAS}.md`, `docs/adr/ADR-022-descartes-del-port.md`, `docs/openapi.json`,
`evidence/instalacion_desde_clon_limpio.md`, `PROMPT.md`, `supervisor.sh`.

- `archivos_tocados_desde_checkpoint`: ninguno (checkpoint = commit `0034bc9`)

## Bloqueos y lo que se necesita para resolverlos

**Ninguno técnico.** No hay ninguna task BLOQUEADA: lo que queda son decisiones del propietario
(«Autorizaciones pendientes») y dos puntos de entorno del supervisor.

- `bloqueos`: ninguno

## Autorizaciones pendientes

1. **R-26 — la gobernanza (`newsV2/`) sigue fuera de todo repositorio** (sin historial, sin
   remoto, sin copia). Decidir: (a) moverla a `neural-news/docs/governance/` y redirigir las
   referencias documentadas, o (b) versionarla como repositorio propio. Cambia el alcance de rutas
   ya documentadas → **no se ejecuta sin autorización**.
2. **Crear un remoto remoto de git** (GitHub/GitLab): el remoto actual es local
   (`.remotes/neural-news.git`). Acción externa → **no se ejecuta sin autorización**.
3. **`SUP-01`** — rellenar `AGENTE_CMD` en `supervisor.sh:5` con el comando real de esta máquina
   (ahora es un marcador de posición).
4. **`SUP-02`** — el `supervisor.sh` es Bash y usa `crontab`: en Windows hace falta WSL o Git Bash
   con cron. **No se ha configurado ningún `crontab`** porque no hay un programador real
   verificado en este sistema.

- `autorizaciones_pendientes`: las cuatro anteriores

## Cuota y fecha de reinicio

**desconocido.** No existe herramienta de consulta de cuota o de saldo en esta plataforma, así que
**no se inventa ningún dato**. Lo único comprobable es que la ejecución continúa (requests y
tiempo acumulados) sin que se haya notificado ningún límite; eso no es un saldo.

- `cuota`: desconocido

## Reanudación automática

**NO_DISPONIBLE** — no procede: el proyecto está **COMPLETADO** y el contrato exige cancelar los
relanzamientos pendientes en ese caso. El mecanismo externo **sí existe** (`cron_create`, comprobado
con `cron_read list` → **0 tareas programadas**, así que no hay nada que cancelar) y **no** se
configura: relanzar un plan cerrado no aporta nada. Si se autoriza alguna de las decisiones
anteriores, ahí sí procede un relanzamiento real con la instrucción «lee `docs/agente/ESTADO.md` y
continúa desde `PRÓXIMA ACCIÓN EXACTA`».

- `reanudacion_automatica`: NO_DISPONIBLE

**Supervisor externo (añadido por petición del propietario).** `PROMPT.md` (el prompt del agente) y
`supervisor.sh` (el guion de Bash que lo relanza, lee sus etiquetas y gestiona la espera por cuota)
están en la raíz del repositorio. El supervisor usa `docs/agente/PLAN.md` —el espejo con casillas
del plan maestro— y su marcador `docs/agente/TERMINADO`. `docs/agente/TERMINADO` está **ignorado
por git** (es estado de máquina): por eso el supervisor no relanza. **Para retomar el trabajo
pendiente, bórralo.**

## PRÓXIMA ACCIÓN EXACTA

**Esperar la decisión del propietario** sobre `docs/agente/TAREAS.md` → filas `DEC-01` (mover
`newsV2/` al control de versiones) y `DEC-02` (crear un remoto remoto), y `SUP-01`/`SUP-02`
(activar el supervisor). Si se autoriza alguna, ejecutarla **empezando por `DEC-01`**: mover
`C:\Users\haxth3\Documents\NeuralStories\newsV2` a
`C:\Users\haxth3\Documents\NeuralStories\neural-news\docs\governance`, redirigir las rutas
documentadas que la apuntan (`ESTADO_REAL.md:5`, `docs/agente/PLAN_MAESTRO.md`,
`docs/agente/REGISTRO.md`, `newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md`) y commitearlo en
`beta/v1`.

- `proxima_accion_exacta`: la anterior (una sola acción concreta y ejecutable)

---

## Contexto mínimo para reanudar sin historial

- **Repositorio activo:** `C:\Users\haxth3\Documents\NeuralStories\neural-news`, rama `beta/v1`.
  Remoto: `.remotes/neural-news.git` (local). HEAD `0034bc9`.
- **Hermano congelado:** `archive/neuralnews-20261101/` (fuera de git por `.gitignore`): es
  **fuente de capacidades**, no un segundo producto (ADR-016).
- **Cómo se verifica todo (comandos que funcionan tal cual):**

```powershell
cd "C:\Users\haxth3\Documents\NeuralStories\neural-news"
python -m pytest tests -q                     # exit 0 (343 tests)
python tools\check_clases.py                  # 0 reimplementaciones
python tools\check_a11y.py                    # 0 bloqueantes
python tools\scan_secrets.py .                # 0 hallazgos
python tools\auditar_evidencias.py            # 0 desfasadas
cd apps\web
npx tsc --noEmit                              # 0 errores
npx eslint .                                  # 0 problemas
npx playwright test                            # 8 passed (levanta su propia pila)
```

- **Dos reglas aprendidas que evitan perder otra tanda de E2E** (ver `REGISTRO.md`, B32/B33):
  1. **Antes de `npm run build` o de un E2E: `scripts\stop.ps1`.** Un `next start` vivo sirve un
     build viejo → chunks 400 → la página no hidrata → el E2E se agota esperando un botón.
  2. **Ninguna herramienta que importe la aplicación puede tocar la base viva** (importar la
     aplicación aplica migraciones): `tools/exportar_openapi.py` usa ya una base aislada.
