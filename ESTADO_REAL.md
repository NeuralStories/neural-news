# ESTADO REAL — neural.news (actualizado 01/11/2026)

**Repositorio activo:** `neural-news` · **Rama de trabajo:** `beta/v1` (desde `main` `ef01bd0`)
**Repositorio hermano:** `archive/neuralnews-20261101/` — **archivado y sellado** (ADR-016). Es fuente de capacidades, no un segundo producto.
**Plan rector:** [`newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md`](../newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md) · **Tarea:** [`newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md`](../newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md)

**Etiquetas:** FUNCIONA (probado con test automático) · PARCIAL (funciona con límites documentados) · PENDIENTE_POR_ACTIVO (falta material del propietario) · PENDIENTE_POR_API (falta integración externa autorizada) · NO_IMPLEMENTADO (fuera de la primera ventana).

> **Escala de verificación.** **E** = ejecutado (prueba real). **A** = verificado sobre el artefacto (fichero leído). **R** = derivado por código, sin ejecución. Las entradas de esta tabla son **E** salvo donde se indica lo contrario.

---

## 1. Estado del producto

**NO APROBADO — EN CURSO DE PREPARACIÓN DE BETA.** La lógica de Flow está reintegrada y operativa; la capa de entrega (corrección de defectos, cola, configuración por entorno) está en ejecución.

---

## 2. Recorrido de producción audiovisual

| Módulo | Estado | Evidencia |
|---|---|---|
| Proyectos de producción con persistencia PostgreSQL/SQLite vía API (CAS 409, revisiones inmutables por paso) | FUNCIONA | `tests/test_projects_studio.py` (11 tests; crear→editar→reiniciar→recuperar) — **E** |
| Biblioteca de medios: subida idempotente por SHA-256, almacén direccionado, ffprobe opcional, aprobación humana | FUNCIONA | `tests/test_projects_studio.py::test_take_media_upload_is_idempotent_and_never_autoapproved` — **E** |
| Studio Flow de 8 etapas integrado en Next.js **sin iframe** | FUNCIONA | E2E `studio-reintegration.spec.ts` (8 etapas + persistencia tras recargar) — **E** |
| Pestaña Noticias conectada al motor editorial (dossier con fuentes y estados) | FUNCIONA | `tests/test_editorial_graphics.py::test_dossier_shares_the_editorial_newsroom` — **E** |
| Director audiovisual determinista (cap. 7) | FUNCIONA | `tests/test_director_package.py` (7 tests, determinismo incluido) — **E** |
| Prompts versionados por toma | FUNCIONA | `test_prompt_versions_accumulate_and_take_becomes_prompt_ready` — **E** |
| `FlowManualPackage.v1` exportable | FUNCIONA | `test_flow_manual_package_requires_prompt_and_carries_full_instructions` — **E** |
| Importación de MP4 externo asociado a toma y revisión; aprobación/rechazo humano | FUNCIONA | E2E `vertical-production.spec.ts` — **E** |
| Gráficos programáticos (SVG determinista, valores exactos) | FUNCIONA (PARCIAL: **solo plantilla BAR**) | `tests/test_editorial_graphics.py` — **E**. Verificado: `api/projects.py:910` rechaza cualquier `chart_type != "BAR"` |
| Invalidación dirigida: cambio de guion → derivados INVALIDADO + auditoría | FUNCIONA (PARCIAL: solo la regla factual→derivados) | `test_script_change_invalidates_derived_graphics` — **E** |
| Correcciones de auditoría F-01…F-10 | FUNCIONA | `tests/test_regressions_f01_f10.py` (10 tests) — **E** |
| Montaje FFmpeg local 9:16 con transiciones xfade | FUNCIONA (PARCIAL: **animática sin locución**) | `tests/test_montage.py`, `tests/test_transiciones_movimiento.py` — **E**. Etiquetado como animática en `services/montage.py:235` |
| Runtime de Flow fuera del editor | PARCIAL (por diseño) | `features/studio/flow/adapter.ts`; E2E verifica banner BLOCKED — **E** |
| Regresiones heredadas R-BUG-1/2/3/4 | FUNCIONA | `TASK_NN-107` — **E** |

---

## 3. FASE 4 — Transcripción automática de cualquier fuente (01/11/2026)

Commits `4b9ec04`, `d9f89f6`, `ef01bd0`. **Estado: PARCIAL** — la cadena de proveedores funciona, pero el recorrido de usuario tiene defectos abiertos (ver §5, B1, B2, B4).

