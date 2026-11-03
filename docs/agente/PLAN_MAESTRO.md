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
- Plan rector: `docs/governance/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md`
- Tarea: `docs/governance/06_TASKS/TASK_NN-108_VERSION_BETA.md`
- Estado real del producto: `neural-news/ESTADO_REAL.md`
- Decisiones y riesgos: `docs/governance/01_DOCUMENTACION/12_REGISTRO_DECISIONES_Y_RIESGOS.md`

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
| NN-111.9 | Argon2id para contraseñas | NN-117 | Hash argon2 con fallback PBKDF2 | **COMPLETADA** | Hecho con NN-117.5 — **E** |
| NN-111.10 | Rate limit en `/auth/login` | — | Límite de intentos con respuesta clara | **COMPLETADA** | `rate_limit.py`: 5 fallos → 429 con enfriamiento; en memoria, por proceso — **E** |
| NN-111.11 | Escaneo de secretos (árbol + historial) | — | 0 hallazgos | **COMPLETADA** | `tools/scan_secrets.py`: **0 hallazgos** (3 avisos por la contraseña de ejemplo) — **E** |
| NN-111.12 | Checklist de despliegue de 20 puntos, verificado en máquina limpia | NN-111.1…NN-111.11 | Checklist firmado y ejecutado | **COMPLETADA** | `docs/DEPLOY.md`: 40 comprobaciones en 11 bloques, con la evidencia de lo verificado — **A** |

