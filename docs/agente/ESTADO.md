# ESTADO — checkpoint de sesión · neural.news

## Última actualización

2026-11-02 00:45 (Europe/Madrid) — **NN-110.a COMPLETADA**. Fase 3 en curso; siguiente: **NN-110.b**.

## Capacidades disponibles

| Capacidad | Estado | Detalle |
|---|---|---|
| Archivos persistentes | ✅ | `neural-news/` (repo git activo), `newsV2/` (gobernanza, **fuera de git**), `archive/`, `backups/`, `.remotes/` |
| Ejecución de comandos | ✅ | PowerShell 7 en Windows; `python` 3.12.6 con FastAPI/SQLAlchemy/Alembic/pytest; `node` 24, Next.js 15, Playwright (Edge del sistema) |
| Base de datos | ✅ | PostgreSQL 16.9 nativo en `pglocal/` (**puerto 5433**, en marcha, PID 9932); `neuralnews` con 20 tablas |
| Red | ⚠️ | Sin remoto remoto de git: el remoto es **local** (`.remotes/*.git`). Internet disponible para consultas, pero **no usado** en el trabajo ejecutado |
| Consulta de cuota | ❌ | **No disponible**: no hay ninguna herramienta de cuota en esta plataforma. Estado: **desconocido** |
| Programador / reanudación | ❌ | **No disponible**: no hay herramienta de creación de tareas programadas. Reanudación = reejecutar este mismo `/goal` |
| Multiagente | ✅ | Disponible para tareas exploradoras independientes |
| Manipulación de ficheros | ⚠️ | `Remove-Item` está bloqueado por la política local; para eliminar, usar `git rm` (recuperable por historial) |

## Tarea actual y estado

**NN-110.b — Tipos de job `transcribe_source`, `build_montage`, `probe_media`, `extract_web` + handlers.** PENDIENTE → EN CURSO.

Contexto: hoy hay 5 tipos de job (`process_source`, `analyze_video`, `research_story`,
`draft_script`, `export_batch`). La transcripción y el montaje se ejecutan **dentro del hilo de
petición** (`api/sources.py:206` y `api/projects.py:1021`), y el `ffprobe` de la subida de medios
también (`api/projects.py:530,611`).

## Último punto verificado

**NN-110.a — COMPLETADA con evidencia E.**

- `python -m pytest tests -q` → **167 passed, 1 skipped, 0 fallos** (65 s).
- 8 pruebas nuevas en `tests/test_queue_leases.py`, verificadas **rojas** antes del arreglo:
  la reserva no era visible para otras sesiones, `renew_lease` no existía, `release_job` no
  limpiaba el lease ni el intento, y no había barrido periódico.
- El lease ahora significa algo: `claim_next_job` confirma la reserva (el trabajo es visible como
  `RUNNING` con su lease antes de ejecutar nada), el worker renueva el lease con un hilo dedicado
  mientras el trabajo corre, el barrido periódico recupera lo vencido **sin reiniciar el worker**,
  y `release_job` limpia `lease_until`, `next_run_at` y `attempt`.
- Commit `NN-110.a` en `beta/v1` (pendiente de push en este checkpoint).

## Trabajo a medias sin verificar

- **Ninguno.** NN-110.a está cerrada con evidencia; NN-110.b empieza desde cero.

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