| Componente | Estado | Evidencia |
|---|---|---|
| Cadena de 3 proveedores: `yt-dlp` (principal) → `timedtext` (pistas manuales) → reproductor interno (ASR) | FUNCIONA | `tests/test_transcribe_ytdlp.py` (5), `test_transcribe_auto.py` (3), `test_transcribe_sources.py` (5) — **E** |
| Binario `yt-dlp` local sin dependencias de Python ni claves de API | FUNCIONA | `tools/yt-dlp.exe` (23,6 MB); búsqueda por `NEURAL_YTDLP_PATH` → PATH → rutas del repo — **A** |
| Idioma preferido con desempate por variante regional (`es-419` antes que `es`) | FUNCIONA | `providers/transcript.py:_pick_language` — **A** |
| Pista de pódcast `podcast:transcript` desde el feed RSS | **NO FUNCIONA** | **B1**: `api/sources.py:262` lee `source.metadata`, que no existe (el modelo expone `metadata_json`, `models.py:65`) → `AttributeError` enmascarado por el `except Exception` de `:290` |
| UI de transcripción en `/fuentes` | PARCIAL | **B2** (la transcripción pegada se descarta), **B4** (errores en verde) — ver §5 |

---

## 4. Pruebas (verificadas el 01/11/2026, tras NN-109)

- **API:** **154 passed, 1 skipped, 0 fallos** — **E**, desde la raíz del repositorio (`python -m pytest tests -q`, 65 s).
  - **Antes de NN-109: 139 passed, 1 skipped.** Las **15 pruebas nuevas** de `tests/test_nn109_defectos.py` cubren B1, B2, B3, B7, B8, B15 y B16, y se han verificado **rojas sobre el código original** (8 de 15 fallaban) y **verdes** después del arreglo.
  - ⚠ **Fragilidad pendiente (NN-114):** ejecutada desde `apps/api` la suite **falla 3 tests** (`ModuleNotFoundError: No module named 'tests.test_director_package'`) porque `apps/api/pyproject.toml` declara `testpaths = ["../../tests"]` pero los imports `from tests.*` no resuelven sin la raíz en `sys.path`. **Falta un `conftest.py` en la raíz o un `pythonpath` en la configuración de pytest.**
  - El skip corresponde al test de PostgreSQL real, que se activa con `NEURAL_TEST_POSTGRES`.
- **Tipos (web):** `npx tsc --noEmit` → **0 errores** — **E**.
- **Build (web):** `next build` → **compila**, 9 páginas estáticas — **E**. Y **falla a propósito** sin `NEURAL_API_URL` fuera de local (B9) — **E**.
- **E2E navegador real (Edge):** 2 specs — `studio-reintegration`, `vertical-production` — **E**.
- **Migraciones:** cadena `d38b9d62cb47 → d4ce8c95781e → b3c1d9e4f7a2` (head). Paridad modelos↔migraciones verificada por comparación estática de las 31 tablas — **R** (sin `alembic upgrade` ejecutado en esta auditoría).
- **PostgreSQL 16.9 local** (puerto 5433): dump, restauración en base limpia y comparación de recuento en 20 tablas → **idéntico**. **E**.
- **17/17 fuentes de Flow** contrastan con `reports/manifest.json` (SHA-256 + bytes). **E**.

---

## 5. Defectos verificados (01/11/2026) — estado tras NN-109

Todos **A** (verificados sobre el artefacto). **Estado**: `CERRADO` = corregido con test de regresión que falla antes y pasa después (**E**).

### 5.1 Defectos funcionales