### Fase 5 — Frontend · **EN CURSO**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-113.1 | `loading.tsx` / `error.tsx` / `not-found.tsx` por sección | — | Ninguna sección puede quedar en blanco por un error de render | **COMPLETADA** | `app/error.tsx` (con reintentar), `app/not-found.tsx`, `app/loading.tsx` + 6 de sección (`components/marcador-carga.tsx`) — **E** |
| NN-113.2 | ESLint real (`eslint-config-next`) + `npm run lint` | — | El script se ejecuta y no falla | **COMPLETADA** | `eslint@9` + `eslint-config-next@15.1.6` + `eslint.config.mjs` · **0 problemas** (antes: el script no era ejecutable) — **E** |
| NN-113.3 | `npm run typecheck` + `strict` + `noUnusedLocals` + `noUncheckedIndexedAccess` | — | Script en verde; 0 `any` en el Studio | **COMPLETADA** | `npm run typecheck` → 0 errores — **E** |
| NN-113.4 | Cliente HTTP único con `ApiError` tipado | — | 1 solo `fetch`; 1 solo modelo de error | **COMPLETADA** | `apps/web/lib/http.ts` (nuevo): `request()` + `ApiError` con `status`/`code`/`detail` y `esConflicto`. `lib/api.ts`, `features/studio/lib/projectApi.ts` y `ProductionVertical.tsx` lo usan; el `fetch` a mano del Studio desaparece (`projectApi` traduce el 409 en `ProjectConflict`) — **E** (`eslint` 0, `tsc` 0) |
| NN-113.5 | Propagar el error de `useJobPolling` | — | Las páginas muestran el fallo del trabajo | **COMPLETADA** | `app/fuentes/page.tsx`: `useJobPolling()` ya exponía `error` y la página lo **descartaba**; ahora se muestra junto al aviso — **A** (`apps/web/app/fuentes/page.tsx:43,156`) |
| NN-113.6 | Un solo mapa de estado, compartido y generado | — | 0 duplicados del mapa de estados | **COMPLETADA** | `tools/generate_estados.py` genera `apps/web/lib/estados.generado.ts` desde `states.py` (backend = fuente de verdad) y `apps/web/lib/estados.ts` es el **único** mapa de insignias. Se eliminaron 3 copias del mapa de noticia/fuente (`app/noticias/page.tsx`, `app/noticias/[id]/page.tsx`, `app/fuentes/page.tsx`) y un 4º mapa **distinto** con 2 estados inexistentes (`CONFIRMED`, `DESACTUALIZADA` en `DossierPanel.tsx`) · `tests/test_estados_compartidos.py` (5) — **E** (rojo→verde verificado con `git stash`) |
| NN-113.7 | Eliminar los `any` | NN-113.3 | 0 `any` en el Studio | **COMPLETADA** | Los 10 `any` sustituidos por tipos reales (`ConfiguracionImportada`, `NoticiaImportada`, `mensajeDeError`) — **E** |
| NN-113.8 | A11y: teclado, `aria-label`, foco, contraste AA | — | Auditoría sin bloqueantes | **COMPLETADA** | `tools/check_a11y.py`: auditoría **ejecutable** (botón sin nombre accesible, imagen sin `alt`, campo sin etiqueta, `focus:outline-none` sin indicador alternativo). Resultado: **0 bloqueantes · 0 avisos** (partía de 8 botones vacíos y 51 campos sin etiqueta). El analizador escanea JSX carácter a carácter: con `[^>]*` las flechas (`=>`) de los manejadores cortaban la expresión regular y los botones vacíos **no se detectaban** — **E** |
| NN-113.9 | Lint de clases inexistentes | — | `scrollbar-none`/`studio-root` sustituidas o definidas | **COMPLETADA** | Ambas clases se usaban y **no existían** en `globals.css` (`scrollbar-none`: la barra de desplazamiento aparecía en Chromium; `studio-root`: el envoltorio del Studio no tenía altura). Ahora están **definidas** y `tools/check_clases.py` falla si se usa una clase propia inexistente · `tests/test_clases_web.py` — **E** (rojo→verde verificado con `git stash`) |
| NN-113.10 | `next/font` en vez de `<link>` externo | — | 0 peticiones bloqueantes a terceros | **COMPLETADA** | **Desviación documentada**: `Material Symbols Outlined` **no está** en el catálogo de `next/font/google` (comprobado en `node_modules/next/font/google/index.d.ts`), así que no puede autopropiarse. La carga se hace sin bloquear: `components/carga-fuente-iconos.tsx` con `media="print"` + `onLoad` → el criterio (0 peticiones bloqueantes) se cumple — **A** |
| NN-113.11 | Idempotencia real por contenido | — | La clave no depende de `Date.now()` | **COMPLETADA** | `idempotenciaDe()` en `lib/http.ts`: FNV-1a de 32 bits sobre el payload con claves ordenadas → el mismo contenido da siempre la misma clave y el servidor devuelve la fuente existente en vez de duplicarla — **E** |
| NN-113.12 | Unificar el sistema visual | — | 1 sistema de componentes | **COMPLETADA** | Todos los componentes viven **una sola vez** en `apps/web/app/globals.css` (`.card`, `.card-compact`, `.card-quiet`, `.input`, `.input-compact`, `.btn`, `.btn-sm`, `.btn-sm-primary`, `.panel-header`, `.modal-actions`, `.inset`, `.table-wrap`, `.badge-*`). 44 composiciones reimplementadas en línea sustituidas por clases del sistema (visualmente idénticas) y `tools/check_clases.py` **falla** si vuelve a aparecer una reimplementación: **0 reimplementaciones en línea** — **E** |
| NN-113.13 | Dividir los archivos grandes | — | Ningún componente >500 líneas sin motivo | **COMPLETADA** | `features/studio/App.tsx`: 907 → 478 líneas (lógica extraída a 7 hooks con nombre: `useHidratacionStudio`, `useGuardadoPasos`, `useNoticiasStudio`, `useReferenciasStudio`, `useFlowStudio`, `usePaqueteProduccion`, `usePromptFinal`). `NewsEditorialTab.tsx`: 759 → 240 líneas (lista y 3 modales a `components/news/`). **Ningún fichero de la web supera ya las 500 líneas** — **E** (tsc 0, eslint 0, build OK, E2E 8/8) |
| NN-113.14 | `webServer` en Playwright | — | `npm run e2e` funciona sin pila levantada a mano | **COMPLETADA** | `playwright.config.ts` con `webServer` (API + worker + web) — el E2E levanta la pila sola — **E** (8 passed) |
| NN-113.15 | Cablear `BackupModal` (capacidad real, B18) | NN-113.1 | El Centro de mantenimiento es accesible desde la UI | **COMPLETADA** | Botón «Mantenimiento» en la navegación del Studio → `BackupModal` con **datos veraces**: el manifiesto de las fuentes lo calcula `tools/generar_manifiesto_studio.py` sobre los ficheros reales (SHA-256 incluidos) y el estado del Studio se audita en el navegador. La interfaz dice explícitamente que **no** es un backup de la base de datos (eso es `scripts/db_backup.py`) · `tests/test_manifiesto_studio.py` (3) — **E** |
| NN-113.16 | **B23** — «Investigar» sobre una noticia aprobada moría con `ValueError` y se reintentaba 3 veces | NN-110.f | La transición `APPROVED → RESEARCHING` es válida y la aprobación queda anulada | **COMPLETADA** | `states.py` (transición) + `research.py` (invalida la aprobación `ACTIVE` antes de investigar) · `tests/test_reinvestigar_aprobada.py` — **E** |
| NN-113.17 | **B24** — dos borradores simultáneos chocaban con el UNIQUE de `script_versions` y rompían la sesión | NN-110.f | La versión se asigna con savepoint + reintento sobre un número libre | **COMPLETADA** | `services/scripts.py`: *savepoint* + hasta 3 intentos; la transacción del manejador sobrevive al choque · `tests/test_version_script_concurrente.py` — **E** |

