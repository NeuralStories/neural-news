# ESTADO — checkpoint de sesión · neural.news

## Última actualización

2026-11-02 08:40 (Europe/Madrid) — **Fase 3 (NN-110) COMPLETADA**: NN-110.a…e cerradas con
evidencia; NN-110.f (verificación) en curso. Siguiente: **NN-111** (beta-go-live).

## Capacidades disponibles

| Capacidad | Estado | Detalle |
|---|---|---|
| Archivos persistentes | ✅ | `neural-news/` (repo git activo, rama `beta/v1`), `newsV2/` (gobernanza, **fuera de git**), `archive/`, `backups/`, `.remotes/` |
| Ejecución de comandos | ✅ | PowerShell 7 en Windows; `python` 3.12.6 con FastAPI/SQLAlchemy/Alembic/pytest; `node` 24, Next.js 15, Playwright (Edge del sistema) |
| Base de datos | ✅ | PostgreSQL 16.9 nativo en `pglocal/` (**puerto 5433**, en marcha); SQLite en `neural-news/storage/` (esquema en `c4d2e8f1a5b6`, migrado y verificado) |
| Red | ⚠️ | Sin remoto remoto de git: el remoto es **local** (`.remotes/*.git`). Internet disponible para consultas, **no usado** en el trabajo ejecutado |
| Consulta de cuota | ❌ | **No disponible**: no hay ninguna herramienta de cuota en esta plataforma. Estado: **desconocido** |
| Programador / reanudación | ❌ | **No disponible**: no hay herramienta de creación de tareas programadas. Reanudación = reejecutar este mismo `/goal` |
| Multiagente | ✅ | Disponible para tareas exploradoras independientes |
| Manipulación de ficheros | ⚠️ | `Remove-Item` está bloqueado por la política local; para eliminar, usar `git rm` (recuperable por historial) |

## Tarea actual y estado

**NN-110.f — Verificación de la Fase 3: test de latencia y E2E del recorrido beta.** EN CURSO.

Contexto: el gate G3 («ninguna operación de más de 2 s dentro de un handler») se comprueba con
`tests/test_latencia_handlers.py`, que vuelve **lento a propósito** al proveedor que antes se
ejecutaba en la petición: si el trabajo volviera al hilo, el handler tardaría 3 s y la prueba fallaría.

## Último punto verificado

**NN-110.e — COMPLETADA con evidencia E.**

- `python -m pytest tests -q` → **182 passed, 1 skipped, 0 fallos** (79 s).
- 6 pruebas nuevas en `tests/test_logging_observabilidad.py`: el log es **JSON por evento** con
  `job_id`, `status`, `duration_s` y `error_kind`; el motivo del fallo se registra **cuando ocurre**
  (`budget` / `material` / `connector` / `unknown`), no se deduce del texto.
- Traza JSON verificada **en ejecución real** sobre la pila en marcha:
  `{"event": "job.done", "job_id": 48, "status": "DONE", "duration_s": 0.031}`.
- Migración `c4d2e8f1a5b6` (columna `jobs.error_kind`) aplicada a la base viva y verificada:
  31/31 tablas, 0 columnas de menos, `alembic check` sin diferencias.
- Commits en `beta/v1`: `a4b891e` (NN-110.a), `dbd76cc` (NN-110.b), `fa966da` (NN-110.c/d),
  `5f5ce7e` (NN-110.e) — todos empujados a `.remotes/neural-news.git`.

## Trabajo a medias sin verificar

- **NN-110.f**: las pruebas de latencia (`tests/test_latencia_handlers.py`, 5) ya están en **verde**;
  el E2E nuevo `e2e/beta-journey.spec.ts` pasa en verde (15,2 s). Falta la **suite E2E completa**
  en verde y el commit.

## Archivos modificados desde el último checkpoint

Desde el commit `75fbf95` (**sin commitear**):

- `docs/agente/PLAN_MAESTRO.md` — **nuevo**. Plan operativo con las 8 fases, criterio de aceptación y
  estado por tarea.
- `docs/agente/REGISTRO.md` — **nuevo**. Decisiones, motivo, fuentes y errores resueltos.
- `docs/agente/ESTADO.md` — **nuevo**. Este checkpoint.

Fuera del repo (gobernanza, sin control de versiones): `newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md`,
`newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md`,
`newsV2/01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md`.

## Bloqueos y lo que se necesita para resolverlos

| # | Bloqueo | Qué se necesita |
|---|---|---|
| 1 | **R-26**: la gobernanza (`newsV2/`) está fuera de todo repositorio — sin historial, sin remoto, sin copia | **Decisión del propietario**: (a) moverla a `neural-news/docs/governance/` y redirigir las referencias, o (b) versionarla como repositorio propio. No bloquea las fases 3–8; se resuelve al final |
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

Abrir `neural-news/apps/api/src/neuralnews/worker_tasks.py` y añadir los cuatro tipos de job que
existen hoy solo dentro del hilo de petición: `transcribe_source` (transcripción de YouTube/pódcast,
hoy en `api/sources.py:206`), `build_montage` (montaje FFmpeg, hoy en `api/projects.py:1021`),
`probe_media` (ffprobe de la subida, hoy en `api/projects.py:530,611`) y `extract_web` (extracción de
artículo, hoy en `api/sources.py:276`). Cada handler debe ser **idempotente** y tener su prueba en
`tests/test_worker_queue.py` (patrón: encolar → `worker()` → comprobar estado y efecto). Verificar
con `python -m pytest tests/test_worker_queue.py -q` y cerrar **NN-110.b**.
