# PLAN MAESTRO — neural.news · de la integración actual a una BETA operable

**Objetivo:** que `neural.news` sea una beta honesta — un recorrido completo, reproducible y honesto
que un segundo editor pueda usar sin ayuda y sin que el sistema le mienta — verificado con
ejecuciones reales, no con afirmaciones.

**Alcance:** los dos repositorios del producto, sus conexiones (API ↔ web ↔ worker ↔ PostgreSQL /
FFmpeg / yt-dlp) y la gobernanza.

**Fuera de alcance declarado** (§7 del plan rector): TTS/voz real, render final con locución,
publicación en plataformas, generación programática de imagen/vídeo, director LLM, gráficos
line/timeline/percentage, episodios compuestos, multiusuario, material real de MaxDotAi.

**Documentos rectores:**
- Plan rector: `newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md`
- Tarea: `newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md`
- Estado real del producto: `neural-news/ESTADO_REAL.md`
- Decisiones y riesgos: `newsV2/01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md`

**Escala de verificación (obligatoria en cada evidencia):**

| Nivel | Significado |
|---|---|
| **A** | Verificado sobre el artefacto: el fichero existe y se ha leído su contenido literal. |
| **R** | Derivado por código: conclusión razonada, sin ejecución. |
| **E** | Ejecutado: prueba real (pytest, E2E, migración, arranque). |

Sin evidencia **E** o **A** con `fichero:línea`, una tarea **no está completada**.

---

## Definición de beta (gates)

| Gate | Criterio | Verificación |
|---|---|---|
| **G1** Recorrido único | Un editor entra, crea una fuente, obtiene transcripción (o un motivo exacto de por qué no), redacta, dirige, monta una animática, la ve en la UI y la descarga | E2E `beta-journey` en verde + vídeo |
| **G2** Honestidad | Ningún estado muestra «éxito» sobre un fallo; lo no implementado se declara en la UI, no solo en el `.md` | Test de contrato de mensajes + revisión de los 6 estados de error |
| **G3** Sin bloqueo | Ninguna operación de >2 s dentro de un handler; transcripción, montaje, ffprobe y extracción web por la cola | Test de latencia p95 por endpoint |
| **G4** Reproducible | `install → migrate → seed → api → worker → web → e2e` con **un** comando, sin Docker, desde un clon limpio | Script único + vídeo desde directorio nuevo |
| **G5** Blindado | Sin `demo_mode` accidental, sin cookie insegura, sin fallback a localhost en build, sin secretos en el árbol, sin segundo repo | Test de configuración + escaneo de secretos + revisión del árbol |
| **G6** Observable | Todo fallo de worker queda registrado con estructura y es consultable desde la UI | Test: un job forzado a fallo aparece en `/api/v1/jobs` con motivo legible |
| **G7** Documentado | `ESTADO_REAL.md` refleja la realidad; el backlog refleja lo implementado; el ADR registra las decisiones | Revisión cruzada plan ↔ código ↔ backlog |

---

## Tareas

Estado: `PENDIENTE` / `EN CURSO` / `BLOQUEADA` / `COMPLETADA`.

### Fase 0 — Truth · COMPLETADA

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-119.1 | Sellar los 4 artefactos sueltos del árbol (13 MB) + manifiesto SHA-256 | — | 0 binarios sueltos en el árbol versionado; manifiesto con hash de cada artefacto | **COMPLETADA** | `neural-news/storage/` + `backups/MANIFIESTO_SELLADO_2026-11-01.txt` — **E** |
| NN-119.2 | Verificar el backup previo a NN-107 | NN-119.1 | SHA-256 del ZIP igual al registrado | **COMPLETADA** | `c08d99b4…77d69d` coincide — **E** |
| NN-119.3 | Bundles de git de ambos repos | — | `git bundle verify` → *is okay* | **COMPLETADA** | `backups/bundles/*.bundle` — **E** |
| NN-119.4 | Backup **verificado** de PostgreSQL | — | Dump restaurado en base limpia con recuento idéntico | **COMPLETADA** | 20 tablas con recuento idéntico — **E** |
| NN-119.5 | `ESTADO_REAL.md` con la FASE 4 y los defectos | NN-119.4 | Menciona la transcripción automática y cada defecto con `fichero:línea` | **COMPLETADA** | `neural-news/ESTADO_REAL.md` §2, §5 — **A** |
| NN-119.6 | `IMPLEMENTACION_REALIZADA.md` con la FASE 4 | NN-119.5 | Registra la FASE 4 con sus commits | **COMPLETADA** | §FASE 5 — **A** |
| NN-119.7 | Reconstruir `BACKLOG.csv` con el estado real | NN-119.5 | Cada ítem con estado y evidencia coherentes con el código | **COMPLETADA** | 107 ítems reconstruidos — **A** |
| NN-119.8 | Registrar R-17…R-25 | NN-119.5 | El registro contiene los 9 riesgos nuevos | **COMPLETADA** | `12_REGISTRO_DECISIONES_Y_RIESGOS.md` — **A** |

