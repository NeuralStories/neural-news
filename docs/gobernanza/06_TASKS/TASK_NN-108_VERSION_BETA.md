# TASK NN-108 → NN-119 — De la integración actual a una versión BETA operable

**Creada:** 01/11/2026 · **Rev. 1** · **Estado:** `PROPUESTA — pendiente de aprobación del propietario`
**Plan rector:** [`18_PLAN_MAESTRO_BETA.md`](../01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md) · **Registro de decisiones:** [`12_REGISTRO_DECISIONES_Y_RIESGOS.md`](../01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md)
**Prioridad:** P0 · **Ventana:** BETA (5 sesiones de 10 h + 2 de reserva) · **Rama objetivo:** `beta/v1` desde `neural-news/main` (`ef01bd0`)

---

## ESTADO DE EJECUCIÓN — 01/11/2026

**Fases 0, 1 y 2 COMPLETADAS.** Commit `2af9c34` en `beta/v1`, empujado al remoto local.

| Fase | Tarea | Resultado | Evidencia |
|---|---|---|---|
| 0 | **NN-119** Truth | COMPLETADA | Backup previo a NN-107 con SHA-256 **coincidente**; dump de PostgreSQL **restaurado en base limpia** con recuento idéntico en **20 tablas**; 2 bundles git *is okay*; 4 artefactos sueltos (13 MB) fuera del árbol con manifiesto; 17/17 fuentes de Flow con hash correcto; `ESTADO_REAL.md` y `IMPLEMENTACION_REALIZADA.md` reescritos; `BACKLOG.csv` reconstruido con el estado real; R-17…R-25 registrados — **E** |
| 1 | **NN-108** Consolidación | COMPLETADA | Hermano archivado en `archive/neuralnews-20261101/` (20 024 ficheros, repo válido, con su remoto) + manifiesto SHA-256 de sus 121 ficheros versionados; remoto local `.remotes/neural-news.git` (3 ramas + tag) con **push**; clon limpio desde el remoto → **27 commits y árbol de 141 ficheros idéntico**; `.gitignore` ampliado; rama `beta/v1`; README único — **E** |
| 2 | **NN-109** Defectos | COMPLETADA | **20 pruebas de regresión nuevas** (17 en `test_nn109_defectos.py`, verificadas **rojas sobre el código original** — 8 de 15 fallaban — y **verdes** tras el arreglo; 3 en `test_schema_migrations.py`). Suite: **159 passed, 1 skipped, 0 fallos**. `tsc --noEmit` sin errores. `next build` compila (9 páginas) y **falla a propósito** sin `NEURAL_API_URL`. **E2E Edge: 7 passed, 0 fallos** — frente a **4 de 5 fallando** en el código original — **E** |

### Hallazgos nuevos surgidos al corregir (no estaban en el plan)

| # | Hallazgo | Gravedad | Estado |
|---|---|---|---|
| **B16** | `podcast:transcript` se leía del atributo `href`; **feedparser lo expone como `url`**. La transcripción de pódcast **nunca funcionó**, por dos motivos independientes (B1 y B16) | Alta | CERRADO — **E** |
| **B17** | La identidad «NeuralDotAI» (nombre previo a la reintegración) aparecía en **5 componentes visibles**, violando la regla F-01 del propio proyecto. El test original solo miraba 4 ficheros y no lo detectaba | Media | CERRADO — la comprobación F-01 ahora recorre todo el árbol — **E** |
| **B18** | `BackupModal.tsx` **no es código muerto**: es el «Centro de mantenimiento» (SHA-256 + descarga JSON), capacidad real guarded por la auditoría F-10 | — | **ABIERTO por decisión** — se conserva; cablearlo es NN-113 |
| **B19** | **El worker no podía completar ningún trabajo** con la salida redirigida en Windows: el `print` con «→» estaba **dentro de la transacción**, el `UnicodeEncodeError` (cp1252) la revertía entera y el trabajo volvía a la cola **para siempre** | **Crítica** | CERRADO — flujos a UTF-8 y estado escrito fuera de la transacción — **E** |
| **B20** | **La base de datos viva estaba desfasada respecto a los modelos**: `alembic_version` vacía y faltaba `generated_takes.needs_review`. Causa: `create_all()` al arrancar solo crea tablas y **nunca añade columnas** | **Crítica** | CERRADO — el arranque aplica `alembic upgrade head`; base reparada y verificada (31/31 tablas, `alembic check` sin diferencias); red de seguridad en `tests/test_schema_migrations.py` — **E** |
| **B21** | `useJobPolling` tenía **un solo temporizador compartido** y `poll()` **no esperaba**: con dos sondeos simultáneos, el antiguo machacaba **el guion recién escrito** y la edición se perdía en silencio. Enfrentado al código original, el E2E «recorrido crítico» falla 4 de 5 | **Alta** (pérdida de datos) | CERRADO — `poll()` espera al trabajo y cada trabajo lleva su propio temporizador — **E** |

