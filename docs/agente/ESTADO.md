# ESTADO — checkpoint de neural.news

> Formato según el contrato vigente del `/goal`: cada campo obligatorio está
> presente con su nombre exacto. Sin secretos ni credenciales.

- **ultima_actualizacion:** 2026-11-02 21:30 (Europe/Madrid)
- **plan_actual:** `neural-news/docs/agente/PLAN_MAESTRO.md` (89 filas de tarea, todas COMPLETADAS) ·
  cola operativa en `neural-news/docs/agente/TAREAS.md` · decisiones y hallazgos en
  `neural-news/docs/agente/REGISTRO.md`
- **task_actual:** ninguna — **PLAN COMPLETADO** (0 PENDIENTES, 0 BLOQUEADAS). Commit
  `ea8486d` en `beta/v1`, empujado a `origin beta/v1`.
- **capacidades_disponibles:** **archivos persistentes** ✓ (repositorio y `docs/agente/` en disco) ·
  **internet** ✓ (disponible, no usado en este tramo) · **cuota consultable: NO** (no hay
  herramienta de consulta de cuota ni de saldo) · **programador externo: SÍ** (`cron_create`
  verificado; hoy sin tareas) · **ejecución de Bash/WSL: parcial** (WSL no arranca: la
  virtualización está desactivada, así que el `supervisor.sh` **no** se ha podido ejecutar aquí).
- **ultimo_punto_verificado:** **Verificación final completa, ejecutada sobre el árbol limpio en
  `ea8486d`:**
  - `python -m pytest tests -q` → **exit 0** (332 tests, 1 skip)
  - `npx tsc --noEmit` → **0 errores** · `npx eslint .` → **0 problemas** · `npm run build` → compila
  - `npx playwright test` → **8 passed (1,6 min)** (pila levantada por el propio Playwright)
  - `python tools/check_clases.py` → **0 reimplementaciones en línea**, 0 clases inexistentes
  - `python tools/check_a11y.py` → **0 bloqueantes · 0 avisos**
  - `python tools/scan_secrets.py .` → **0 hallazgos de secretos** (0 avisos de ejemplo)
  - `python tools/generate_estados.py --check` y `tools/generar_manifiesto_studio.py --check` → al día
  - `python tools/exportar_openapi.py --check` → el contrato exportado coincide con el servido
  - `python tools/auditar_evidencias.py` → **84 referencias de evidencia comprobadas y
    existentes, 9 fuera del repositorio (artefactos sellados), 0 desfasadas**: ninguna fila
    completada cita un fichero que ya no exista (B35 corregido: la primera versión no
    comprobaba los ficheros y se citaba a sí misma)
  - `python tools/generar_plan_casillas.py --check` → `PLAN.md` (89/89 `[x]`) al día
  - `scripts\bootstrap.ps1` ejecutado de extremo a extremo → **exit 0** (requisitos → backend →
    `.env` → migraciones → web → suite verde) y `scripts\start.ps1` levanta API+worker+web (web 200)
- **trabajo_parcial_sin_verificar:** nada. El árbol de trabajo está limpio (0 ficheros modificados)
  y todo lo verificado está commiteado y empujado.
- **archivos_tocados_desde_checkpoint:** ninguno (checkpoint = commit `ea8486d`).
  En los lotes anteriores: `docs/agente/{PLAN_MAESTRO,REGISTRO,ESTADO}.md`,
  `docs/adr/ADR-022-descartes-del-port.md`, `docs/openapi.json`,
  `evidence/instalacion_desde_clon_limpio.md`.
- **pendientes:**
  - **Ninguna task del plan.** Las 89 filas de tarea están COMPLETADAS con evidencia.
  - Lo único que queda son **dos decisiones del propietario** (ver «autorizaciones_pendientes»).
- **bloqueos:** ninguno técnico. No hay ninguna task BLOQUEADA.
- **autorizaciones_pendientes:**
  1. **R-26 — la gobernanza (`newsV2/`) sigue fuera de todo repositorio** (sin historial, sin
     remoto, sin copia). Decisión: (a) moverla a `neural-news/docs/governance/` y redirigir las
     referencias documentadas, o (b) versionarla como repositorio propio. Es una acción que
     cambia el alcance de las rutas documentadas: **no se ejecuta sin autorización**.
  2. **Crear un remoto remoto de git** (GitHub/GitLab): el remoto actual es local
     (`.remotes/neural-news.git`). Es una acción externa: **no se ejecuta sin autorización**.