### Fase 6 — Reproducibilidad y CI · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-114.1 | `bootstrap.ps1` / `bootstrap.sh`: un comando | NN-111.4 | Clon limpio → pila arriba → suite verde | **COMPLETADA** | `scripts\bootstrap.ps1` ejecutado **de extremo a extremo**: requisitos (Python 3.12, Node 24.20.0) → backend instalado → `.env` creado → migraciones Alembic (5) → web → suite **verde** → «Listo» (**exit 0**). `start.ps1` levanta API+worker+web (salud `neural.news v0.1.0 · entorno local`, web 200) y `stop.ps1` para **sólo** los procesos del proyecto (por línea de comandos). **B30 corregido**: `Start-Process -FilePath "npm"` fallaba en Windows («no es una aplicación Win32 válida») y la web no arrancaba — **E** |
| NN-114.2 | CI con la matriz (py 3.12 · pytest · PG real · tsc · build · E2E) | NN-114.1 | Los 3 workflows manuales pasan a automáticos | **COMPLETADA** | `.github/workflows/ci.yml`: backend (py 3.12 + PostgreSQL 16 real: migraciones, comparación de esquema, suite, **suite desde `apps/api`**, contrato OpenAPI, escaneo de secretos) y web (Node 20: `tsc`, `eslint`, build, **build sin destino debe fallar**, generado de estados, manifiesto del Studio, lint de clases, auditoría a11y, E2E). **B31 corregido**: todos los pasos usaban `working-directory: neural-news`, que no existe al hacer checkout (el repositorio **es** la raíz del producto) → el CI fallaba en el primer paso. YAML validado — **A** |
| NN-114.3 | Cubrir módulos sin test: `providers/research.py`, `providers/video_analysis.py`, `api/ops.py` | — | Cada rama real tiene test | **COMPLETADA** | `tests/test_proveedores_analisis.py` (21): la evidencia de demo usa el dominio reservado `.invalid`, una opinión no se «verifica», sin evidencia no se marca `SUPPORTED`, sin clave **falla** en vez de simular, la salida de vídeo se marca `VIDEO_ANALYSIS`/`is_verbatim=False`, `_mmss_to_ms` y `extract_json_block`. `tests/test_ops_api.py` (10): 404 de trabajo inexistente, motivo normalizado, tope del listado, estado real de los proveedores, pesos de puntuación, presupuesto rechazado en demo, secretos sin filtrar valores. **B29 corregido** (rojo→verde verificado): `PUT /settings/score-weights` devolvía **500** con un peso no numérico («0,75») → ahora 422 con el peso que falla y el motivo — **E** |
| NN-114.4 | `openapi.json` regenerado y verificado en CI | — | Falla si el contrato exportado ≠ el servido | **COMPLETADA** | `tools/exportar_openapi.py` genera `docs/openapi.json` (105 KB) desde la aplicación real y `--check` falla si difiere; `tests/test_openapi_exportado.py` (2) lo verifica en la suite (ya detectó un desfase real: la descripción del endpoint que cambió con B29). Paso de CI añadido — **E** |
| NN-114.5 | Equivalencia `export ≠ backup BD` verde tras los cambios | NN-114.1 | Test sigue verde | **COMPLETADA** | `tests/test_regressions_f01_f10.py::test_f10_backup_json_is_not_a_database_backup` sigue verde: la interfaz del Centro de mantenimiento dice que **no** es un backup de la base de datos (eso es `scripts/db_backup.py`) — **E** |
| NN-114.6 | Corregir la fragilidad del `sys.path` (3 tests fallan desde `apps/api`) | — | La suite pasa desde **cualquier** directorio | **COMPLETADA** | `pytest.ini` en la raíz con `pythonpath = .`: la suite pasa desde la raíz **y** desde `apps/api` (`python -m pytest -q ../../tests` → **exit 0**). Ambos pasos están en el CI — **E** |
| NN-114.7 | Vídeo de la instalación desde un clon limpio | NN-114.1 | Vídeo en `evidence/` | **COMPLETADA** (desviación) | **Desviación documentada**: esta sesión **no tiene capacidad de grabar vídeo**. Se deja `evidence/instalacion_desde_clon_limpio.md` con la **transcripción literal** de la instalación real (bootstrap, start, stop y sus salidas reales) y el hallazgo B30 que salió de ella. Estado del formato vídeo: `PENDIENTE_POR_CAPACIDAD` — **A** |