### Lo que queda abierto (real, no teórico)

- **NN-110 (Fase 3)** — el trabajo pesado sigue dentro del hilo de petición (transcripción, montaje, ffprobe, extracción web). Es la fase de mayor riesgo y la que más valor aporta a la beta.
- **NN-111 (Fase 4)** — `demo_mode` abierto por defecto, cookie `secure=False` hardcodeado, tope de bytes aplicado tarde, DNS-rebinding. (B9 y B20 ya cerrados.)
- **NN-113 (Fase 5)** — error boundaries, ESLint ejecutable, cliente HTTP único, a11y, cableado de `BackupModal`.
- **NN-114 (Fase 6)** — la suite debe ejecutarse **desde la raíz**: desde `apps/api` fallan 3 tests por el `sys.path`.
- **NN-115/116 (Fase 8)** — `/ops` en la web, health checks reales, presupuesto verificado antes de la llamada.
- **Decisión del propietario (R-26)** — la gobernanza (`newsV2/`) está **fuera de todo repositorio**: sin historial, sin remoto, sin copia. Es lo único que explica por qué el código es como es. Opciones: moverla a `neural-news/docs/governance/` (cambia rutas documentadas) o versionarla aparte. **No se ejecuta sin aprobación.**

---

> **Alcance de esta tarea:** cerrar la **capa de entrega** para que el producto sea una beta honesta.
> **No** es una reescritura del Studio, **no** añade funciones de producto nuevas (TTS, render final,
> publicación, multiusuario) y **no** elimina ninguna implementación sin equivalencia acreditada (D6).

---

## 0. Condición de entrada — CUMPLIDA

La auditoría de repositorio del 01/11/2026 (plan rector §3) está ejecutada y verificada sobre los
artefactos. Condiciones previas:

- **A** — `neural-news` y `neuralnews` son repositorios **independientes** (sin objetos git comunes,
  sin remoto en ninguno) con bases de datos, cadenas Alembic y aplicaciones web distintas.
- **A** — 9 defectos funcionales verificados (B1–B9) y 8 riesgos de plataforma (P1–P8) con
  `fichero:línea`.
- **A** — El Studio, el director determinista, la invalidación por hash de guion, el montaje FFmpeg
  etiquetado como animática, la puerta de gasto y el guardián SSRF están **correctamente construidos**
  y no se tocan (salvo lo indicado en NN-109/NN-110).
- **R** — El techo de verificación de la auditoría es **R** (inspección de artefactos, sin ejecución).
  Todo lo que este TASK marque como «E» exige ejecución real antes de declararse cerrado.

**Regla de oro de este TASK:** *ningún ítem se cierra por «ya está hecho» sin evidencia ejecutada (E)
en `evidence/`.* Un ítem marcado con casillas sin evidencia es un ítem abierto.

---

## 1. Resumen

Convertir el estado actual («implementada, no aprobada») en una beta que se pueda abrir a un segundo
editor: **9 bugs corregidos con test**, **el trabajo pesado movido a la cola**, **la configuración
blindada por entorno**, **el frontend con contrato y error boundaries**, **un comando para levantarlo
todo**, **el repo hermano archivado con sus capacidades portadas una a una** y **la gobernanza
diciendo la verdad**.

**Presupuesto:** 50 h en 5 sesiones de 10 h, +2 sesiones de reserva. Las fases cierran por **gates**,
no por horas. El mínimo aceptable para declarar beta es **Fases 0–6 completas**; las Fases 7–8 son
mejora y operación respectively, y su ausencia **no** impide abrir la beta (se declaran como tal).

---

## 2. Mapa de tareas

| id | Tarea | Fase | Horas | Prioridad | Depende de | Estado |
|---|---|---|---|---|---|---|
| **NN-119** | Truth: backlog, estados y artefactos reales | 0 | 2 | P0 | — | `NOT_STARTED` |
| **NN-108** | Consolidación: repo único, remoto, binarios fuera del árbol | 1 | 4 | P0 | NN-119 | `NOT_STARTED` |
| **NN-109** | Corrección de los 9 defectos funcionales | 2 | 6 | P0 | NN-119 | `NOT_STARTED` |
| **NN-110** | Cola, latencia, leases y logging | 3 | 8 | P0 | NN-109 | `NOT_STARTED` |
| **NN-111** | Beta-go-live: entorno, auth, esquema, red | 4 | 6 | P0 | NN-110 | `NOT_STARTED` |
| **NN-113** | Frontend: contrato, error boundaries, a11y, lint | 5 | 6 | P1 | NN-109 | `NOT_STARTED` |
| **NN-114** | Reproducibilidad y CI | 6 | 4 | P1 | NN-111, NN-113 | `NOT_STARTED` |
| **NN-117** | Reintegración selectiva del repo hermano | 7 | 8 | P1 | NN-108 | `NOT_STARTED` |
| **NN-115** | Observabilidad y operación | 8 | 4 | P1 | NN-110 | `NOT_STARTED` |
| **NN-116** | Presupuesto real por llamada | 3+8 | 2 | P1 | NN-110 | `NOT_STARTED` |
| **NN-118** | Cadena de valor post-beta (**fuera de beta**) | — | 0 | P2 | — | `DEFERRED` |

