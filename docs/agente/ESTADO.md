# ESTADO — checkpoint de sesión · neural.news

## Última actualización

2026-11-02 15:30 (Europe/Madrid) — **Fases 0–4 y 7 cerradas**; Fase 5 (NN-113) **EN CURSO**
(`.1`–`.5`, `.7`, `.10`, `.11`, `.14`, `.16`, `.17` completadas); Fase 6 (NN-114) y Fase 8
(NN-115/116) pendientes.

## Capacidades disponibles

| Capacidad | Estado | Detalle |
|---|---|---|
| Archivos persistentes | ✅ | `neural-news/` (repo git activo, rama `beta/v1`), `newsV2/` (gobernanza, **fuera de git**), `archive/`, `backups/`, `.remotes/` |
| Ejecución de comandos | ✅ | PowerShell 7 en Windows; `python` 3.12.6 con FastAPI/SQLAlchemy/Alembic/pytest; `node` 24, Next.js 15.1.6, Playwright (Edge del sistema), ESLint 9 |
| Base de datos | ✅ | PostgreSQL 16.9 nativo en `pglocal/` (**puerto 5433**, en marcha); SQLite en `neural-news/storage/` (esquema en `d5e3f9a2b7c1`, migrado y verificado) |
| Red | ⚠️ | Sin remoto remoto de git: el remoto es **local** (`.remotes/*.git`). Internet disponible (descarga de fuentes), usado de forma puntual |
| Consulta de cuota | ❌ | **No disponible**: no hay ninguna herramienta de cuota en esta plataforma. Estado: **desconocido** |
| Programador / reanudación | ❌ | **No disponible**: no hay herramienta de creación de tareas programadas. Reanudación = reejecutar este mismo `/goal` |
| Multiagente | ⚠️ | Disponible, pero el subagente de lint **fue cortado por el límite de uso** a mitad; su trabajo se terminó a mano |
| Manipulación de ficheros | ⚠️ | `Remove-Item` está bloqueado; para eliminar, `rm <ruta>` (lanzador con papelera) o `git rm` |

## Tarea actual y estado

**NN-113 — Frontend (Fase 5).** EN CURSO.

Hecho y verificado: `.1` (fronteras de error y estados de carga), `.2` (ESLint ejecutable),
`.3` (script `typecheck`), `.4` (cliente HTTP único con `ApiError`), `.5` (error del trabajo
propagado), `.7` (0 `any`), `.10` (fuente de iconos sin bloquear el render), `.11` (idempotencia
por contenido), `.14` (`webServer` en Playwright), `.16` (B23), `.17` (B24).

Pendiente en esta fase: `.6` (mapa de estado compartido), `.8` (a11y), `.9` (lint de clases
inexistentes), `.12` (sistema visual único), `.13` (dividir archivos grandes: `features/studio/App.tsx`
= 840 líneas y `NewsEditorialTab.tsx` = 759), `.15` (cablear `BackupModal`).

## Último punto verificado

**NN-113.4 / .5 / .11 + B23 (NN-113.16) + B24 (NN-113.17) — COMPLETADAS con evidencia E.**

- `python -m pytest tests -q` → **258 passed, 1 skipped** (259 tests colectados), **exit 0**.
- `npx eslint .` → **0 problemas**. `npx tsc --noEmit` → **0 errores**.
- `npx playwright test` → **8 passed, 0 fallos** (exit 0).
- **B23**: `APPROVED → RESEARCHING` era una transición inválida → el trabajo moría con
  `ValueError: Transición de estado no permitida` y **se reintentaba 3 veces**. Ahora la transición
  es válida y `research_story` **invalida la aprobación activa** antes de investigar (igual que al
  editar el guion).
- **B24**: el número de versión de guion se calculaba «último + 1»: dos borradores simultáneos
  chocaban con el UNIQUE `(story_id, version)` y la sesión quedaba rota («This Session's transaction
  has been rolled back…»). Ahora el intento va dentro de un **savepoint**: si choca, sólo se revierte
  ese savepoint y se recalcula el número libre.
- Los dos los destapó el **log del worker**, no las pruebas: **un E2E en verde no basta**.

**NN-113.2 / .3 / .7 — COMPLETADAS con evidencia E.**

- `npx eslint .` → **0 problemas** (antes: el script `npm run lint` **no era ejecutable**; al
  hacerlo funcionar aparecieron 38 errores y 6 avisos reales).
- `npx tsc --noEmit` → **0 errores**. Los 10 `any` se sustituyeron por tipos reales
  (`ConfiguracionImportada`, `NoticiaImportada`, `mensajeDeError`).