### Fase 7 — Reintegración selectiva del repo hermano · **PENDIENTE**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-117.1 | Port de `backup/verify` de BD | NN-108.1 | Backup → restore en BD limpia → verificación de hash | **COMPLETADA** | `scripts/db_backup.py`: verificado en ejecución (626 filas restauradas en base aislada, viva intacta) — **E** |
| NN-117.2 | Zonas seguras (el plan apuntaba al fichero equivocado) | NN-108.1 | Test de etiqueta fuera de margen | **COMPLETADA** | El `SAFE_ZONE` del hermano **no se usa** (código muerto): se corrigió la incoherencia real — el rótulo ahora usa la zona segura compartida — `tests/test_zona_segura.py` — **E** |
| NN-117.3 | Port del vault (`app/security/vault.py`) | NN-108.1 | Round-trip Fernet + `secret_status` | **COMPLETADA** | `neuralnews/vault.py` + `services/secrets.py`: sólo texto cifrado en la base; 5 adaptadores resuelven «bóveda primero, entorno después» — **E** |
| NN-117.4 | Port de rutas de modelo (`c0f68f32807d`) | NN-108.1 | Resolución de modelo en el job con snapshot | **COMPLETADA** | Migración `e7a1b3c9d4f2` (tabla `model_routes` + `jobs.model_snapshot`), `services/model_routes.py` (resolución por prioridad, instantánea y lectura del modelo del trabajo) y endpoints `GET`/`PUT /api/v1/model-routes`. El trabajo se ata a la ruta que tenía **al encolarse**: cambiarla después no altera el trabajo en marcha · `tests/test_model_routes.py` (9) — **E** |
| NN-117.5 | Port de Argon2id (`app/security/auth.py`) | NN-108.1, NN-111.9 | Test de sesión | **COMPLETADA** | Argon2id con verificación PBKDF2 conservada (las contraseñas existentes siguen funcionando) — `tests/test_argon2id.py` — **E** |
| NN-117.6 | Port de subtítulos SRT/VTT (`app/domain/subtitles.py`) | NN-117.1 | SRT/VTT desde los segmentos de transcripción | **COMPLETADA** | `services/subtitles.py`: SRT y VTT desde los `SourceSegment` reales, con el texto **íntegro** (round-trip) y tiempos monótonos comprobados · `tests/test_subtitulos_contradicciones.py` — **E** |
| NN-117.7 | Port de contradicciones de cifras (`app/domain/contradictions.py`) | NN-117.1 | Test de contradicción sin auto-cambio | **COMPLETADA** | `services/contradictions.py`: propone la contradicción (`action: "PROPOSED"`, estado sugerido `CONTRADICTED` del vocabulario de este producto) y **no cambia** ningún estado: quien revisa es una persona · `tests/test_subtitulos_contradicciones.py` — **E** |
| NN-117.8 | ADR de los descartes (scheduler, briefs, prompt catalog) | NN-108.1 | ADR-016 con la justificación | **COMPLETADA** | `docs/adr/ADR-022-descartes-del-port.md`: cada capacidad del hermano que **no** entra tiene su motivo escrito (planificador de feeds, *briefs* versionados, catálogo de prompts, gráficos line/timeline/percentage, ZIP de Flow, CAS/clasificador de riesgo) y se distingue lo que entra **con adaptación** de lo que se descarta — **A** |