---

## 3. FASE 0 — Truth (NN-119) · 2 h · **GATE BLOQUEANTE**

> Nada de código de producto se toca antes de cerrar este gate. Sin él, los fixes posteriores quedan
> sin trazabilidad y el backlog vuelve a mentir (riesgo R-19).

- [x] **NN-119.1** Auditar los 4 artefactos sin trackear en `neural-news/`: `NEURAL_NEWS_ENTREGA_UNICA_PARA_AGENTE.zip` (6,6 MB), `flow-recovery.rar` (6,7 MB), `flow-recovery/`, `NEURAL_NEWS_ENTREGA_UNICA_PARA_AGENTE/`. Mover a `storage/_entregas/2026-11-01/` y generar `MANIFIESTO_SHA256.txt`.
- [x] **NN-119.2** Verificar si existe `backups/neural-news-pre-NN107-F0-20261031.zip`. Hoy solo consta el `.SHA256.txt`. Si el ZIP no existe, **reconstruirlo** desde el commit `pre-merge-main` (`dd7c414`) y sellarlo.
- [x] **NN-119.3** `git bundle create` del historial completo de `neural-news` **y** de `neuralnews` → `backups/bundles/`. Verificar con `git bundle verify`.
- [x] **NN-119.4** Backup **verificado** de la BD PostgreSQL `neuralnews` (`pg_dump` + SHA-256 + restore en BD limpia + `SELECT count(*)` de las tablas clave). **E**.
- [x] **NN-119.5** Actualizar `neural-news/ESTADO_REAL.md`: añadir la **FASE 4 de transcripción** (commits `4b9ec04`, `d9f89f6`, `ef01bd0`) y una sección nueva «Defectos abiertos verificados» con B1–B9 y P1–P8, cada uno con `fichero:línea` y etiqueta de estado.
- [x] **NN-119.6** Actualizar `neural-news/IMPLEMENTACION_REALIZADA.md`: incorporar la FASE 4 y declarar explícitamente que el estado sigue siendo `NO APROBADO`.
- [x] **NN-119.7** **Rebuild del `BACKLOG.csv`**: los 106 `NOT_STARTED` no reflejan la realidad. Marcar el estado **real** de cada ítem (incluido NN-001…NN-065, implementado en el repo hermano y nunca registrado) y añadir las columnas `repo` y `evidencia`. **E**: el CSV debe permitir responder «¿qué está hecho?» sin leer código.
- [x] **NN-119.8** Registrar en `12_REGISTRO_DECISIONES_Y_RIESGOS.md` los riesgos R-17…R-25 del plan rector §8.2.

> **GATE 0:** ✅ `ESTADO_REAL.md` y `BACKLOG.csv` dicen la verdad · ✅ backup verificado de ambas BDs ·
> ✅ bundles + manifiestos SHA-256 · ✅ R-17…R-25 registrados.

---

## 4. FASE 1 — Consolidación (NN-108) · 4 h

> Ejecuta ADR-015, que se decidió el 31/10 y no se aplicó. Riesgo R-21 (pérdida total por fallo de disco).

- [x] **NN-108.1** Congelar `neuralnews/` → `archive/neuralnews-20261101/` con `MANIFIESTO_SHA256.txt` + `git bundle`. **No se borra nada**: se mueve y se sella. **E**: `git bundle verify` + recomputar el manifiesto.
- [x] **NN-108.2** Crear el remoto. Opción local sin servicios externos: `git init --bare` en `C:/Users/haxth3/Documents/NeuralStories/.remotes/neural-news.git` + `git remote add origin` + `push --all`. Si hay credenciales de GitHub disponibles, usar el remoto remoto. **E**: `git clone` del remoto en un directorio nuevo y comparar el árbol.
- [x] **NN-108.3** Lo mismo para el repo hermano congelado (`NN-108.1`): bundle + manifest + copia en el remoto.
- [x] **NN-108.4** Mover `ffmpeg-local/`, `pglocal/`, `tools/yt-dlp.exe` y `tools/dbg*` fuera del árbol de trabajo de git (o añadir a `.gitignore` con su ubicación documentada). Hoy `tools/` (23 MB de `yt-dlp.exe`) está **fuera de todo repo** y no está en ningún manifiesto.
- [x] **NN-108.5** `.gitignore` nuevo y verificado: `storage/`, `*.log`, `.env`, `backups/`, `pglocal/`, `ffmpeg-local/`, `*.zip`, `*.rar`, `node_modules/`, `.next/`, `__pycache__/`.
- [x] **NN-108.6** Crear la rama `beta/v1` desde `main` (`ef01bd0`).
- [x] **NN-108.7** Actualizar `README.md` raíz: **una sola** guía de arranque (hoy conviven `README.md`, `ESTADO_REAL.md`, `IMPLEMENTACION_REALIZADA.md`, `docs/OPERATIONS.md`, `GUIA_DE_REVISION.md` con fechas y estados distintos).