- `npm run build` → compila (9 páginas).
- Los 38 errores de lint eran reales: código muerto (16 variables sin usar), `any`, comillas sin
  escapar en JSX y una interfaz vacía. Al retirarlos se eliminaron también props que el Studio
  **nunca usó** (`editorialReferences` y `onAssignArticleToBlock` en `NewsEditorialTab`,
  `onUpdateVisualRefStatus` en `ReferencesTab`, tres props de `ResultTab`).

**Bug real encontrado y corregido al verificar (B22):** en la página de noticia, el aviso
«Guardado como versión N» salía **antes** de refrescar el estado; pulsar «Aprobar esta versión»
actuaba entonces sobre la versión anterior y la API la rechazaba (exige la más reciente). Ahora el
estado se refresca **antes** de avisar y los botones se bloquean mientras se guarda. Lo detectó el
E2E `beta-journey` (falló 1 de 7 en una pasada).

## Trabajo a medias sin verificar

- **NN-113**: las tareas `.4`/`.5`/`.11` y los defectos B23/B24 están verificados pero **sin commitear**
  (el commit se hace justo después de este checkpoint).
- **NN-114**: `pytest.ini` en la raíz (la suite ya pasa desde cualquier directorio),
  `scripts/bootstrap.ps1`, `scripts/start.ps1`, `scripts/stop.ps1` y `.github/workflows/ci.yml`
  **escritos pero sin ejecutar de extremo a extremo**.

## Archivos modificados desde el último checkpoint

Sin commitear (desde `e7b3588`):

- `apps/web/lib/http.ts` — **nuevo**: cliente HTTP único (`request`, `ApiError`, `idempotenciaDe`).
- `apps/web/lib/api.ts` — deja de tener su propio `fetch`; usa `lib/http.ts`.
- `apps/web/features/studio/lib/projectApi.ts` — usa `lib/http.ts`; traduce el 409 en `ProjectConflict`.
- `apps/web/features/studio/components/ProductionVertical.tsx` — 0 `fetch` a mano.
- `apps/web/app/fuentes/page.tsx` — muestra el error del trabajo (NN-113.5) e idempotencia por
  contenido (NN-113.11).
- `apps/api/src/neuralnews/states.py` — transición `APPROVED → RESEARCHING` (B23).
- `apps/api/src/neuralnews/services/research.py` — invalida la aprobación al reinvestigar (B23).
- `apps/api/src/neuralnews/services/scripts.py` — savepoint + reintento del número de versión (B24).
- `tests/test_reinvestigar_aprobada.py` — **nuevo** (B23).
- `tests/test_version_script_concurrente.py` — **nuevo** (B24).
- `docs/agente/PLAN_MAESTRO.md`, `docs/agente/REGISTRO.md`, `docs/agente/ESTADO.md`.
- `tools/diag_script.py` — **eliminado** (script de diagnóstico temporal).

## Bloqueos y lo que se necesita para resolverlos

| # | Bloqueo | Qué se necesita |
|---|---|---|
| 1 | **R-26**: la gobernanza (`newsV2/`) está fuera de todo repositorio — sin historial, sin remoto, sin copia | **Decisión del propietario**: (a) moverla a `neural-news/docs/governance/` y redirigir las referencias, o (b) versionarla como repositorio propio. No bloquea las fases 5, 6 y 8 |
| 2 | Sin **remoto remoto** de git | **Decisión del propietario**: ¿GitHub/GitLab con credenciales, o el remoto local es suficiente? Afecta a la duración del backup, no a la ejecución |
| 3 | **Cuota desconocida**: no hay forma de consultar la capacidad restante | Ninguna acción; se aplica la sección 8 del objetivo si la capacidad baja |

## Autorizaciones pendientes

1. **Mover `newsV2/` al control de versiones** — cambia rutas documentadas → requiere autorización.
2. **Crear un remoto remoto** (GitHub/GitLab) — acción externa → requiere autorización.
3. **Publicar en producción** — fuera del alcance de este plan; no se hará.

## Cuota y fecha de reinicio

**Desconocido.** No hay herramienta de consulta de cuota en esta plataforma. La capacidad se controla
guardando checkpoint tras cada tarea completada.

## PRÓXIMA ACCIÓN EXACTA

Commitear lo verificado de NN-113 (`.4`, `.5`, `.11`, B23 y B24) y empujarlo a `origin beta/v1`
con el mensaje «NN-113: cliente HTTP único, idempotencia por contenido y dos fallos de concurrencia
corregidos (B23, B24)». Después, seguir con **NN-113.6** (mapa de estado compartido: buscar los
duplicados del mapa de estados entre `lib/hooks.ts`, `features/studio/constants.ts` y
`features/studio/types.ts`) y **NN-113.13** (dividir `features/studio/App.tsx`, 840 líneas, y
`NewsEditorialTab.tsx`, 759).