| # | Defecto | Ubicación | Impacto | Estado |
|---|---|---|---|---|
| **B1** | `source.metadata` no existe (el modelo expone `metadata_json`) | `api/sources.py:262` | `AttributeError` en la ruta de pódcast, enmascarado por `except Exception` | **CERRADO** — corregido, y al arreglarlo se descubrió **B16**: la función nunca funcionó por dos motivos independientes. `test_b1_spotify_con_feed_descarga_la_transcripcion` — **E** |
| **B2** | La transcripción pegada en el alta se descartaba | `app/fuentes/page.tsx:90` + `services/sources.py` (rama de texto) | **Dos** puntos de pérdida: la interfaz no la enviaba y el backend la ignoraba en la rama de texto | **CERRADO** — `test_b2_la_transcripcion_del_alta_se_guarda` — **E** |
| **B3** | El paso **«Resultado» no se persistía** (7 de 8) | `features/studio/App.tsx` | Al recargar se perdía el estado del paso Resultado | **CERRADO** — 8.º paso persistido + hidratado; `test_b3_los_ocho_pasos_se_pueden_guardar` — **E** |
| **B4** | Errores pintados en verde de éxito | `app/fuentes/page.tsx:374` | «El vídeo no tiene subtítulos» se leía como operación correcta | **CERRADO** — severidad explícita `ok`/`warn`/`error`; `found:false` ya no se pinta como éxito — **E** (revisión visual en NN-113) |
| **B7** | `str(exc)` crudo devuelto al cliente | `api/sources.py`, `api/projects.py`, `services/sources.py`, `worker_tasks.py` | Fuga de rutas del sistema y stderr de ffmpeg | **CERRADO** — nuevo módulo `neuralnews/errors.py` con `safe_error()`; el detalle completo va al log — **E** |
| **B8** | Caché global sin TTL ni límite | `api/sources.py:18` | Crecimiento sin límite por proceso | **CERRADO** — TTL 3600 s (300 s para negativos) y tope de 64 entradas; los negativos también se cachean — **E** |
| **B9** | El rewrite caía en `127.0.0.1:8000` y el build **no fallaba** | `apps/web/next.config.ts` | Un build de producción sin la variable dejaba la app sin datos | **CERRADO** — `NEURAL_API_URL` obligatoria fuera de local; **el build falla con mensaje explícito** (verificado: sin la variable → error; con `NEURAL_ENV=local` → compila) — **E** |
| **B10** | `tracks` calculado y no usado | `providers/transcript.py:123` | Código muerto | **CERRADO** — **A** |
| **B11** | El nombre de la pista se interpolaba sin codificar | `providers/transcript.py:145-147` | Podía romper la URL | **CERRADO** — `quote()` — **A** |
| **B12** | El docstring anunciaba un default `PENDING` inexistente | `services/director.py:13` | Discrepancia documentación↔código | **CERRADO** — docstring alineado con el comportamiento real — **A** |
| **B13** | `HelpModal.tsx` sin usar | `features/studio/components/HelpModal.tsx` | 4 KB muertos | **CERRADO** — **eliminado**: es el «Manual y Contrato», herramienta retirada de la UI por decisión del propietario. Contenido recuperable en el historial |
| **B14** | `setError_clear` sin usar | `apps/web/lib/hooks.ts:46` | API muerta | **CERRADO** — eliminada — **A** |
| **B15** | `logout` borraba todas las sesiones del actor | `api/auth.py:57-59` | Expulsaba también de otras pestañas | **CERRADO** — ahora cierra solo la sesión actual — **E** |
| **B16** | `podcast:transcript` se leía del atributo `href` | `providers/transcript.py` | feedparser lo expone como `url`: **la transcripción de pódcast nunca se recuperó** | **CERRADO** — se aceptan `href` y `url` — **E** |
| **B17** | «NeuralDotAI» (nombre previo a la reintegración) en 5 sitios visibles | `BackupModal.tsx:95`, `ReferencesTab.tsx:138,365`, `ResultTab.tsx:142`, `VoiceTab.tsx:22` | Violaba la regla de identidad F-01 del propio proyecto; el test original solo miraba 4 ficheros y no lo detectaba | **CERRADO** — la comprobación F-01 ahora recorre **todo** el árbol del Studio (más fuerte que la lista fija) — **E** |
| **B18** | `BackupModal.tsx` sin usar | `features/studio/components/BackupModal.tsx` | **NO es código muerto**: es el «Centro de mantenimiento» (SHA-256 + descarga JSON), una capacidad real que la auditoría F-10 guarda | **ABIERTO por decisión** — se conserva; cablearlo es NN-113 |

### 5.2 Riesgos de plataforma (beta-go-live)

| # | Riesgo | Ubicación |
|---|---|---|
| **P1** | Cookie de sesión con `secure=False` **hardcodeado**; el comentario dice «activar via variable de entorno» pero no existe | `security.py:65` |
| **P2** | `demo_mode=True` por defecto habilita `/api/v1/auth/demo` sin contraseña. `require_demo_disabled` existe y **tiene 0 usos** | `config.py:23`, `api/auth.py:43-51`, `security.py:86` |
| **P3** | Doble fuente de esquema: `Base.metadata.create_all()` en SQLite convive con Alembic | `main.py:31-32` |
| **P4** | El lease del trabajo se fija una vez y no se renueva; los trabajos vencidos solo se recuperan al **arrancar el worker**; `release_job` no limpia `lease_until` ni `attempt` | `queue.py:99`, `queue.py:131-132`, `worker.py:36` |
| **P5** | Los errores del bucle del worker se escriben **solo a stderr**; `_worker.log` no los captura | `worker.py:51` |
| **P6** | El presupuesto no se verifica antes de la llamada; el coste se registra a posteriori como `cost_estimate=0.0` | `worker_tasks.py:143` |
| **P7** | El tope de bytes se aplica **después** de cargar el cuerpo completo en memoria | `providers/safety.py:80` |
| **P8** | TOCTOU de DNS-rebinding: se resuelve y valida una IP y `httpx` vuelve a resolver | `providers/safety.py:50` vs `:71-72` |