### Fase 1 — Consolidación · COMPLETADA

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-108.1 | Archivar y sellar el repo hermano | NN-119.3 | Carpeta con todo el contenido + manifiesto SHA-256 + bundle; nada borrado | **COMPLETADA** | `archive/neuralnews-20261101/` (20 024 ficheros) + `backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt` — **E** |
| NN-108.2 | Remoto local + push | NN-108.1 | `git clone` del remoto reproduce commits y árbol | **COMPLETADA** | `.remotes/neural-news.git`; clon → 27 commits, árbol de 141 ficheros idéntico — **E** |
| NN-108.3 | Bundle + manifiesto del hermano | NN-108.1 | Bundle verificado + hash por fichero versionado | **COMPLETADA** | `backups/bundles/neuralnews-2026-11-01.bundle` — **E** |
| NN-108.4 | Herramientas fuera del árbol | NN-119.1 | `ffmpeg-local/`, `pglocal/`, `tools/` no versionados ni en el árbol | **COMPLETADA** | Viven en la raíz del workspace, fuera del repo — **A** |
| NN-108.5 | `.gitignore` ampliado | NN-119.1 | Cubre zip/rar/`.env`/`storage/`/`tools/`/`archive/`/`.remotes/` | **COMPLETADA** | `neural-news/.gitignore` — **A** |
| NN-108.6 | Rama `beta/v1` | NN-108.2 | Rama creada desde `main` y empujada | **COMPLETADA** | `beta/v1` @ `ef01bd0` — **E** |
| NN-108.7 | README único | NN-119.5 | Un solo README con arranque, variables, qué se puede probar y límites | **COMPLETADA** | `neural-news/README.md` — **A** |

### Fase 2 — Defectos · COMPLETADA

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-109.1 | B1 — `source.metadata` → `metadata_json` + test de pódcast | NN-108.6 | Test rojo antes / verde después | **COMPLETADA** | `test_b1_spotify_con_feed_descarga_la_transcripcion` — **E** |
| NN-109.2 | B2 — la transcripción del alta no se pierde | NN-109.1 | Test de regresión + E2E | **COMPLETADA** | `test_b2_la_transcripcion_del_alta_se_guarda` — **E** |
| NN-109.3 | B3 — se persiste el paso «Resultado» | NN-109.1 | Los 8 pasos se guardan y se recuperan | **COMPLETADA** | `test_b3_los_ocho_pasos_se_pueden_guardar` — **E** |
| NN-109.4 | B4 — severidad explícita en los mensajes | NN-109.1 | `found:false` no se pinta como éxito | **COMPLETADA** | `MSG_CLASS` `ok/warn/error` — **A** |
| NN-109.5 | B7 — el cliente no recibe texto crudo de excepción | NN-109.1 | `safe_error()` sin rutas/secretos; el detalle va al log | **COMPLETADA** | `neuralnews/errors.py` + 3 tests — **E** |
| NN-109.6 | B8 — caché con TTL y tope | NN-109.1 | TTL 3600/300 s, tope 64, negativos cacheados | **COMPLETADA** | 3 tests de caché — **E** |
| NN-109.7 | B9 — `NEURAL_API_URL` obligatoria | NN-109.1 | El build falla sin la variable, con mensaje explícito | **COMPLETADA** | Build sin la variable → error; con `NEURAL_ENV=local` → compila — **E** |
| NN-109.8 | B10/B11/B12 — código muerto, URL sin codificar, docstring | NN-109.1 | Sin código muerto; `quote()` en la URL; docstring alineado | **COMPLETADA** | `providers/transcript.py`, `services/director.py` — **A** |
| NN-109.9 | B13/B14 — código muerto eliminado | NN-109.8 | `HelpModal.tsx` y `setError_clear` fuera | **COMPLETADA** | Recuperable en el historial — **A** |
| NN-109.10 | B15 — logout cierra solo la sesión actual | NN-109.8 | Otra pestaña sigue viva | **COMPLETADA** | `test_b15_logout_cierra_solo_la_sesion_actual` — **E** |
| NN-109.11 | B16 — `podcast:transcript` se leía de `href` | NN-109.1 | Se aceptan `href` y `url` | **COMPLETADA** | `test_b16_feedparser_expone_url_y_el_codigo_lo_acepta` — **E** |
| NN-109.12 | B17 — la identidad «NeuralDotAI» se colaba en 5 componentes | NN-109.1 | 0 apariciones; F-01 recorre todo el árbol | **COMPLETADA** | `test_regressions_f01_f10.py` ampliado — **E** |
| NN-109.13 | B18 — `BackupModal` **se conserva** (capacidad real guardada por F-10) | NN-109.8 | No se elimina una capacidad | **COMPLETADA** | Cablearlo queda en NN-113 — **A** |
| NN-109.14 | B19 — el worker no completaba trabajos con salida redirigida | NN-109.1 | El trabajo termina aunque el log no codifique «→» | **COMPLETADA** | `test_b19_el_trabajo_termina_aunque_el_log_no_codifique_la_flecha` — **E** |
| NN-109.15 | B20 — la base viva estaba desfasada | NN-109.1 | Solo Alembic; base reparada; migraciones == modelos | **COMPLETADA** | `test_schema_migrations.py` (3) — **E** |
| NN-109.16 | B21 — el sondeo machacaba la edición del guion | NN-109.1 | `poll()` espera; temporizador por trabajo | **COMPLETADA** | E2E 7/7 — **E** |

