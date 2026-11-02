# ESTADO — checkpoint de sesión · neural.news

## Última actualización

2026-11-02 21:30 (Europe/Madrid) — **Plan maestro cerrado**: las 95 filas están **COMPLETADAS**
(0 PENDIENTES, 0 BLOQUEADAS) y `origin beta/v1` está al día en `a08c831`. Solo queda la decisión
del propietario sobre R-26 y el remoto remoto.

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
propagado), `.6` (mapa de estado único y generado), `.7` (0 `any`), `.8` (a11y: 0 bloqueantes),
`.9` (lint de clases inexistentes), `.10` (fuente de iconos sin bloquear), `.11` (idempotencia
por contenido), `.12` (sistema visual único), `.13` (archivos grandes divididos), `.14`
(`webServer` en Playwright), `.15` (Centro de mantenimiento cableado), `.16` (B23), `.17` (B24).

**NN-113 completa salvo el commit de este lote.**

## Último punto verificado

**Verificación final del lote (Fase 8 + NN-117) — TODO EN VERDE:**

- `python -m pytest tests -q` → **exit 0** (suite completa, 1 skip).
- `npx tsc --noEmit` → **0 errores**; `npx eslint .` → **0 problemas**.
- `npm run build` → compila; `npx playwright test` → **8 passed (1,6 min)**.
- `python tools/check_clases.py` → **0 reimplementaciones en línea**.
- `python tools/check_a11y.py` → **0 bloqueantes · 0 avisos**.
- `python tools/generate_estados.py --check` y `generar_manifiesto_studio.py --check` → **al día**.
- `python tools/scan_secrets.py .` → **0 hallazgos de secretos**.

**NN-115.1–.5 y NN-116.1–.3 — COMPLETADAS con evidencia E.**

- `python -m pytest tests -q` → **exit 0** (suite completa, 1 skip).
- `GET /api/v1/metrics` → métricas (p95, media, tasa de fallo, profundidad de cola, por
  `error_kind`) y **alertas** (cola parada, lease vencido, presupuesto 80 %, fallo repetido),
  calculadas **de la base de datos**.
- La página `/ops` los muestra arriba, con `role="alert"`.
- **NN-115.5 (cronometrado)**: el fallo de proveedor aparece en lo que consume la UI en
  **< 60 s** (`tests/test_metricas_alertas.py`).
- **NN-116**: el presupuesto ya se verificaba **antes** de la llamada; ahora está **documentado
  con su evidencia** (`assert_paid_call_allowed` antes de llamar al modelo, la búsqueda o el
  análisis de vídeo; `FAILED` con `error_kind="budget"`).

**NN-117.4 / .6 / .7 / .8 — COMPLETADAS con evidencia E** (falta el commit).

- **NN-117.4**: migración `e7a1b3c9d4f2` (`model_routes` + `jobs.model_snapshot`),
  `services/model_routes.py` y endpoints `GET`/`PUT /api/v1/model-routes`. El trabajo se ata a la
  ruta que tenía **al encolarse** · `tests/test_model_routes.py` (9) — **E**.
- **NN-117.6**: `services/subtitles.py` (SRT/VTT desde los `SourceSegment` reales, texto íntegro,
  tiempos monótonos) — **E**.
- **NN-117.7**: `services/contradictions.py` propone la contradicción y **no** cambia ningún
  estado — **E**.
- **NN-117.8**: `docs/adr/ADR-022-descartes-del-port.md` — cada descarte del port con su motivo
  escrito — **A**.

**NN-114.1–.7 — COMPLETADAS con evidencia E y COMMITEADAS** (`cce8054`, empujado).

- `scripts\bootstrap.ps1` ejecutado **de extremo a extremo** → **exit 0**: requisitos (Python 3.12,
  Node 24.20.0) → backend instalado → `.env` creado → migraciones Alembic (5) → web → **suite
  verde** → «Listo».
- `scripts\start.ps1` → API + worker + web levantados; salud `neural.news v0.1.0 · entorno local`,
  API 200 y web 200. `scripts\stop.ps1` → para **sólo** los procesos del proyecto.
- **B30 (nuevo, real):** `start.ps1` no arrancaba la web en Windows
  (`Start-Process -FilePath "npm"` → «no es una aplicación Win32 válida»). Corregido con
  `Get-Command npm.cmd`.
- **B31 (nuevo, real):** el CI usaba `working-directory: neural-news`, que no existe al hacer
  checkout (el repositorio **es** la raíz del producto) → fallaba en el primer paso. Corregido.
- **B29 (nuevo, real):** `PUT /settings/score-weights` devolvía **500** con un peso no numérico
  («0,75») → ahora **422** con el peso que falla. Rojo→verde verificado con `git stash`.
