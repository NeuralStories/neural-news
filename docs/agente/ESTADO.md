# ESTADO — checkpoint de sesión · neural.news

## Última actualización

2026-11-02 14:30 (Europe/Madrid) — **Fases 0–4 y 7 cerradas**; Fase 5 (NN-113) en curso;
Fase 6 (NN-114) y Fase 8 (NN-115/116) pendientes.

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
`.3` (script `typecheck`), `.7` (0 `any`), `.10` (fuente de iconos sin bloquear el render),
`.14` (`webServer` en Playwright).

Pendiente en esta fase: `.4` (cliente HTTP único con error tipado), `.5` (propagar el error del
trabajo), `.6` (mapa de estado compartido), `.8` (a11y), `.11` (idempotencia por contenido),
`.12` (sistema visual único), `.13` (dividir archivos grandes), `.15` (cablear `BackupModal`).

## Último punto verificado

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

- **NN-113**: el E2E completo se está reejecutando tras el arreglo de B22 (el resultado está en la
  salida de la última ejecución).
- **NN-114**: `pytest.ini` en la raíz (la suite ya pasa desde cualquier directorio),
  `scripts/bootstrap.ps1`, `scripts/start.ps1`, `scripts/stop.ps1` y `.github/workflows/ci.yml`
  **escritos pero sin ejecutar de extremo a extremo**.

## Archivos modificados desde el último checkpoint

Sin commitear (desde `23d70c0`):

- `apps/web/` — `eslint.config.mjs`, `package.json` (+ `typecheck`, `lint` real), `package-lock.json`,
  `playwright.config.ts` (webServer), `app/error.tsx`, `app/not-found.tsx`, `app/loading.tsx`,
  `app/ops/page.tsx` + `app/ops/loading.tsx`, `app/*/loading.tsx` (6), `components/marcador-carga.tsx`,
  `components/carga-fuente-iconos.tsx`, `components/app-shell.tsx` (enlace «Operación»),
  `lib/api.ts` (+ `health()`), `features/studio/**` (limpieza de lint, `types.ts` + `ConfiguracionImportada`,
  `utils/errorMessage.ts`), `app/noticias/[id]/page.tsx` (carrera B22).
- `apps/api/` — `health.py` (comprobaciones reales), `main.py` (las usa), `services/budget.py`
  (costes por proveedor), `worker_tasks.py` (presupuesto antes de la llamada), `pyproject.toml`
  (argon2-cffi), `pytest.ini` nuevo en la raíz.
- `scripts/` — `db_backup.py`, `bootstrap.ps1`, `start.ps1`, `stop.ps1`.
- `tests/` — `test_presupuesto.py`, `test_salud.py`, `test_queue_leases.py`, `test_boveda.py`,
  `test_argon2id.py`, `test_zona_segura.py`, `test_red_descargas.py`, `test_limite_entradas.py`,
  `test_entorno_beta.py`, `test_nn109_defectos.py`, `test_logging_observabilidad.py`.
- `.github/workflows/ci.yml` — nuevo.
- `docs/agente/` — `PLAN_MAESTRO.md`, `REGISTRO.md`, `ESTADO.md`.

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

Comprobar el resultado del E2E que se está ejecutando en segundo plano
(`npx playwright test` en `neural-news/apps/web`): debe dar **7 passed**. Si es verde, confirmar
`npx eslint .` → 0 problemas y `npx tsc --noEmit` → 0 errores, y **commitear** todo lo de la Fase 5
con el mensaje «NN-113: lint ejecutable, tipos sin `any`, fronteras de error y carrera del guion
corregida», empujando a `origin beta/v1`. Después, seguir con **NN-113.4** (cliente HTTP único con
`ApiError` tipado en `apps/web/lib/api.ts`, que hoy conviven con `projectApi.ts` y con un `fetch` a
mano en `ProductionVertical.tsx`) y **NN-113.5** (propagar el error del trabajo: `useJobPolling` ya
lo expone, pero `app/fuentes/page.tsx:25` lo descarta).