### Fase 3 — Cola, latencia, leases y logging · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-110.a | Renovación de lease + recuperación periódica + `release_job` limpio | NN-109.14 | Un job largo no pierde el lease; un job vencido se recupera sin reiniciar el worker; `lease_until`/`attempt` se limpian | **COMPLETADA** | `tests/test_queue_leases.py` (8 pruebas, rojas antes) · suite **167 passed, 1 skipped** — **E** |
| NN-110.b | Tipos de job `transcribe_source`, `build_montage`, `probe_media`, `extract_web` + handlers | NN-110.a | Cada handler es idempotente y tiene test | **COMPLETADA** | `tests/test_worker_jobs.py` (8 pruebas) · `services/transcription.py` y `services/montage.persist_animatica` · suite **175 passed, 1 skipped** — **E** |
| NN-110.c | `transcribe_source` → `202 + job_id` | NN-110.b | El handler responde en <2 s; la UI muestra el progreso y el resultado | **COMPLETADA** | `test_transcribe_responde_de_inmediato` (el handler tarda <1 s con un proveedor lento) · UI: `/fuentes` sigue el trabajo y distingue aviso de error — **E** |
| NN-110.d | `build_montage` → `202 + job_id` + `ffprobe` al worker | NN-110.b | Ídem; el MP4 importado nunca se destruye | **COMPLETADA** | `tests/test_montage.py` y `test_transiciones_movimiento.py` reescritos al recorrido encolar→worker→comprobar · E2E **7 passed** — **E** |
| NN-110.e | Logging estructurado + motivo de fallo normalizado | NN-110.a | El fallo queda en `Job.error` legible y en el log estructurado | **COMPLETADA** | `logging_setup.py` (JSON por evento) + columna `jobs.error_kind` con migración `c4d2e8f1a5b6` · `tests/test_logging_observabilidad.py` (6) · traza JSON verificada en ejecución real — **E** |
| NN-110.f | Verificación de latencia y E2E del recorrido | NN-110.c, NN-110.d | p95 < 2 s por endpoint; `beta-journey` en verde | **COMPLETADA** | `tests/test_latencia_handlers.py` (5) con el proveedor lento a propósito · `e2e/beta-journey.spec.ts` · suite **187 passed, 1 skipped** · E2E **8 passed** — **E** |