- **NN-114.3:** 31 pruebas nuevas para `providers/research.py`, `providers/video_analysis.py` y
  `api/ops.py` (antes sin ninguna cobertura).
- **NN-114.4:** `docs/openapi.json` generado desde la app real (105 KB) y verificado por
  `tools/exportar_openapi.py --check` + `tests/test_openapi_exportado.py` (el test ya detectó un
  desfase real).
- **NN-114.6:** la suite pasa desde la raíz **y** desde `apps/api` (`pytest -q ../../tests` →
  **exit 0**); ambos pasos están en el CI.
- **NN-114.7:** desviación documentada: no hay capacidad de grabar vídeo; se deja
  `evidence/instalacion_desde_clon_limpio.md` con la transcripción literal de la instalación real.

**NN-113.6 / .8 / .9 / .12 / .13 / .15 — COMPLETADAS y COMMITEADAS** (`8fff0d7`, empujado).

**NN-113.4 / .5 / .11 + B23 (NN-113.16) + B24 (NN-113.17) — COMPLETADAS y COMMITEADAS**
(`f8a7b40`, empujado a `origin beta/v1`).

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

**Falso positivo-costoso (lección, repetida dos veces):** una tanda de E2E dio **7 fallos de 8**
con el error boundary de React. La causa **no** era el código: un `next start` de una sesión
anterior seguía sirviendo el puerto 3000 y, al reconstruir, el navegador pidió chunks
inexistentes (HTTP 400). **Regla: antes de `npm run build`, detener el servidor del puerto 3000;
y antes de un E2E, `scripts\stop.ps1`.** La segunda vez el servidor superviviente era el que había
sobrevivido a un E2E cancelado: por eso `stop.ps1` se corrigió (B33) y el E2E ya no reutiliza
servidores (`reuseExistingServer: false`).

## Trabajo a medias sin verificar

- **NN-115/116 y NN-117.4/.6/.7/.8**: verificados y **sin commitear** (el commit va justo
  después de este checkpoint).
- **NN-114**: cerrada y commiteada (`cce8054`).

## Archivos modificados desde el último checkpoint

Sin commitear (desde `cce8054`):

- **Backend**: `apps/api/src/neuralnews/metrics.py` (nuevo), `services/model_routes.py` (nuevo),
  `services/subtitles.py` (nuevo), `services/contradictions.py` (nuevo),
  `api/ops.py` (endpoints `/metrics` y `/model-routes`, validación de pesos),
  `queue.py` (instantánea de la ruta), `worker_tasks.py` (usa el modelo de la instantánea),
  `models.py` (`ModelRoute` + `jobs.model_snapshot`).
- **Migración**: `infra/migrations/versions/e7a1b3c9d4f2_nn117_model_routes.py` (nueva).
- **Web**: `apps/web/app/ops/page.tsx` (métricas y alertas), `apps/web/lib/api.ts` (`api.metrics()`),
  `apps/web/playwright.config.ts` (`reuseExistingServer: false`).
- **Herramientas**: `tools/exportar_openapi.py` (base **aislada**: no toca la base viva),
  `tools/scan_secrets.py` (UTF-8 y escaneo de lo versionado).
- **Scripts**: `scripts/start.ps1` (B30: `npm.cmd`), `scripts/stop.ps1` (B33: rutas de Next).
- **Pruebas**: `tests/test_metricas_alertas.py`, `tests/test_model_routes.py`,
  `tests/test_subtitulos_contradicciones.py` (nuevas).
- **Documentación**: `docs/adr/ADR-022-descartes-del-port.md` (nuevo), `docs/openapi.json`
  (regenerado), `docs/agente/PLAN_MAESTRO.md`, `docs/agente/REGISTRO.md`, `docs/agente/ESTADO.md`.

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

**El plan maestro está cerrado**: las 95 filas están **COMPLETADAS**, ninguna PENDIENTE ni
BLOQUEADA, y `origin beta/v1` está al día (`a08c831`).

Lo que queda no es una tarea del plan, sino **una decisión del propietario** (no se ejecuta sin
autorización):

1. **Mover `newsV2/` al control de versiones** (riesgo R-26): la gobernanza sigue fuera de todo
   repositorio. Decidir entre (a) moverla a `neural-news/docs/governance/` y redirigir las
   referencias, o (b) versionarla como repositorio propio.
2. **Crear un remoto remoto (GitHub/GitLab)**: el remoto actual es local
   (`.remotes/neural-news.git`); crear uno externo es una acción externa.

Si ninguna de las dos se autoriza, el producto queda en el estado en que está y **no** hay más
tareas del plan pendientes. Para retomar el trabajo: leer este `docs/agente/ESTADO.md` y seguir
desde aquí.