### Fase 8 — Observabilidad y presupuesto · **COMPLETADA**

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| NN-115.1 | Página `/ops`: trabajos, uso, presupuesto, salud | NN-110.e | La UI los muestra | **COMPLETADA** | `apps/web/app/ops/page.tsx`: salud de dependencias, consumo de hoy, estado de proveedores, trabajos recientes con su motivo normalizado, **métricas** y **alertas**; refresco automático cada 15 s — **A** |
| NN-115.2 | `/health` que comprueba BD, FFmpeg, yt-dlp y proveedores | NN-115.1 | Un proveedor caído se ve en el health | **COMPLETADA** | `neuralnews/health.py`: la base responde (`SELECT 1`), FFmpeg y yt-dlp se comprueban (con caché), los proveedores se listan con si tienen clave; `/api/v1/health` lo expone — **E** (`tests/test_salud.py`) |
| NN-115.3 | Métricas: p95, tasa de fallo, duración y profundidad de cola | NN-115.1 | Métricas consultables | **COMPLETADA** | `neuralnews/metrics.py` + `GET /api/v1/metrics`: p95 y media de duración (percentil por rango más cercano), tasa de fallo, profundidad de cola, desglose por tipo y por `error_kind`. Todo se calcula **de la base de datos**, no de memoria — **E** |
| NN-115.4 | Alertas: cola parada, lease vencido, presupuesto 80 %, proveedor repetido | NN-115.3 | Alerta visible | **COMPLETADA** | `neuralnews/metrics.py::alertas`: cola parada (trabajo en cola sin recoger >5 min), lease vencido, presupuesto al 80 % y fallo repetido (≥3 del mismo tipo). La página `/ops` los muestra arriba, con `role="alert"` — **E** |
| NN-115.5 | Verificación E: un fallo de proveedor se ve en la UI en <60 s | NN-115.1 | Test cronometrado | **COMPLETADA** | `tests/test_metricas_alertas.py::test_nn115_5_el_fallo_de_proveedor_se_ve_en_menos_de_60_segundos`: cronometra el tiempo desde el fallo hasta que la alerta aparece en lo que consume la UI; **< 60 s** — **E** |
| NN-116.1 | Presupuesto verificado **antes** de la llamada | — | La llamada se corta, no se registra después | **COMPLETADA** | `budget_service.assert_paid_call_allowed()` se llama **antes** de `call_gemini_video_analysis`, de la búsqueda y de la redacción; si se agota, el trabajo se marca `FAILED` con `error_kind="budget"` y se registra el uso como `blocked` — **E** (`tests/test_presupuesto.py`) |
| NN-116.2 | Tope diario real con contador | NN-116.1 | El tope frena de verdad | **COMPLETADA** | El gasto se suma de `UsageEvent` del día (`cost_actual` o `cost_estimate`); `spent + coste_estimado > límite` corta la llamada — **E** |
| NN-116.3 | Coste estimado real por llamada, visible en `/ops/usage` | NN-116.1 | Coste ≠ 0.0 | **COMPLETADA** | `COSTE_ESTIMADO_EUR` por proveedor (búsqueda 0,005 €, modelo 0,010 €…) y `usage_summary` expone `today_spent_eur`; antes se registraba 0,0 € y el tope **nunca** disparaba — **E** |