### Fase 4 — Beta-go-live · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-111.1 | `NEURAL_ENV=local\|beta\|prod` gobierna demo, cookie, allowlist y esquema; el arranque **falla** si la configuración es incoherente | NN-109.7 | Sin `NEURAL_ENV=prod` la app no arranca con demo activo o cookie insegura | **COMPLETADA** | `Settings.comprobar()` en el arranque de API y worker · `tests/test_entorno_beta.py` — **E** |
| NN-111.2 | Cookie `secure`/`SameSite`/`dominio` por entorno | NN-111.1 | Sin `secure=False` hardcodeado | **COMPLETADA** | `Secure` fuera de local; `Domain`/`SameSite` configurables — **E** |
| NN-111.3 | `require_demo_disabled` aplicado a las rutas de pago/servicio externo | NN-111.1 | 0 usos → ≥1 uso real, con test | **COMPLETADA** | `/auth/demo` sólo en local; `require_paid_services` en `research`/`draft`/`analyze`; presupuesto con demo → 400 — **E** |
| NN-111.4 | Esquema **solo** por Alembic | NN-109.15 | `upgrade → downgrade → upgrade` verde en PG limpio | **COMPLETADA** | Ejecutado sobre `nn_beta_check` (PostgreSQL limpio): cadena de 4 migraciones, 32 tablas — **E** |
| NN-111.5 | Paridad SQLite/PostgreSQL | NN-111.4 | El esquema de local y de CI es el de producción | **COMPLETADA** | `tools/compare_schema.py`: 31/31 tablas y 0 diferencias en **ambos** motores — **E** |
| NN-111.6 | Descargas con streaming y corte real de bytes | — | El cuerpo no se carga entero en memoria antes de recortar | **COMPLETADA** | Lectura por trozos con parada en el límite (`tests/test_red_descargas.py`) — **E** |
| NN-111.7 | Mitigar DNS-rebinding (IP fijada o proxy de salida) | — | Test que cambia la resolución entre validar y conectar | **COMPLETADA** | Se comprueba la IP real de la conexión contra las validadas; se descarta si no encaja — **E** |
| NN-111.8 | Documentar la allowlist de red | — | `docs/SECURITY.md` recoge la lista y su motivo | **COMPLETADA** | `SECURITY.md` §1.1: motivo, alcance, riesgo asumido y lista actual — **A** |
| NN-111.9 | Argon2id para contraseñas | NN-117 | Hash argon2 con fallback PBKDF2 | PENDIENTE | — |
| NN-111.10 | Rate limit en `/auth/login` | — | Límite de intentos con respuesta clara | **COMPLETADA** | `rate_limit.py`: 5 fallos → 429 con enfriamiento; en memoria, por proceso — **E** |
| NN-111.11 | Escaneo de secretos (árbol + historial) | — | 0 hallazgos | **COMPLETADA** | `tools/scan_secrets.py`: **0 hallazgos** (3 avisos por la contraseña de ejemplo) — **E** |
| NN-111.12 | Checklist de despliegue de 20 puntos, verificado en máquina limpia | NN-111.1…NN-111.11 | Checklist firmado y ejecutado | **COMPLETADA** | `docs/DEPLOY.md`: 40 comprobaciones en 11 bloques, con la evidencia de lo verificado — **A** |

### Fase 5 — Frontend · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-113.1 | `loading.tsx` / `error.tsx` / `not-found.tsx` por sección | — | Ninguna sección puede quedar en blanco por un error de render | PENDIENTE | — |
| NN-113.2 | ESLint real (`eslint-config-next`) + `npm run lint` | — | El script se ejecuta y no falla | PENDIENTE | — |
| NN-113.3 | `npm run typecheck` + `strict` + `noUnusedLocals` + `noUncheckedIndexedAccess` | — | Script en verde; 0 `any` en el Studio | PENDIENTE | — |
| NN-113.4 | Cliente HTTP único con `ApiError` tipado | — | 1 solo `fetch`; 1 solo modelo de error | PENDIENTE | — |
| NN-113.5 | Propagar el error de `useJobPolling` | — | Las páginas muestran el fallo del trabajo | PENDIENTE | — |
| NN-113.6 | Un solo mapa de estado, compartido y generado | — | 0 duplicados del mapa de estados | PENDIENTE | — |
| NN-113.7 | Eliminar los `any` | NN-113.3 | 0 `any` en el Studio | PENDIENTE | — |
| NN-113.8 | A11y: teclado, `aria-label`, foco, contraste AA | — | Auditoría sin bloqueantes | PENDIENTE | — |
| NN-113.9 | Lint de clases inexistentes | — | `scrollbar-none`/`studio-root` sustituidas o definidas | PENDIENTE | — |
| NN-113.10 | `next/font` en vez de `<link>` externo | — | 0 peticiones bloqueantes a terceros | PENDIENTE | — |
| NN-113.11 | Idempotencia real por contenido | — | La clave no depende de `Date.now()` | PENDIENTE | — |
| NN-113.12 | Unificar el sistema visual | — | 1 sistema de componentes | PENDIENTE | — |
| NN-113.13 | Dividir los archivos grandes | — | Ningún componente >500 líneas sin motivo | PENDIENTE | — |
| NN-113.14 | `webServer` en Playwright | — | `npm run e2e` funciona sin pila levantada a mano | PENDIENTE | — |
| NN-113.15 | Cablear `BackupModal` (capacidad real, B18) | NN-113.1 | El Centro de mantenimiento es accesible desde la UI | PENDIENTE | — |