> **GATE 1:** ✅ `git clone` desde el remoto produce el árbol completo con historial · ✅ hermano archivado,
> sellado y con bundle verificado · ✅ cero binarios sueltos en el árbol · ✅ rama `beta/v1` creada.

---

## 5. FASE 2 — Defectos (NN-109) · 6 h

Cada ítem exige **test de regresión que falle antes del fix** y pase después. Sin excepción.

### 5.1 Bloqueantes de usuario (P0)

- [x] **NN-109.1 · B1** `api/sources.py:262` → `source.metadata` **no existe** (el modelo expone `metadata_json`, `models.py:65`). Corregir a `source.metadata_json`. Añadir test que fije la ruta de pódcast (feed con `podcast:transcript`) — hoy nunca funcionó y se anunciaba como operativa.
- [x] **NN-109.2 · B2** `app/fuentes/page.tsx:90` envía `{url, text}` y **descarta `transcript`**; `:54` hace `setTranscript("")`. Incluir `transcript` en el payload (`SourceCreate` ya lo acepta) y **no limpiar** el campo si el alta falló. **E**: E2E «pegar transcripción → Registrar → la transcripción queda guardada y visible».
- [x] **NN-109.3 · B3** `features/studio/App.tsx:218-245` persiste 7 de 8 etapas (falta `resultado`). Añadir el `saveIfChanged('resultado', …)` correspondiente. **E**: test de persistencia de los **8** pasos tras recarga.
- [x] **NN-109.4 · B4** `app/fuentes/page.tsx:374` pinta en `text-emerald-400` un `msg` que mezcla éxito y error. Introducir severidad explícita (`ok`/`warn`/`error`) y derivar el color del token. **E**: test de contrato de mensajes — «el vídeo no tiene subtítulos» **no** se renderiza como éxito.

### 5.2 Corrección y robustez (P1)

- [x] **NN-109.5 · B7** `api/sources.py:291` y `api/projects.py:1029` devuelven `str(exc)` crudo al cliente. Registrar el error completo en el log/auditoría y devolver **código + mensaje seguro**. Comprobar también `services/sources.py:210-213` (expone `str(exc)[:500]` en `metadata_json`, que `source_to_out` devuelve al cliente).
- [x] **NN-109.6 · B8** `api/sources.py:18` — `_auto_transcript_cache` es un `dict` global sin TTL ni tope. Sustituir por caché con TTL y tamaño máximo, o por caché en tabla con invalidación por hash del vídeo.
- [x] **NN-109.7 · B9** `next.config.ts:6` — sin `NEURAL_API_URL` el rewrite proxya a `http://127.0.0.1:8000` y **el build no falla** (los rewrites se evalúan en runtime). Hacer `NEURAL_API_URL` obligatorio en build no-local y fallar el arranque con mensaje explícito.
- [x] **NN-109.8** `providers/transcript.py:123` — `tracks = re.findall(...)` se calcula y **nunca se usa** (el bucle real usa `parsed`). Eliminar el código muerto.
- [x] **NN-109.9** `providers/transcript.py:145-147` — el `name` de la pista se interpola en la URL **sin codificar**. Usar `urllib.parse.quote`.
- [x] **NN-109.10** `services/director.py:13` — el docstring anuncia un default `PENDING` que `_shot_kind` (`:56-81`) **no implementa** (devuelve siempre `GENERATIVE_BROLL`). Alinear docstring y código (o implementar el default). La discrepancia contradice la honestidad documental del proyecto.
- [x] **NN-109.11 · F5** Borrar el código muerto del Studio: `features/studio/components/HelpModal.tsx` (4 KB), `BackupModal.tsx` (12 KB) y los estados `helpOpen`/`backupOpen` (`App.tsx:45-46`) que nunca se leen — **o** conectarlos a un punto de entrada real. Decidir y documentar.
- [x] **NN-109.12** `lib/hooks.ts:46` — `setError_clear` es API muerta. Eliminar o usar.
- [x] **NN-109.13** `api/auth.py:57-59` — `logout` borra **todas** las sesiones del actor, no solo la actual. Documentar el comportamiento mono-usuario o corregirlo.

> **GATE 2:** ✅ B1–B9 con test de regresión rojo→verde · ✅ cero `except Exception` devolviendo texto crudo al
> cliente · ✅ cero código muerto en el camino caliente · ✅ `next build` falla si `NEURAL_API_URL` falta.

---

## 6. FASE 3 — Cola, latencia y leases (NN-110) · 8 h

> Riesgo R-18 (cambia el contrato de los handlers). El frontend **ya tiene** `useJobPolling`; el trabajo
> de UI está hecho, falta conectarlo.