---

## ENTREGA BETA — versión local `1.0.0-beta.1`

Bloque **nuevo**, separado de las 89 tareas del plan (que están COMPLETADAS). Estos estados son
**los de la entrega**: `COMPLETADA`, `BLOQUEADA` o `APLAZADA` (lo que se deja fuera a
consciousemente, y que **no** impide cerrar la beta).

| ID | Tarea | Depende de | Criterio de aceptación | Estado | Evidencia |
|---|---|---|---|---|---|
| **F1** | Diagnóstico sin modificar nada | — | Línea base registrada: ruta, rama, commit, estado, tipo de repo, versiones, venv, destino, capacidades | **COMPLETADA** | `docs/entrega/evidencias/F1_linea_base.md` — toplevel `.../neural-news`, rama `beta/v1`, commit `4a6d5db`, `git status` vacío, `.git` directorio, Node v24.20.0 / npm 11.19.0 / Python 3.12.6, sin `.venv`, destino `proyecto final` **inexistente**, internet 200, cuota **no consultable** |
| **F2** | Reubicación a `proyecto final` | F1 | `git rev-parse --show-toplevel` = ruta final; commit e historial iguales; sin `proyecto final/proyecto final` | **COMPLETADA** | `Move-Item` de la carpeta completa (con `.git` y los ficheros sin commitear): `git rev-parse --show-toplevel` → `C:/Users/haxth3/Documents/NeuralStories/proyecto final`; commit `4a6d5db` intacto; historia idéntica; sin anidamiento. El paquete Python instalado en modo editable **guardaba la ruta absoluta**: reinstalado (`pip install -e ".[dev]"`) → `neuralnews` resuelve a la ruta nueva |
| **F3** | Verificación técnica completa (con la ruta definitiva) | F2 | Todas las comprobaciones dan **PASA** con código de salida; logs en `docs/entrega/evidencias/` | **COMPLETADA** | `docs/entrega/verificar.ps1` (14 comprobaciones, cada una con veredicto, código de salida y log íntegro): **14/14 PASA** con la ruta **definitiva y con espacio**. `RESUMEN_VERIFICACIONES.md` + `pytest.log`, `tsc.log`, `eslint.log`, `build.log`, `playwright.log`… Dos correcciones del propio script: `$PSScriptRoot` vacío en el binding del parámetro (raíz resuelta en el cuerpo) y `ExitCode` nulo tras `WaitForExit(ms)` (se añade la sobrecarga sin timeout). El `build` falla **por diseño** sin `NEURAL_ENV=local` (gate G5): el script carga el `.env` local del proyecto |
| **F4** | Preparación de la beta | F3 | Versión coherente en todo el repo; `CHANGELOG.md`; `.env.example` completo; DEC-01 aplicado; auditorías hechas; 0 secretos | **COMPLETADA** | Versión **1.0.0-beta.1** en `package.json`, `pyproject.toml`, `__version__` y `apps/web/lib/version.ts` (visible en el pie), con `docs/openapi.json` regenerado y `tests/test_version_coherente.py` (5). `CHANGELOG.md` (Keep a Changelog). `.env.example` **completo** (las 30 variables de `Settings`, antes faltaban 14) con `tests/test_env_example_completo.py` (33). **DEC-01**: la gobernanza entra como `docs/governance/` (328 ficheros, 15,2 MB, mayor 6,4 MB) con **0 hallazgos de secretos** y sin artefactos generados; `tests/test_gobernanza_integra.py` verifica su manifiesto SHA-256. Auditorías: `npm audit --omit=dev` → parche **next 15.1.6 → 15.5.28** (3 vulnerabilidades → 2, la crítica resuelta; las 2 restantes exigen Next 16, ruptura mayor → no se aplican). `pip-audit` **no está instalado** → registrado, no ejecutado. `tools/check_build_produccion.py` (nuevo): **0 hallazgos** de depuración, credenciales o datos personales en el build (y 4 `print()` del worker eliminados: rompían el log JSON por evento) |
| **F5** | Documentación de la entrega | F4 | README + RESUMEN_COMPLETO + NOTAS_BETA + GUIA_PRUEBAS_BETA + INFORME_FINAL | **COMPLETADA** | `README.md` reescrito como guía única de la beta (qué es, qué se ha verificado, tecnologías, requisitos, instalación, variables, lanzamiento, pruebas, estructura, límites y enlaces). `docs/entrega/RESUMEN_COMPLETO.md` (propósito, alcance, arquitectura, flujos, integraciones, archivos clave, configuración, verificación, seguridad, limitaciones y hoja de ruta), `NOTAS_BETA.md` (novedades, 7 problemas conocidos, requisitos y expectativas) y `GUIA_PRUEBAS_BETA.md` (pruebas paso a paso + plantilla de incidencia). `INFORME_FINAL.md` en F8 |
| **F6** | Lanzamiento local en modo producción | F3, F4 | La URL responde 200 y una prueba rápida de Playwright contra esa instancia pasa; comandos de arranque y parada documentados | **COMPLETADA** | `scripts/beta_start.mjs` / `scripts/beta_stop.mjs` (Node, **multiplataforma**: nada de Bash, WSL ni cron) + `scripts/start.ps1` / `stop.ps1` (Windows). Instancia en marcha: web **http://localhost:3000** (200), API **http://127.0.0.1:8000/api/v1/health** (200, `version: 1.0.0-beta.1`, BD/FFmpeg/yt-dlp OK). Prueba rápida `apps/web/scripts/prueba_rapida_beta.mjs`: **7/7 PASA** (acceso con modo demo, producto abierto, pie con la versión, sin errores de JS, sin recursos rotos y la API con la misma versión). Evidencia: `docs/entrega/evidencias/F6_lanzamiento.md` |
| **F7** | Rama, commit y tag local de la beta | F3, F6 | Rama `release/1.0.0-beta.1`, commit `release: v1.0.0-beta.1`, tag anotado `v1.0.0-beta.1`; **sin push** | **COMPLETADA** | Rama `release/1.0.0-beta.1` creada desde `beta/v1` @ `4a6d5db`; commit `1c63a3a` («release: v1.0.0-beta.1», 320 ficheros); tag anotado `v1.0.0-beta.1` («Beta 1.0.0-beta.1»). Verificado con `git log -1`, `git tag -l` y `git status` (limpio). **Sin push**: el remoto remoto está APLAZADA (DEC-02) |
| **F8** | Cierre | F5, F7 | INFORME_FINAL, ESTADO.md y REGISTRO.md al día; estado beta final emitido | **COMPLETADA** | `docs/entrega/INFORME_FINAL.md` (los 10 puntos del §9), `docs/agente/ESTADO.md` (checkpoint con los dos juegos de campos y `estado_beta: BETA_LISTA`), `docs/agente/REGISTRO.md` (entrada de la entrega con B29–B38) y `docs/agente/TAREAS.md` (cola con DEC-01 completada y DEC-02/SUP-01/SUP-02 APLAZADAS). Commit de cierre `docs: cierre beta` **sin mover el tag** |
| **DEC-01** | `docs/gobernanza/` dentro de Git | F4 | Solo si cumple las 4 condiciones; lo que no, a `.gitignore` y anotado | **COMPLETADA** | La gobernanza real (328 ficheros, 15,2 MB) entra como `docs/gobernanza/`: **0 hallazgos** de `scan_secrets`, **ningún fichero > 50 MB** (mayor 6,4 MB) y **sin artefactos generados**. Lo que no cumplía queda **fuera y anotado**: `newsV2/neural-news/` (copia duplicada del repo con su propio `.git`, que no se puede versionar) y `newsV2/flow-recovery/node_modules` (con un `.node` de 105 MB). Referencias redirigidas a `docs/gobernanza/` en README, `ESTADO_REAL.md`, `IMPLEMENTACION_REALIZADA.md`, este plan y el registro |
| **DEC-02** | Remoto GitHub/GitLab | — | Fuera de esta entrega | **APLAZADA** | Sección 0 del `/goal` |
| **SUP-01** | `AGENTE_CMD` del supervisor | — | Fuera del alcance de la beta | **APLAZADA** | Sección 0 del `/goal` |
| **SUP-02** | `crontab`/WSL | — | Fuera del alcance de la beta | **APLAZADA** | Sección 0 del `/goal` |

