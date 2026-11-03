# ESTADO — checkpoint de neural.news

> Checkpoint de la entrega de la beta `1.0.0-beta.1`. Cada campo obligatorio
> aparece con su nombre **exacto**; los dos contratos de `/goal` usados en el
> proyecto nombran los campos de forma distinta, así que se dan **los dos
> alias** (`ultima_actualizacion` = «Última actualización», etc.). Sin secretos
> ni credenciales.

## Última actualización

**2026-11-03 10:05 (Europe/Madrid)** — **Beta local entregada.** Las ocho fases
(F1–F8) están COMPLETADAS con evidencia. Rama `release/1.0.0-beta.1`, commit
`1c63a3a` («release: v1.0.0-beta.1»), tag anotado `v1.0.0-beta.1`. **Sin push**
(el remoto remoto queda aplazado por decisión del propietario).

- `ultima_actualizacion`: 2026-11-03 10:05 (Europe/Madrid)
- `plan_actual`: `docs/agente/PLAN_MAESTRO.md` → ahora
  `proyecto final/docs/agente/PLAN_MAESTRO.md` (89 filas de tarea + el bloque
  «ENTREGA BETA» con F1–F8 y las decisiones) · espejo con casillas en
  `docs/agente/PLAN.md` (89/89 `[x]`) · cola operativa en `docs/agente/TAREAS.md`
  · decisiones en `docs/agente/REGISTRO.md`

## Capacidades disponibles

- **archivos persistentes:** ✓ (repositorio y `docs/` en disco)
- **internet:** ✓ (`GET https://registry.npmjs.org/-/ping` → 200)
- **cuota consultable:** **NO** — no existe herramienta de consulta de cuota ni de
  saldo
- **programador de tareas:** ✓ existe (`cron_create`/`cron_read`, **0 tareas**
  activas) · **pero** el `supervisor.sh` es Bash y **WSL no arranca** en esta
  máquina (virtualización desactivada): **no hay ningún `crontab` configurado**
- **PostgreSQL local:** ✓ (16.9 en `pglocal/`, puerto 5433) — permite ejecutar la
  prueba real de PostgreSQL (0 skips)

- `capacidades`: archivos ✓ · internet ✓ · cuota **no consultable** · programador
  externo ✓ (sin tareas) · Bash/WSL **parcial** (WSL no arranca) · PostgreSQL
  local ✓

## Tarea actual y estado

**Ninguna: BETA ENTREGADA.** El plan maestro tiene sus 89 filas COMPLETADAS y las
8 fases de la entrega COMPLETADAS.

- `tarea_actual`: ninguna — beta entregada (0 PENDIENTES, 0 BLOQUEADAS),
  commit `1c63a3a`, tag `v1.0.0-beta.1`

## Último punto verificado

**Verificación final completa, ejecutada sobre el árbol limpio (14/14 PASA):**

- `python -m pytest tests -q` → **exit 0** — **386 tests, 0 skip** (la prueba
  real de PostgreSQL se ejecuta: `scripts/preparar_base_pg_test.py` crea una
  base aislada)
- `npx tsc --noEmit` → **0 errores** · `npx eslint .` → **0 problemas**
- `npm run build` → **compila** (modo producción, con `NEURAL_ENV=local`)
- `npx playwright test` → **8 passed** (la pila la levanta el propio Playwright)
- `tools/check_clases.py` → 0 reimplementaciones en línea, 0 clases inexistentes
- `tools/check_a11y.py` → **0 bloqueantes · 0 avisos**
- `tools/scan_secrets.py .` → **0 hallazgos** (árbol **e** historial de git)
- `generate_estados` / `generar_manifiesto_studio` / `generar_plan_casillas`
  `--check` → **al día**
- `tools/exportar_openapi.py --check` → el contrato exportado coincide con el servido
- `tools/auditar_evidencias.py` → **0 referencias desfasadas** en el plan
- `git diff --check` → sin errores de espacios
- `tools/check_build_produccion.py` → **0 hallazgos** de depuración, credenciales
  ni datos personales en el build
- **Lanzamiento (F6)**: web **http://localhost:3000** → 200; API
  **http://127.0.0.1:8000/api/v1/health** → 200 con
  `{"ok": true, "version": "1.0.0-beta.1"}` (base, FFmpeg y yt-dlp OK);
  prueba rápida de Playwright contra esa instancia → **7/7 PASA**

Evidencia íntegra (un log por comando) en `docs/entrega/evidencias/` y resumen en
`docs/entrega/RESUMEN_VERIFICACIONES.md`.

- `ultimo_punto_verificado`: lo anterior, todo ejecutado en esta entrega sobre el
  commit `1c63a3a`

## Trabajo a medias sin verificar

**Nada.** El árbol estaba limpio tras el commit de la beta.

- `trabajo_sin_verificar`: ninguno