- [ ] **NN-110.1** Añadir los tipos de job `transcribe_source`, `build_montage`, `probe_media`, `extract_web` en `worker_tasks.py` (hoy hay 5: `process_source`, `analyze_video`, `research_story`, `draft_script`, `export_batch`).
- [ ] **NN-110.2** Convertir `api/sources.py:206` `transcribe_source` en `202 + job_id`. Hoy ejecuta `yt-dlp --list-subs` (timeout 90 s) + hasta 3 intentos × 2 flags × timeout 180 s + backoff **en el hilo de la petición**.
- [ ] **NN-110.3** Convertir `api/projects.py:1021` `build_montage` en `202 + job_id`. Hoy ejecuta `subprocess.run(ffmpeg, timeout=600)` **en el hilo**.
- [ ] **NN-110.4** Mover el `ffprobe` de `services/media_library.py:42-47` al worker (se invoca hoy desde el handler de subida, `api/projects.py:530,611`).
- [ ] **NN-110.5** **Renovación de lease** (heartbeat) durante la ejecución del job. Hoy `queue.py:99` fija `lease_until` una vez y no hay renovación ⇒ un job largo puede perder su lease a mitad.
- [ ] **NN-110.6** Recuperar jobs con lease vencido **de forma periódica en el bucle** del worker, no solo al arrancar (`worker.py:36`).
- [ ] **NN-110.7** `queue.py:131-132` `release_job` debe limpiar `lease_until` y `attempt` al re-encolar.
- [ ] **NN-110.8** **Logging estructurado** (JSON a fichero + `Job.error` legible). Hoy `worker.py:51` escribe **solo a stderr** ⇒ `_worker.log` no captura los fallos del bucle.
- [ ] **NN-110.9** `api/ops.py` — exponer en `GET /api/v1/jobs` el motivo del fallo de forma normalizada (código + mensaje), no solo el `str(exc)`.
- [ ] **NN-110.10** **E**: test de latencia — ningún handler de la API supera 2 s en p95 con la cola activa.
- [ ] **NN-110.11** **E**: E2E nuevo `beta-journey.spec.ts` — la transcripción se pide, la UI muestra progreso y el resultado llega sin recargar a mano.

> **GATE 3:** ✅ 0 operaciones >2 s dentro de handlers · ✅ lease renovado y recuperado sin reiniciar el
> worker · ✅ un job fallido es consultable en `/api/v1/jobs` con motivo legible · ✅ E2E del recorrido
> completo en verde.

---

## 7. FASE 4 — Beta-go-live (NN-111) · 6 h

- [ ] **NN-111.1** Introducir `NEURAL_ENV=local|beta|prod` (ADR-017) con comportamiento explícito por entorno. **`prod` sin `NEURAL_ADMIN_PASSWORD`, con `demo_mode=True` o con cookie no segura ⇒ el arranque falla**, no se avisa por log.
- [ ] **NN-111.2** `security.py:65` — `secure=False` **hardcodeado**. El comentario dice «activar via variable de entorno» pero **no existe**. Implementar la variable (por entorno) y aplicar `SameSite`/`domain` coherentes.
- [ ] **NN-111.3** `config.py:23` — `demo_mode=True` por defecto habilita `/api/v1/auth/demo` sin contraseña. Aplicar `require_demo_disabled` (`security.py:86`, hoy con **0 usos**) en todas las rutas de pago/servicio externo. El endpoint `/auth/demo` debe quedar **deshabilitado** fuera de `local`.
- [ ] **NN-111.4** `main.py:31-32` — eliminar `Base.metadata.create_all(get_engine())`. El esquema **siempre** por Alembic. **E**: smoke test `upgrade head` → `downgrade -1` → `upgrade head` sobre PostgreSQL limpio.
- [ ] **NN-111.5** **Paridad SQLite/PostgreSQL**: el esquema usado en local y en CI debe ser el mismo que el de producción. Hoy `create_all` en SQLite puede divergir de Alembic sin que nada lo detecte.
- [ ] **NN-111.6** `safety.py:80` — el tope de bytes se aplica **después** de cargar el cuerpo completo (`response.content[:max+1]`). Cambiar a descarga en streaming con corte real por bytes.
- [ ] **NN-111.7** `safety.py:50` vs `:71-72` — TOCTOU de DNS-rebinding: se resuelve y valida una IP, y `httpx` vuelve a resolver. Mitigar fijando la IP validada en la conexión o usando un proxy de salida con allowlist.
- [ ] **NN-111.8** `safety.py:48-49` — `allowed_hosts` **omite deliberadamente** el bloqueo de red privada. Documentarlo en `docs/SECURITY.md` como decisión explícita, con la lista real y su motivo.
- [ ] **NN-111.9** Endurecer el hashing de contraseña a Argon2id (el repo hermano ya lo tiene: `app/security/auth.py`). Mantener PBKDF2 como fallback de un release.
- [ ] **NN-111.10** Rate limiting en `/auth/login` (no hay límite de intentos).
- [ ] **NN-111.11** Escaneo de secretos del árbol **y del historial** de ambos repos. Verificado hoy: `neuralnews/.env` **sí** está correctamente fuera de git (`.gitignore:18`) y contiene claves locales (`APP_MASTER_KEY`, `SESSION_SECRET`) que **deben regenerarse**, nunca migrarse. Comprobar que ningún `.env` ni clave real aparece en el árbol ni en el historial de `neural-news`.
- [ ] **NN-111.12** Checklist de despliegue de 20 puntos, firmado y verificado en una máquina limpia. **E**.
- [ ] **NN-111.13** `docs/SECURITY.md` y `docs/OPERATIONS.md` actualizados con el modelo de entorno, el modelo de secretos y el procedimiento de rotación.