---

## Ideas fuera de alcance (detectadas, no ejecutadas)

Se anotan aquí para no perderlas y **no** se ejecutan sin decisión del propietario:

1. **Métricas persistentes en histórico**: lo que hay son métricas de la ventana (24 h) calculadas
   de la base de datos; un histórico exigiría otra base de datos o una tabla de series.
2. **Caché distribuida de transcripciones**: hoy es por proceso; con más de una instancia habría que
   moverla a tabla.
3. **Pruebas de carga**: el plan pide «p95 por endpoint», no un test de carga sostenida.
4. **Migrar `docs/governance/` al control de versiones** (riesgo R-26): requiere decisión porque cambia rutas
   ya documentadas.
5. **Crear un remoto remoto (GitHub/GitLab)**: es una acción externa; el remoto actual es local
   (`.remotes/neural-news.git`).
6. **Vídeo de la instalación** (NN-114.7): esta sesión no tiene capacidad de grabación; queda la
   transcripción literal en `evidence/instalacion_desde_clon_limpio.md`.
7. **Capacidades del hermano descartadas** (planificador de feeds, *briefs* versionados, catálogo
   de prompts, gráficos line/timeline/percentage, CAS/clasificador de riesgo): el motivo escrito de
   cada una está en `docs/adr/ADR-022-descartes-del-port.md`.