## Archivos modificados desde el último checkpoint

Ninguno desde el commit de cierre (`docs: cierre beta`) de `release/1.0.0-beta.1`, que recoge
solo este checkpoint, el registro, el plan y la auditoría de la entrega.

- `archivos_modificados`: ninguno (checkpoint = último commit de `release/1.0.0-beta.1`)

## Bloqueos y lo que se necesita para resolverlos

**Ninguno.** No hay ninguna fase BLOQUEADA.

- `bloqueos`: ninguno

## Autorizaciones pendientes

1. **`DEC-02` — remoto remoto de git (GitHub/GitLab)**: el remoto actual es local
   (`.remotes/neural-news.git`). Crear uno externo y publicar la rama de la beta
   son **acciones externas**: requieren autorización expresa.
2. **`SUP-01` — `AGENTE_CMD` del supervisor**: `supervisor.sh:5` sigue siendo un
   marcador de posición (`tu_comando_de_agente_aqui --prompt PROMPT.md`).
3. **`SUP-02` — `crontab`/WSL**: hace falta un entorno con WSL o Git Bash y cron;
   en esta máquina WSL no arranca (virtualización desactivada).

- `autorizaciones_pendientes`: las tres anteriores (ninguna bloquea la beta)

## Cuota y fecha de reinicio

**desconocido.** No existe herramienta de consulta de cuota o de saldo en esta
plataforma, así que **no se inventa ningún dato**. Lo único comprobable es que la
ejecución continuó (requests y tiempo acumulados) sin que se notificara ningún
límite; eso no es un saldo.

- `cuota`: desconocido

## Estado beta

**`BETA_LISTA`** — F1–F8 COMPLETADAS con evidencia. Lo **aplazado** (DEC-02,
SUP-01, SUP-02) no impide este estado y está en el informe final.

- `estado_beta`: BETA_LISTA

## Reanudación automática

**NO_DISPONIBLE** — no procede: la entrega está **cerrada** y el contrato exige
cancelar los relanzamientos pendientes. El mecanismo externo **sí** existe
(`cron_create`; `cron_read list` → **0 tareas**, nada que cancelar) y **no** se
configura: relanzar un plan cerrado no aporta nada. Si el propietario decide
retomar (por ejemplo, autorizando `DEC-02`), se configura **una** reanudación con
la instrucción «lee `docs/agente/ESTADO.md` y continúa desde
`proxima_accion_exacta`».

- `reanudacion_automatica`: NO_DISPONIBLE

## PRÓXIMA ACCIÓN EXACTA

**Esperar la decisión del propietario** sobre `docs/agente/TAREAS.md` → filas
`DEC-02` (remoto remoto), `SUP-01` (`AGENTE_CMD`) y `SUP-02` (crontab/WSL). Si se
autoriza `DEC-02`, ejecutarla **empezando por** crear el remoto y añadirlo como
`origin`, **sin publicar** la rama `release/1.0.0-beta.1` hasta que se pida
expresamente (la sección 0 del `/goal` prohíbe el push).

- `proxima_accion_exacta`: la anterior (una sola acción concreta)

---

## Contexto mínimo para reanudar sin historial

- **Repositorio activo:** `C:\Users\haxth3\Documents\NeuralStories\proyecto final`,
  rama `release/1.0.0-beta.1`, commit `1c63a3a`, tag `v1.0.0-beta.1`. Remoto:
  `.remotes/neural-news.git` (local). Rama de desarrollo: `beta/v1` @ `4a6d5db`.
- **Hermano congelado:** `archive/neuralnews-20261101/` (fuera de git): es
  **fuente de capacidades**, no un segundo producto (ADR-016).
- **Cómo se verifica todo (comandos que funcionan tal cual):**

```powershell
cd "C:\Users\haxth3\Documents\NeuralStories\proyecto final"
pwsh -NoProfile -File docs\entrega\verificar.ps1   # 14 comprobaciones con veredicto y log
python -m pytest tests -q                          # 386 tests, 0 skip
node scripts\beta_start.mjs                        # arrancar la beta (multiplataforma)
node scripts\beta_stop.mjs                         # pararla
```

- **Tres reglas aprendidas que evitan perder otra tanda de E2E** (ver `REGISTRO.md`,
  B32/B33/B34):
  1. **Antes de `npm run build` o de un E2E: `scripts\stop.ps1`.** Un `next start` vivo
     sirve un build viejo → chunks 400 → la página no hidrata.
  2. **Ninguna herramienta que importe la aplicación puede tocar la base viva**
     (importarla aplica migraciones): `tools/exportar_openapi.py` usa una base aislada.
  3. **La carpeta con espacio no es el problema**: si una herramienta falla por la ruta,
     se arregla la herramienta (`pathlib`, comillas), no el nombre de la carpeta.