> **GATE 4:** ✅ sin `NEURAL_ENV=prod` la app **no arranca** · ✅ checklist de despliegue firmado · ✅
> `upgrade/downgrade/upgrade` verde en PG limpio · ✅ escaneo de secretos sin hallazgos.

---

## 8. FASE 5 — Frontend (NN-113) · 6 h

- [ ] **NN-113.1** `loading.tsx`, `error.tsx` y `not-found.tsx` por sección. Hoy, un error de render del Studio (911 líneas) deja la **página en blanco**.
- [ ] **NN-113.2** ESLint real: `eslint` + `eslint-config-next` en `devDependencies`, `eslint.config.mjs`. Hoy `npm run lint` **no es ejecutable** (`package.json:9`).
- [ ] **NN-113.3** `npm run typecheck` (`tsc --noEmit`) en CI; `tsconfig.json` con `noUnusedLocals` y `noUncheckedIndexedAccess` (hoy `allowJs: true` + `skipLibCheck: true`).
- [ ] **NN-113.4** **Un cliente HTTP único** con `ApiError` tipado (`status`, `code`, `detail`). Hoy conviven **tres**(fetchers con dos modelos de error incompatibles: `lib/api.ts:3`, `features/studio/lib/projectApi.ts:49` (clase `ProjectConflict`), `features/studio/components/DossierPanel.tsx:32` (fetch crudo)).
- [ ] **NN-113.5** Propagar el `error` de `useJobPolling` (`lib/hooks.ts:46`) a las páginas que hoy lo descartan (`app/fuentes/page.tsx:25`).
- [ ] **NN-113.6** **Un solo mapa de estado**, compartido y generado desde `packages/contracts` (hoy duplicado en `fuentes/page.tsx:8-15`, `noticias/page.tsx:9-16`, `noticias/[id]/page.tsx:10-17`).
- [ ] **NN-113.7** Eliminar los `any` (10 posiciones: `App.tsx:529,608,616,642,696,716`, `NewsEditorialTab.tsx:151,194`, `ReferencesTab.tsx:22`).
- [ ] **NN-113.8** A11y: filas activables con teclado (`role`, `tabIndex`, `Enter`/`Space`) en `app/fuentes/page.tsx:260`; `aria-label` en botones de icono (`App.tsx:776,786`); foco visible; contraste AA verificado.
- [ ] **NN-113.9** Eliminar las clases inexistentes `scrollbar-none` (`TopNavigation.tsx:102`) y `studio-root` (`app/estudio/page.tsx:177`) — hoy son no-ops silenciosos.
- [ ] **NN-113.10** `app/layout.tsx:15-18` — sustituir el `<link>` externo a Google Fonts por `next/font` (petición bloqueante + dependencia externa en runtime).
- [ ] **NN-113.11** Idempotencia real: `app/fuentes/page.tsx:46` genera `web-${Date.now()}-${random}` en cada intento ⇒ la idempotencia del backend nunca se ejerce desde la UI. Derivar la clave del contenido.
- [ ] **NN-113.12** Unificar el sistema visual: `app/globals.css` define tokens (`.btn`, `.card`, `.input`, `.badge*`) y el Studio usa cadenas Tailwind propias. Verificar que **no** hay dos sistemas visuales conviviendo (la unificación del 01/11 unificó paleta, no el sistema de componentes).
- [ ] **NN-113.13** Dividir los archivos grandes: `App.tsx` (911), `NewsEditorialTab.tsx` (807), `ReferencesTab.tsx` (514), `ProductionVertical.tsx` (455), `ResultTab.tsx` (310), `fuentes/page.tsx` y `noticias/[id]/page.tsx` (381 cada uno).
- [ ] **NN-113.14** `next.config.ts` + `playwright.config.ts`: `NEURAL_API_URL` obligatorio y `webServer` en Playwright para que las E2E no dependan de una pila levantada a mano.

> **GATE 5:** ✅ `lint` + `typecheck` + `build` + `e2e` en verde en CI · ✅ ninguna sección puede quedar en
> blanco por un error de render · ✅ 0 `any` en el Studio · ✅ auditoría a11y sin bloqueantes.

---