### 5.3 Trabajo pesado dentro del hilo de petición

| # | Riesgo | Ubicación | Duración máxima |
|---|---|---|---|
| **B5** | Transcripción: `yt-dlp --list-subs` + hasta 3 intentos × 2 banderas × timeout 180 s + backoff, **en la petición** | `api/sources.py:244` | >10 min |
| **B6** | Montaje: `subprocess.run(ffmpeg, timeout=600)`, **en la petición** | `api/projects.py:1021` → `services/montage.py:223` | 10 min |
| — | `ffprobe` de la subida de medios, **en la petición** | `api/projects.py:530,611` | — |
| — | Extracción web de artículos, **en la petición** | `api/sources.py:276` | 20 s (timeout del guardián SSRF) |

---

## 6. PENDIENTE_POR_ACTIVO (dependen del propietario)

- Handle real de maxDotAi en Flow y su hoja maestra aprobada: la ficha queda `PENDIENTE_DE_VINCULAR`.
- MP4 real generado en Flow por toma (la importación está probada con archivo de prueba; el flujo es idéntico).
- Referencias visuales aprobadas (las de ejemplo arrancan `pendiente`).
- Fondo CRT definitivo y marca visible definitiva.
- Voz definitiva y consentimiento para TTS.

## 7. PENDIENTE_POR_API

- Generación programática de imágenes/vídeo: requiere integración externa autorizada y comprobada (ADR-006).

## 8. NO_IMPLEMENTADO (declarado)

- TTS / voz real (el paso «Voz» persiste solo `voiceSpeed`).
- Render final con locución (hoy: animática sin audio, etiquetada correctamente).
- Gráficos line/timeline/percentage (**verificado: solo BAR**).
- Director LLM (el determinista funciona y es testeable).
- Publicación en plataformas; episodios 5/10 compuestos.
- Multiusuario / roles (el modelo es de un único editor).
- Subtítulos SRT/VTT, contradicciones de cifras, scheduler de feeds, briefs con abstención — **viven en el repo hermano archivado** y están portados en NN-117.

---

## 9. Estado de la consolidación (01/11/2026) — NN-108

| Ítem | Estado | Evidencia |
|---|---|---|
| Artefactos sueltos (13 MB de ZIP/RAR y 2 directorios) sacados del árbol | FUNCIONA | `neural-news/storage/` (gitignored) + `backups/MANIFIESTO_SELLADO_2026-11-01.txt` — **E** |
| Backup previo a NN-107 verificado | FUNCIONA | SHA-256 `c08d99b4…77d69d` **coincide** con el registrado — **E** |
| Dump de PostgreSQL + restauración verificada | FUNCIONA | 20 tablas con recuento idéntico entre original y copia restaurada — **E** |
| Bundles de git de ambos repos | FUNCIONA | `git bundle verify` → *is okay* — **E** |
| Remoto local + push de ambas ramas | FUNCIONA | `.remotes/neural-news.git` (3 ramas + tag) y `.remotes/neuralnews.git` — **E** |
| Clon limpio desde el remoto | FUNCIONA | 27 commits, árbol de 141 ficheros **idéntico**, working tree limpio — **E** |
| Repositorio hermano archivado y sellado | FUNCIONA | `archive/neuralnews-20261101/` (20 024 ficheros, repo git válido con su remoto) + `backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt` — **E** |
| Rama `beta/v1` creada desde `main` | FUNCIONA | `ef01bd0` — **E** |

> **Nota operativa:** la pila del repositorio hermano estaba **en marcha** (API en `:8800`, web en `:3100`) mientras se archivaba. Se detuvieron **solo** esos dos procesos; la pila principal (`neural-news`, API `:8000`, web `:3000`, worker) **siguió activa** durante toda la operación.

---

## 10. Entregables y ubicaciones

| Qué | Dónde |
|---|---|
| Repositorio activo | `NeuralStories/neural-news/` (rama `beta/v1`) |
| Remoto local | `NeuralStories/.remotes/neural-news.git` |
| Repositorio hermano archivado | `NeuralStories/archive/neuralnews-20261101/` |
| Manifiesto de sellado | `NeuralStories/backups/MANIFIESTO_SELLADO_2026-11-01.txt` |
| Manifiesto de archivo | `NeuralStories/backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt` |
| Bundles de git | `NeuralStories/backups/bundles/` |
| Dump de BD | `NeuralStories/backups/db/neuralnews-2026-11-01.sql` |
| Fuentes de Flow selladas | `NeuralStories/neural-news/storage/FLOW_RECOVERY_2026-11-01_DIR/` (17/17 verificadas) |
| Plan rector | `newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md` |
| Tarea | `newsV2/06_TASKS/TASK_NN-108_VERSION_BETA.md` |