### Fase 6 — Reproducibilidad y CI · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-114.1 | `bootstrap.ps1` / `bootstrap.sh`: un comando | NN-111.4 | Clon limpio → pila arriba → suite verde | PENDIENTE | — |
| NN-114.2 | CI con la matriz (py 3.12 · pytest · PG real · tsc · build · E2E) | NN-114.1 | Los 3 workflows manuales pasan a automáticos | PENDIENTE | — |
| NN-114.3 | Cubrir módulos sin test: `providers/research.py`, `providers/video_analysis.py`, `api/ops.py` | — | Cada rama real tiene test | PENDIENTE | — |
| NN-114.4 | `openapi.json` regenerado y verificado en CI | — | Falla si el contrato exportado ≠ el servido | PENDIENTE | — |
| NN-114.5 | Equivalencia `export ≠ backup BD` verde tras los cambios | NN-114.1 | Test sigue verde | PENDIENTE | — |
| NN-114.6 | Corregir la fragilidad del `sys.path` (3 tests fallan desde `apps/api`) | — | La suite pasa desde **cualquier** directorio | PENDIENTE | — |
| NN-114.7 | Vídeo de la instalación desde un clon limpio | NN-114.1 | Vídeo en `evidence/` | PENDIENTE | — |

### Fase 7 — Reintegración selectiva del repo hermano · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-117.1 | Port de `backup/verify` de BD (`app/domain/media.py`) | NN-108.1 | Backup → restore en BD limpia → verificación de hash | PENDIENTE | — |
| NN-117.2 | Port de zonas seguras / cámara (`app/domain/camera.py`) | NN-108.1 | Test de etiqueta fuera de margen | PENDIENTE | — |
| NN-117.3 | Port del vault (`app/security/vault.py`) | NN-108.1 | Round-trip Fernet + `secret_status` | PENDIENTE | — |
| NN-117.4 | Port de rutas de modelo (`c0f68f32807d`) | NN-108.1 | Resolución de modelo en el job con snapshot | PENDIENTE | — |
| NN-117.5 | Port de Argon2id (`app/security/auth.py`) | NN-108.1, NN-111.9 | Test de sesión | PENDIENTE | — |
| NN-117.6 | Port de subtítulos SRT/VTT (`app/domain/subtitles.py`) | NN-117.1 | SRT/VTT desde los segmentos de transcripción | PENDIENTE | — |
| NN-117.7 | Port de contradicciones de cifras (`app/domain/contradictions.py`) | NN-117.1 | Test de contradicción sin auto-cambio | PENDIENTE | — |
| NN-117.8 | ADR de los descartes (scheduler, briefs, prompt catalog) | NN-108.1 | ADR-016 con la justificación | PENDIENTE | — |

### Fase 8 — Observabilidad y presupuesto · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-115.1 | Página `/ops`: trabajos, uso, presupuesto, salud | NN-110.e | La UI los muestra | PENDIENTE | — |
| NN-115.2 | `/health` que comprueba BD, FFmpeg, yt-dlp y proveedores | NN-115.1 | Un proveedor caído se ve en el health | PENDIENTE | — |
| NN-115.3 | Métricas: p95, tasa de fallo, duración y profundidad de cola | NN-115.1 | Métricas consultables | PENDIENTE | — |
| NN-115.4 | Alertas: cola parada, lease vencido, presupuesto 80 %, proveedor repetido | NN-115.3 | Alerta visible | PENDIENTE | — |
| NN-115.5 | Verificación E: un fallo de proveedor se ve en la UI en <60 s | NN-115.1 | Test cronometrado | PENDIENTE | — |
| NN-116.1 | Presupuesto verificado **antes** de la llamada | — | La llamada se corta, no se registra después | PENDIENTE | — |
| NN-116.2 | Tope diario real con contador | NN-116.1 | El tope frena de verdad | PENDIENTE | — |
| NN-116.3 | Coste estimado real por llamada, visible en `/ops/usage` | NN-116.1 | Coste ≠ 0.0 | PENDIENTE | — |

---

## Ideas fuera de alcance (detectadas, no ejecutadas)

Se anotan aquí para no perderlas y **no** se ejecutan sin decisión del propietario:

1. **Subtítulos SRT/VTT y contradicciones de cifras** están portados en el plan (NN-117.6/7) pero no son requisito de la beta.
2. **`/ops` con métricas persistentes**: se prevé métricas en memoria + health; un histórico exigiría otra base de datos.
3. **Caché distribuida de transcripciones**: hoy es por proceso; con más de una instancia habría que moverla a tabla.
4. **Pruebas de carga**: el plan pide «p95 por endpoint», no un test de carga sostenida.
5. **Migrar `newsV2/` al control de versiones** (riesgo R-26): requiere decisión porque cambia rutas ya documentadas.