## 9. FASE 6 — Reproducibilidad y CI (NN-114) · 4 h

- [ ] **NN-114.1** `scripts/bootstrap.ps1` y `bootstrap.sh`: clonar → `.env` de ejemplo → `alembic upgrade head` → seed demo → arrancar API + worker + web → `pytest` → `e2e`. **Un comando.**
- [ ] **NN-114.2** CI con la matriz: Python 3.12 · `pytest` (140 tests) · PostgreSQL real (sin Docker) · `tsc --noEmit` · `next build` · Playwright sobre Edge. Los 3 workflows de hoy son manuales.
- [ ] **NN-114.3** Cubrir los módulos sin test directo: `providers/research.py` (la ruta Brave real **nunca** se prueba), `providers/video_analysis.py` (`call_gemini_video_analysis` nunca probado), `api/ops.py` (`/provider-status`, `/config/budget`, `/settings/score-weights` sin test).
- [ ] **NN-114.4** `packages/contracts/openapi.json` regenerado y **verificado en CI** (falla si el contrato exportado ≠ el servido).
- [ ] **NN-114.5** Test de equivalencia de la exportación: `export ≠ backup BD` (F-10) debe seguir verde tras los cambios de esquema.
- [ ] **NN-114.6** **E**: vídeo de la instalación completa desde un clon limpio en un directorio nuevo, sin artefactos de la máquina actual.

> **GATE 6:** ✅ clon limpio + un comando ⇒ pila arriba + suite verde, demostrado en vídeo.

---

## 10. FASE 7 — Reintegración selectiva (NN-117) · 8 h

> Cada capacidad se porta **por módulo y por fichero**, con contrato propio y **test de equivalencia**.
> **Nunca** «copiar la carpeta». Nada se elimina sin equivalencia acreditada (D6).

- [ ] **NN-117.1** **Backup/verify de BD** (hermano: `app/domain/media.py`) — **entra en beta**. `pg_dump` + hash + restore en BD limpia + verificación. 3 h.
- [ ] **NN-117.2** **Zonas seguras / cámara** (hermano: `app/domain/camera.py`) — **entra en beta**. Afecta a los gráficos, que son producto. 2 h.
- [ ] **NN-117.3** **Vault de secretos** (hermano: `app/security/vault.py`) — **entra en beta**. Sustituye el `.env` plano; `secrets_status()` se mantiene. 2 h.
- [ ] **NN-117.4** **Rutas de modelo** (hermano: migración `c0f68f32807d`) — **entra en beta**. Resolución de modelo en el job con snapshot. 1 h.
- [ ] **NN-117.5** **Argon2id** (hermano: `app/security/auth.py`) — **entra en beta**. Endurece `security.py`. 1 h. (Alternativa: NN-111.9.)
- [ ] **NN-117.6** Subtítulos SRT/VTT (hermano: `app/domain/subtitles.py`) — entra tras la beta. 1 h.
- [ ] **NN-117.7** Contradicciones de cifras (hermano: `app/domain/contradictions.py`) — entra tras la beta. 2 h.
- [ ] **NN-117.8** **Descartado formalmente** (con ADR): scheduler de feeds, briefs con abstención, catálogo de prompts. El Studio ya cubre el dossier; el scheduler implica operación 2×/día, incompatible con una beta de un solo editor.

> **GATE 7:** ✅ cada capacidad portada con su test de equivalencia en verde en **ambos** lados, o
> descartada con ADR · ✅ el hermano queda archivado, sellado y con bundle verificado · ✅ ADR-016 aprobado.

---

## 11. FASE 8 — Observabilidad y operación (NN-115 + NN-116) · 6 h

- [ ] **NN-115.1** Página `/ops` en la web: trabajos, uso, presupuesto, salud de proveedores. Los endpoints **ya existen** (`api/ops.py`) pero **no hay página**.
- [ ] **NN-115.2** `/health` que comprueba **BD, FFmpeg, yt-dlp y proveedores**, no solo que la API responde.
- [ ] **NN-115.3** Métricas: p95 por endpoint, tasa de fallo por proveedor, duración y profundidad de la cola.
- [ ] **NN-115.4** Alertas: cola parada, lease vencido, presupuesto al 80 %, fallo repetido de proveedor.
- [ ] **NN-115.5** **E**: un fallo de proveedor se ve en la UI en menos de 60 s sin mirar los logs.
- [ ] **NN-116.1** Presupuesto verificado **antes** de la llamada a proveedor (hoy `_call_llm` no comprueba presupuesto; `worker_tasks.py:143` registra `cost_estimate=0.0` a posteriori).
- [ ] **NN-116.2** Tope diario real con contador, no solo el binario `paid_services_enabled`.
- [ ] **NN-116.3** Coste estimado real registrado por llamada y visible en `/ops/usage`.

> **GATE 8:** ✅ un fallo se ve en la UI en <60 s · ✅ el presupuesto corta **antes** de gastar, no después.

---