- **cuota:** **desconocido**. No existe herramienta de consulta de cuota o de saldo en esta
  plataforma; no se inventa ningún dato. Lo único comprobable es que la ejecución continúa
  (requests y tiempo accumulates) sin que se haya notificado ningún límite, pero eso no es un saldo.
- **reanudacion_automatica:** **NO_DISPONIBLE** — no procede: el proyecto está **COMPLETADO** y
  §6.6.6 exige cancelar los relanzamientos pendientes en ese caso. El mecanismo externo **sí
  existe** (`cron_create`, comprobado con `cron_read list` → **0 tareas programadas**, así que no
  hay nada que cancelar) y **no** se configura: relanzar un plan cerrado no aporta nada. Si en el
  futuro se autoriza una de las dos decisiones de arriba, ahí sí procede un relanzamiento real
  con la instrucción «lee `docs/agente/ESTADO.md` y continúa desde `proxima_accion_exacta`».
- **supervisor externo (añadido por petición del propietario):** `PROMPT.md` (el prompt del
  agente) y `supervisor.sh` (el guion de Bash que lo relanza, lee sus etiquetas y gestiona la
  espera por cuota) están **en la raíz del repositorio**. El supervisor usa
  `docs/agente/PLAN.md` —el espejo con casillas del plan maestro, generado por
  `tools/generar_plan_casillas.py`— y su marcador `docs/agente/TERMINADO`.
  - **Estado real:** `AGENTE_CMD` sigue siendo un marcador de posición (`supervisor.sh:5`): hay que
    rellenarlo con el comando real de esta máquina (**SUP-01**).
  - `supervisor.sh` es **Bash** y usa `crontab`: en Windows hace falta WSL o Git Bash con cron.
    **No se ha configurado ningún `crontab`**: no hay un programador real verificado en este
    sistema (**SUP-02**). El mecanismo `cron_create` de la plataforma sí existe, pero no se
    configura mientras el plan esté cerrado.
  - `docs/agente/TERMINADO` está **ignorado por git** (es estado de máquina): por eso el
    supervisor no relanza. **Para retomar el trabajo pendiente, bórralo.**
- **proxima_accion_exacta:** **esperar la decisión del propietario** sobre
  `docs/agente/TAREAS.md` → filas `DEC-01` (mover `newsV2/` al control de versiones) y `DEC-02`
  (crear un remoto remoto), y `SUP-01`/`SUP-02` (activar el supervisor). Si se autoriza alguna,
  ejecutarla **empezando por `DEC-01`**: mover
  `C:\Users\haxth3\Documents\NeuralStories\newsV2` a
  `C:\Users\haxth3\Documents\NeuralStories\neural-news\docs\governance`, redirigir las rutas
  documentadas que la apuntan (`ESTADO_REAL.md:5`, `docs/agente/PLAN_MAESTRO.md`,
  `docs/agente/REGISTRO.md`, `newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md`) y commitearlo en
  `beta/v1`.

---

## Contexto mínimo para reanudar sin historial

- **Repositorio activo:** `C:\Users\haxth3\Documents\NeuralStories\neural-news`, rama `beta/v1`.
  Remoto: `.remotes/neural-news.git` (local). HEAD `ea8486d`.
- **Hermano congelado:** `archive/neuralnews-20261101/` (fuera de git por `.gitignore`): es
  **fuente de capacidades**, no un segundo producto (ADR-016).
- **Capacidades reales comprobadas:** sistema de ficheros persistente ✓ · internet disponible ✓ ·
  **consulta de cuota: no disponible** · programador externo ✓ (`cron_create`, hoy sin tareas).
- **Cómo se verifica todo (comandos que funcionan tal cual):**

```powershell
cd "C:\Users\haxth3\Documents\NeuralStories\neural-news"
python -m pytest tests -q                     # exit 0 (332 tests)
python tools\check_clases.py                  # 0 reimplementaciones
python tools\check_a11y.py                    # 0 bloqueantes
python tools\scan_secrets.py .                # 0 hallazgos
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
