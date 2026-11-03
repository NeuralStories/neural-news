# ESTADO — checkpoint de neural.news

> Checkpoint de la entrega de la beta `1.0.0-beta.1`. Cada campo obligatorio
> aparece con su nombre **exacto**; los dos contratos de `/goal` usados en el
> proyecto nombran los campos de forma distinta, así que se dan **los dos
> alias** (`ultima_actualizacion` = «Última actualización», etc.). Sin secretos
> ni credenciales.

## Última actualización

**2026-11-03 14:00 (Europe/Madrid)** — **Auditoría independiente de la beta
`1.0.0-beta.1` terminada.** El objetivo era **refutar** las afirmaciones de la
entrega, no añadir funcionalidad. Se hicieron cinco comprobaciones (A1 clon
limpio, A2 coherencia documental, A3 ciclo en frío, A4 git e integridad, A5
recorrido funcional) y se corrigió **todo** lo que la auditoría demostró que
estaba roto. Informe: `docs/entrega/AUDITORIA_BETA.md`. Rama
`release/1.0.0-beta.1`, HEAD `104489e`. **Sin push**; el tag `v1.0.0-beta.1`
**no se ha movido** (sigue en `1c63a3a`).

- `ultima_actualizacion`: 2026-11-03 14:00 (Europe/Madrid)
- `plan_actual`: `docs/agente/PLAN_MAESTRO.md` → ahora
  `proyecto final/docs/agente/PLAN_MAESTRO.md` (89 filas de tarea + el bloque
  «ENTREGA BETA» con F1–F8 y las decisiones) · espejo con casillas en
  `docs/agente/PLAN.md` (89/89 `[x]`) · cola operativa en `docs/agente/TAREAS.md`
  · decisiones en `docs/agente/REGISTRO.md` · **auditoría** en
  `docs/entrega/AUDITORIA_BETA.md` (evidencias en
  `docs/entrega/evidencias/auditoria/`)

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

**Ninguna: AUDITORÍA TERMINADA.** La auditoría de la beta `1.0.0-beta.1` está
completa: cinco comprobaciones, 16 defectos hallados y corregidos (14 de código
o repositorio y 2 de la guía de pruebas), y un
informe con veredicto en `docs/entrega/AUDITORIA_BETA.md`.

- `tarea_actual`: ninguna — auditoría terminada (veredicto:
  `BETA_CON_DEFECTOS_CORREGIDOS`), HEAD `104489e`, tag `v1.0.0-beta.1`
  **sin mover** en `1c63a3a`

## Último punto verificado

**Auditoría independiente (2026-11-03), con veredicto y log por comprobación en
`docs/entrega/evidencias/auditoria/`:**

- **A1 (clon limpio)**: clonado desde el tag y desde la rama corregida,
  instalado desde los ficheros de bloqueo. En el **tag** fallaba la
  instalación (Pillow y `cryptography` sin declarar) y la suite abortaba;
  en la rama corregida: **pytest exit 0**, `tsc` 0 errores, `eslint` 0
  problemas, `build` correcto, **Playwright verde** y arranque en
  **3001/8001** con `/health` → `1.0.0-beta.1`.
- **A2 (documentación)**: directorio de gobernanza unificado en
  `docs/gobernanza/`; **0 destinos rotos** en 17 documentos;
  `.env.example` con las **40** variables que el código lee; versión
  `1.0.0-beta.1` idéntica en los **6** sitios (package.json, pyproject,
  `__version__`, lib/version.ts, openapi.json y `/health`).
- **A3 (ciclo en frío)**: parada/arranque/parada/arranque sin puertos
  ocupados ni procesos huérfanos; `beta_stop.mjs` ahora barre huérfanos y
  `start.ps1` registra sus PIDs.
- **A4 (git)**: tag **anotado** que apunta a `1c63a3a`; los tres commits
  post-tag de la entrega solo tocaban documentación; **0 secretos** en árbol
  e historial; `.gitignore` cubre `.env`, `node_modules`, builds y cachés, y
  ninguno está en el índice.
- **A5 (recorrido funcional)**: ver `docs/entrega/AUDITORIA_BETA.md`.

- `ultimo_punto_verificado`: lo anterior, todo reejecutado sobre el commit
  `104489e` de `release/1.0.0-beta.1`

## Trabajo a medias sin verificar

**Nada.** Todos los hallazgos de la auditoría están corregidos y verificados
(clon limpio con las 14 comprobaciones del repo en verde). Lo único que queda
sin poder comprobarse aquí es el entorno que no arranca en esta máquina (WSL,
crontab) y la **cuota**, que no es consultable.

- `trabajo_sin_verificar`: ninguno (WSL/crontab y la cuota siguen sin poder
  comprobarse en esta máquina, pero no bloquean la beta)

## Archivos modificados desde el último checkpoint

Los **cinco commits de corrección de la auditoría** sobre el tag
`v1.0.0-beta.1` (`a480387`, `3eabf21`, `f656d5b`, `f0eb767`, `104489e`) y el
commit de cierre con el informe de auditoría y este checkpoint. Todos locales,
sin push; el tag no se ha movido.

- `archivos_modificados`: los cinco commits de corrección de la auditoría más
  el commit de cierre (`docs/entrega/AUDITORIA_BETA.md`,
  `docs/agente/ESTADO.md`, `docs/agente/REGISTRO.md`,
  `docs/entrega/GUIA_PRUEBAS_BETA.md` y `tools/auditoria/`)

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

**`BETA_CON_DEFECTOS_CORREGIDOS`** — la beta `1.0.0-beta.1` **funciona**, pero
la auditoría independiente encontró **16 defectos reales** (entre ellos: dos
dependencias sin declarar que impedían instalar el repositorio en limpio, el
manifiesto de la gobernanza que no cuadraba con lo entregado, artefactos
generados con finales de línea distintos de los versionados, una web que no
arrancaba en un clon limpio y procesos huérfanos al parar). Todos están
corregidos y verificados en la rama `release/1.0.0-beta.1`.

El tag `v1.0.0-beta.1` **no se ha movido** (sigue en `1c63a3a)**: al corregir
el contenido, el tag deja de representar lo que se entrega. Propuesta —a la
espera de decisión del propietario—: publicar **`1.0.0-beta.2`** con el
contenido ya corregido.

- `estado_beta`: BETA_CON_DEFECTOS_CORREGIDOS

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

**Decidir el versionado de la corrección**: el tag `v1.0.0-beta.1` ya no
representa el contenido verificado. La acción concreta es **crear el tag
anotado `v1.0.0-beta.2` sobre el HEAD de `release/1.0.0-beta.1`** (`104489e`
o el commit que resulte de esta auditoría) **solo con la autorización expresa
del propietario**, sin push y sin mover `v1.0.0-beta.1`.

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