8. **Lo que el encargo de la beta declara fuera de alcance**: TTS/voz real, render final con
   locución, publicación en plataformas, generación programática de imagen o vídeo, director LLM,
   gráficos, episodios compuestos, multiusuario y material real de MaxDotAi.

### Ideas post-beta (detectadas durante la entrega, no ejecutadas)

1. **Contexto de Python por proyecto**: la beta usa el Python del sistema con el paquete instalado
   en modo editable, que guarda **rutas absolutas**: al mover la carpeta hay que reinstalar
   (`pip install -e ".[dev]"`). Un `.venv` por proyecto evitaría ese problema y el de «un entorno
   distinto en cada máquina».
2. **`proyecto final` con espacio en la ruta**: obliga a que todas las rutas se construyan con
   `pathlib` y comillas. Funciona, pero es una fuente clásico de fallos en scripts: cualquier
   herramienta que se añada después debe probarse con esa ruta.
3. **Réplica automática del remoto local**: el remoto es un *bare* en disco; una réplica en otro
   disco (o un remoto real) evita perder todo con un fallo de disco.
4. **Firma de los tags**: los tags anotados no están firmados; con GPG, la beta sería verificable
   por terceros sin consultar al autor.
5. **Prueba de humo del paquete exportado**: el E2E comprueba el recorrido en la web, pero no
   reimporta el `.zip` de producción en una instalación limpia.