## 12. Criterios de aceptación (comunes a todas las fases)

1. **Gates por evidencia, no por afirmación.** Cada ítem cerrado tiene su artefacto en `evidence/`.
2. **Test de regresión rojo→verde** para cada defecto (B1–B9) y cada riesgo de plataforma (P1–P8).
3. **Sin regresar honestidad.** Si algo no se implementa, se declara `NO_IMPLEMENTADO` / `PARCIAL` /
   `PENDIENTE_POR_ACTIVO` / `PENDIENTE_POR_API` — nunca se presenta como funcionando.
4. **Sin números inventados.** Ninguna cifra, fecha o resultado en la documentación sin fuente.
5. **Sin delightful defaults.** Ningún behaviour depende de que el entorno sea el del propietario.
6. **Idempotencia.** Toda operación de escritura es idempotente por clave de contenido.
7. **Una sola fuente de verdad.** Ni el navegador ni el `.md` guardan estado que viva en la BD.
8. **Nada se borra sin equivalencia acreditada** (D6).

**Definición de fallo:** gate declarado sin cumplir · evidencia alterada · cambio sin test de regresión ·
`ESTADO_REAL.md` o `BACKLOG.csv` desincronizados con el código · comportamiento dependiente de la
máquina del propietario · estado «funciona» sin prueba ejecutada.

---

## 13. Riesgos operativos de esta tarea

| ID | Riesgo | Prob./impacto | Mitigación / trigger |
|---|---|---|---|
| **R-17** | Congelar el hermano sin portar sus capacidades ⇒ pérdida de cámara, backup, vault, subtítulos, rutas de modelo | Alta / alta | Tabla de decisión NN-117; ADR antes de archivar; port con test de equivalencia por capacidad |
| **R-18** | Mover a la cola rompe el flujo actual de la UI | Media / alta | `useJobPolling` ya existe; el handler devuelve `202 + job_id` con el mismo esquema; E2E del recorrido |
| **R-19** | Arreglar sin cerrar antes el backlog ⇒ fixes sin trazabilidad | Media / media | Gate 0 bloqueante (NN-119) |
| **R-20** | Endurecer `demo_mode`/cookie rompe el flujo local del propietario | Media / media | `NEURAL_ENV` con tres valores; documentar el cambio en el README |
| **R-21** | Sin remoto, un fallo de disco pierde 36 commits y las dos BDs | Baja / crítica | Gate 1 (push + bundle + backup verificado) **antes** de cualquier refactor |
| **R-22** | La cola hace la UI más lenta de lo esperado | Media / baja | Progreso de job ya visible en la UI; gate de 2 s |
| **R-23** | YouTube cambia su HTML/API y rompe la transcripción | Alta / media | Cadena de 3 proveedores (`yt-dlp` → `timedtext` → innertube) + test con fixture local + aviso honesto |
| **R-24** | Un port arrastra la arquitectura del hermano y choca con la del activo | Media / alta | Port por módulo y por fichero, con contrato propio; nunca copiar carpetas |
| **R-25** | La beta se cumple en la máquina del propietario y no en otra | Media / alta | Gate 6 con clon limpio en directorio nuevo |

---

## 14. Fuera de alcance (declarado)

`NN-118` queda **diferido** y explícitamente fuera de la beta: TTS/voz real · render final con locución ·
publicación en plataformas · generación programática de imagen/vídeo · director LLM · gráficos
line/timeline/percentage · episodios 5/10 compuestos · multiusuario y roles · material real de MaxDotAi.

**No se declara la beta abierta si:** alguno de B1–B9 sigue abierto sin test · `lint`/`typecheck`/
`pytest`/`e2e`/`build` no están verdes · el arranque no falla con configuración incoherente ·
`ESTADO_REAL.md` y `BACKLOG.csv` no reflejan el código · el hermano no está archivado y sellado ·
no hay backup verificado de ambas BDs · no existe el recorrido G1 reproducido por vídeo.

---

## 15. Cierre de la tarea

Al cerrar cada fase se actualizan: `neural-news/ESTADO_REAL.md` (módulo a módulo, con etiquetas),
`neural-news/IMPLEMENTACION_REALIZADA.md` (fases y evidencia), `newsV2/06_TASKS/BACKLOG.csv` (estado
real de los ítems), `newsV2/01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md` (ADRs y riesgos) y
`neural-news/docs/` (operación, seguridad, arquitectura).

**La beta se declara con una frase y tres evidencias:** el recorrido G1 reproducido en vídeo, la
suite completa en verde con su salida, y el manifiesto SHA-256 del árbol de entrega.

---

**Documentos relacionados:** [`18_PLAN_MAESTRO_BETA.md`](../01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md) · [`TASK_NN-107_REINTEGRACION_FLOW.md`](TASK_NN-107_REINTEGRACION_FLOW.md) · [`BACKLOG.csv`](BACKLOG.csv) · [`TEST_MATRIX.csv`](TEST_MATRIX.csv)
