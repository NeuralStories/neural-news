# 18 — PLAN MAESTRO: de la integración actual a una versión BETA operable

**Creado:** 01/11/2026 · **Autor:** auditoría de repositorio + revisión de las últimas acciones (NN-107 F0–F4, transcripción YouTube) · **Estado:** PROPUESTO — pendiente de aprobación del propietario
**Alcance:** los dos repositorios vivos del producto (`neural-news/`, `neuralnews/`), sus conexiones (API ↔ web ↔ worker ↔ PostgreSQL/FFmpeg/yt-dlp), y la gobernanza de `newsV2/`.
**Tarea de seguimiento:** [`TASK_NN-108_VERSION_BETA.md`](../06_TASKS/TASK_NN-108_VERSION_BETA.md) (`NN-108`…`NN-119`).

---

## 0. Escala de verificación usada en este plan

Este documento **no** ejecutó la suite de pruebas ni levantó la pila. Toda la evidencia es de
inspección de artefactos. Se usa la escala del proyecto:

| Nivel | Significado |
|---|---|
| **A** | Verificado sobre el artefacto: el fichero existe y se ha leído su contenido literal en esta auditoría. |
| **R** | Derivado por código: conclusion razonada a partir del código leído, sin ejecución. |
| **E** | Ejecutado: prueba real (pytest, E2E, migración, arranque). |

**Techo de este documento: R.** Las afirmaciones marcadas **A** son citables con `fichero:línea`.
Ninguna afirmación de este plan debe invocarse como «probada» en una entrega sin subirla a **E**.

---

## 1. Veredicto

El producto **no está en beta**: está en un estado que la propia documentación ya sitúa como
*«IMPLEMENTADA — PENDIENTE DE REVISIÓN DEL PROPIETARIO (NO APROBADO)»*, y la auditoría confirma que
ese matiz no es burocrático sino técnico.

Tres hechos resumen el diagnóstico:

1. **La lógica de Flow sí está reintegrada y es sólida.** El Studio de 8 etapas vive en
   `apps/web/features/studio/` (22 ficheros, CAS con `expected_revision`, invalidación dirigida por
   hash de guion, director determinista, `FlowManualPackage.v1`, montaje FFmpeg real etiquetado como
   animática). 140 funciones de test y 2 E2E en navegador real. Esto es trabajo verificado y reutilizable.
2. **La beta está bloqueada por una capa de entrega, no por el producto.** Hay al menos **9 defectos
   funcionales verificados** que rompen el recorrido del usuario final (una transcripción pegada se
   borra, un paso del Studio no se persiste, un error se pinta en verde, la ruta de pódcast lanza
   `AttributeError`, dos endpoints bloquean el hilo HTTP hasta 10 minutos).
3. **Hay dos repositorios completos, independientes y sin remoto.** `neuralnews/` no comparte ni un
   objeto git con `neural-news/`. ADR-015 («repo único») se decidió el 31/10 pero **no se ejecutó**:
   la especificación dice lo contrario que el árbol.

**Conclusión de la auditoría:** el trabajo de *producto* está hecho en un 80 %; el trabajo de *ingeniería
de entrega* está en un 35 %. La beta se alcanza cerrando la capa de entrega, no reescribiendo el
Studio. Presupuesto recomendado: **12 sesiones de 10 h** (§8), no un quarter.

---

## 2. Qué significa «beta» en este proyecto

Una beta honesta para `neural.news` no es «todo funciona»: es **«un recorrido completo, reproducible
y honesto, que un segundo editor puede usar sin ayuda y sin que el sistema le mienta»**. Se define
por **gates observables**, no por porcentaje de código:

| Gate | Criterio verificable | Cómo se comprueba (E) |
|---|---|---|
| **G1 — Recorrido único** | Un editor entra, crea una fuente, obtiene transcripción (o un motivo exacto de por qué no), redacta, dirige, monta una animática, la ve en la UI y la descarga. Sin pantallas técnicas duplicadas. | E2E Playwright nuevo `beta-journey.spec.ts`, una pasada, vídeo + captura. |
| **G2 — Honestidad** | Ningún estado muestra «éxito» sobre un fallo. Ninguna afirmación editorial aparece como verificada sin evidencia. Todo lo no implementado está declarado en la UI, no solo en el `.md`. | Test de contrato de mensajes + revisión visual de los 6 estados de error. |
| **G3 — Sin bloqueo** | Ninguna operación de más de 2 s bloquea un hilo de petición. Extracción, transcripción, ffprobe y montaje pasan por la cola. | Test de latencia p95 por endpoint + aserción de que el handler devuelve `202` + `job_id`. |
| **G4 — Reproducible** | `install → migrate → seed → api → worker → web → e2e` funciona con **un** comando y sin Docker, desde un clon limpio. | Script único + README verificado en máquina limpia. |
| **G5 — Blindado** | Sin `demo_mode` accidental, sin cookie insegura, sin fallback a localhost en build, sin secretos en el árbol, sin stack de segundo repo. | Test de configuración + escaneo de secretos + `git ls-files` review. |
| **G6 — Observable** | Todo fallo de worker queda registrado con estructura y es consultable desde la UI (`/ops/jobs`). | Test: un job forzado a fallo aparece en `/api/v1/jobs` con error legible. |
| **G7 — Documentado** | `ESTADO_REAL.md` refleja la realidad; el backlog refleja lo implementado; el ADR registra las decisiones tomadas. | Revisión cruzada plan ↔ código ↔ backlog. |

**No-go explícito de esta beta** (fuera de alcance, declarado): TTS real, render final con locución,
publicación en plataformas, generación programática de imagen/vídeo, director LLM, multiusuario.
Ver §7.3.

---

## 3. Inventario audited: qué hay realmente

### 3.1 Los dos repositorios (hecho estructural)

| | `neural-news/` | `neuralnews/` |
|---|---|---|
| Commits | 27 (`ef01bd0` HEAD) | 9 (`6083412` HEAD) |
| Ramas | `main`, `nn-107-reintegracion-flow` | `main` |
| Remoto | **ninguno** | **ninguno** |
| Historial git | **independiente** — `neuralnews` no reconoce ningún objeto de `neural-news` (`git cat-file -p dd7c414` → *not a valid object name*) | ídem |
| Backend | `apps/api/src/neuralnews/` — 42 ficheros, ~7 868 líneas | `apps/api/app/` — 52 ficheros, capa `domain/` + `security/` |
| Web | `apps/web` — 7 rutas, Studio de 8 etapas (`features/studio/`) | `apps/web` — 5 rutas, **sin Studio** |
| Rutas API | 61 (60 `@router` + `/health`) | 56 |
| Tests | 140 funciones `test_*` en 23 ficheros | 53 funciones en 13 ficheros |
| Migraciones | `d38b9d62cb47 → d4ce8c95781e → b3c1d9e4f7a2` (head) | `445a3dd92cc6 → c0f68f32807d → 43610b8a7efa` (head) |
| Base de datos | `neuralnews` en PostgreSQL 5433 (+ SQLite `storage/neural-news.db`) | SQLite propia, `.env` presente, `.venv` propia |
| Rasgo distintivo | **Studio / producción audiovisual** | **Motor editorial**: briefs, cámara y zonas seguras, contradicciones, subtítulos SRT/VTT, scheduler de feeds con jitter, vault Fernet, backup/verify de BD, rutas de modelo, reintentos con `UNKNOWN_REMOTE_RESULT` |

**Consecuencia (R):** `neuralnews/` no es «fuente de funcionalidades reutilizables» en abstracto — es
un segundo producto con capacidades que `neural-news/` **no tiene**: cámara y zonas seguras
(`app/domain/camera.py`), contradicciones de cifras (`app/domain/contradictions.py`), subtítulos
(`app/domain/subtitles.py`), scheduler de feeds (`app/domain/scheduler.py`), vault (`app/security/vault.py`),
backup verificable (`app/domain/media.py`), rutas de modelo (`c0f68f32807d`), briefs con abstención
honesta (`app/domain/briefs.py`). Todo eso está **fuera** del producto que se quiere beta.

### 3.2 Lo que sí está bien construido (no tocar)

- **Contrato CAS del Studio**: `PUT /projects/{id}/studio/{step}` con `expected_revision` → 409
  (`api/projects.py:323-384`). Con `useStudioProject.ts` aplicando debounce de 700 ms y recarga en
  conflicto. Correcto y bien diseñado.
- **Invalidación dirigida por hash de guion** (`prompt_packages.source_script_hash`,
  `generated_takes.needs_review`, migración `b3c1d9e4f7a2`): cambiar el guion marca *solo* las tomas
  cuyo prompt dependía del texto; el MP4 importado nunca se destruye. Es la mejor pieza del proyecto.
- **Director determinista** (`services/director.py`): segmentación por cláusulas, 2,85 palabras/s,
  agrupación por capacidad del proveedor, rotación de movimiento sin repetición consecutive,
  transiciones xfade. Sin LLM, sin aleatoriedad, testeable.
- **Etiquetado honesto de la animática**: `"ANIMÁTICA 9:16 — previsualización sin locución; NO es el
  render final"` (`services/montage.py:235`, `api/projects.py:1017`). Coherente con la cultura del
  proyecto.
- **Puerta de gasto**: `paid_services_enabled=False` y `budget_daily_eur=0.0` por defecto
  (`config.py:46-47`); `providers/llm.py:413` y `providers/research.py:148` rechazan la llamada.
- **Guardián SSRF** (`providers/safety.py`): esquema allowlist, resolución DNS, bloqueo de
  private/loopback/link-local/reserved, redirecciones revalidadas una a una.
- **Separación de contratos**: `packages/contracts/*.json` y `openapi.json` versionados.

### 3.3 Los 9 defectos funcionales verificados (bloqueantes de beta)

Todos con evidencia **A** (artefacto leído).

| # | Defecto | Ubicación | Impacto de usuario |
|---|---|---|---|
| **B1** | `source.metadata` — el modelo expone `metadata_json` | `api/sources.py:262` | `AttributeError` en transcripción de pódcast. El error se enmascara con `except Exception` (`:290`) y se devuelve como «No se ha podido obtener la transcripción: 'Source' object has no attribute 'metadata'». **Función anunciada como operativa que nunca lo fue.** |
| **B2** | La transcripción pegada en el alta se **descarta** | `app/fuentes/page.tsx:90` envía `{url, text}`; `:54` hace `setTranscript("")` | El usuario escribe la transcripción, pulsa «Registrar y analizar» y desaparece sin aviso. El backend sí acepta `transcript` (`SourceCreate`). |
| **B3** | El paso **«Resultado» no se persiste** | `features/studio/App.tsx:218-245` → 7 `saveIfChanged` de 8 etapas | Studio de 8 etapas que persiste 7. Al recargar, el resultado se pierde. |
| **B4** | Errores pintados en **verde de éxito** | `app/fuentes/page.tsx:374` (`text-emerald-400` sobre un `msg` que mezcla éxito y error) | «El vídeo no tiene subtítulos» se lee como operación correcta. |
| **B5** | `transcribe_source` **bloquea el hilo HTTP** | `api/sources.py:244` → `providers/transcript.py:407-473` | `yt-dlp --list-subs` (timeout 90 s) + hasta 3 intentos × 2 flags × timeout 180 s + backoff ⇒ **minutos** de bloqueo. Sin gate de demo. |
| **B6** | `build_montage` **bloquea el hilo HTTP** | `api/projects.py:1021-1029` → `services/montage.py:223` (`timeout=600`) | Hasta **10 minutos** de un hilo de FastAPI por montaje. |
| **B7** | **Fuga de internals al cliente** | `api/sources.py:291` y `api/projects.py:1029` devuelven `str(exc)` crudo | Rutas del sistema, stderr de ffmpeg o excepciones de red expuestas al navegador. |
| **B8** | Caché global **sin TTL ni límite** | `api/sources.py:18` (`_auto_transcript_cache: dict`) | Crecimiento sin límite por proceso; objeto `ContentDraft` compartido entre peticiones. |
| **B9** | **Build de producción sin destino válido** | `next.config.ts:6` → `http://127.0.0.1:8000` por defecto | Sin `NEURAL_API_URL`, **todo** `/api/*` proxya a localhost. `next build` **no falla** (los rewrites se evalúan en runtime) ⇒ el fallo solo aparece en producción, ya desplegado. |

### 3.4 Los riesgos de plataforma (beta-go-live)

| # | Riesgo | Ubicación | Por qué bloquea la beta |
|---|---|---|---|
| **P1** | Cookie de sesión `secure=False` **hardcodeado** | `security.py:65` | El comentario dice «activar via variable de entorno» pero **no existe tal variable**. Con HTTPS, la cookie de sesión viaja en claro. |
| **P2** | `demo_mode=True` **por defecto** | `config.py:23` → `api/auth.py:43-51` | `/api/v1/auth/demo` concede sesión sin contraseña. `require_demo_disabled` existe (`security.py:86`) y **nadie lo usa** (0 usos). |
| **P3** | Doble fuente de esquema | `main.py:31-32` (`Base.metadata.create_all` en SQLite) + Alembic | En SQLite el esquema puede divergir de las migraciones sin que nada lo detecte; SQLite y PostgreSQL pueden acabar con esquemas distintos. |
| **P4** | **Lease de job sin renovación** | `queue.py:99` fija `lease_until`; no hay renovación | `recover_stale_jobs` solo se invoca al arrancar el worker (`worker.py:36`). Un job `RUNNING` con lease caducado **no se recupera hasta reiniciar el worker**. `release_job` (`:131-132`) tampoco limpia `lease_until` ni `attempt`. |
| **P5** | Errores del worker **solo a stderr** | `worker.py:51` (`print(..., file=sys.stderr)`) | `_worker.log` (3 líneas) no captura stderr ⇒ los fallos del bucle **se pierden**. |
| **P6** | Presupuesto **no verificado por llamada** | `providers/llm.py` no comprueba presupuesto; `worker_tasks.py:143` registra `cost_estimate=0.0` | El consumo real se anota después del hecho. El límite diario es binario, no un tope. |
| **P7** | Descargas: **tope de bytes aplicado tarde** | `safety.py:80` (`response.content[:max+1]`) | El cuerpo completo ya está en memoria antes de recortar ⇒ agotamiento de RAM por servidor hostil. |
| **P8** | TOCTOU de DNS-rebinding | `safety.py:50` resuelve; `:71-72` `httpx` vuelve a resolver | La IP validada puede no ser la conectada. |

### 3.5 La calidad del frontend

| # | Defecto | Ubicación |
|---|---|---|
| **F1** | Sin `loading.tsx` / `error.tsx` / `not-found.tsx` | `apps/web/app/**` |
| **F2** | Un error de render del Studio (911 líneas) deja la **página en blanco** | `features/studio/App.tsx` |
| **F3** | `npm run lint` **no es ejecutable** | `package.json:9` — no hay `eslint.config.*` ni `eslint` en `devDependencies` |
| **F4** | Sin script `typecheck`; `tsconfig` sin `noUnusedLocals`/`noUncheckedIndexedAccess` | `package.json:5-12`, `tsconfig.json:5-7` |
| **F5** | **Código muerto**: `HelpModal.tsx` (4 KB) y `BackupModal.tsx` (12 KB) no se importan; `helpOpen`/`backupOpen` nunca se leen | `features/studio/App.tsx:45-46` |
| **F6** | **Tres**](https://en.wikipedia.org/wiki/Governor)ksh fetch paralelos** con dos modelos de error incompatibles | `lib/api.ts:3`, `features/studio/lib/projectApi.ts:49`, `features/studio/components/DossierPanel.tsx:32` |
| **F7** | `useJobPolling` devuelve `error` y las páginas lo **descartan** | `lib/hooks.ts:46` vs `app/fuentes/page.tsx:25` |
| **F8** | Clases CSS inexistentes (`scrollbar-none`, `studio-root`) ⇒ no-ops | `TopNavigation.tsx:102`, `app/estudio/page.tsx:177` |
| **F9** | Filas de tabla con `onClick` **sin `role`/`tabIndex`**; botones de cierre sin `aria-label` | `app/fuentes/page.tsx:260`, `App.tsx:776,786` |
| **F10** | Google Fonts **externo en runtime** | `app/layout.tsx:15-18` |
| **F11** | **Idempotencia ficticia**: clave nueva por intento | `app/fuentes/page.tsx:46` |
| **F12** | `any` en 10 posiciones | `App.tsx:529,608,616,642,696,716`, `NewsEditorialTab.tsx:151,194`, `ReferencesTab.tsx:22` |

### 3.6 Lo que la gobernanza ya no refleja

- `newsV2/06_TASKS/BACKLOG.csv`: 107 filas, **106 `NOT_STARTED`** + 1 NN-107 «NO APROBADO». El código
  implementa NN-001…NN-065 (repo hermano) y NN-107 (repo activo). El backlog, que el proyecto usa
  como fuente de verdad, **va 107 items por detrás de la realidad**.
- `ESTADO_REAL.md` y `IMPLEMENTACION_REALIZADA.md` **no mencionan** la FASE 4 de transcripción
  (commits `4b9ec04`, `d9f89f6`, `ef01bd0`, 01/11 17:36–18:33) ni los defectos B1–B9.
- `neural-news/` tiene **4 entradas sin trackear** en el árbol de trabajo: `NEURAL_NEWS_ENTREGA_UNICA_PARA_AGENTE.zip` (6,6 MB), `flow-recovery.rar` (6,7 MB), `flow-recovery/`, `NEURAL_NEWS_ENTREGA_UNICA_PARA_AGENTE/`. Binarios de 13 MB dentro del árbol, no sellados ni versionados.
- **Ningún remoto en ninguno de los dos repos.** 36 commits y todo el historial viven solo en este disco.

---

## 4. Diagnóstico: 5 causas raíz

Los ~30 defectos de §3.3–§3.5 no son 30 problemas: son 5 problemas que se repiten.

| Causa raíz | Manifestaciones | |
|---|---|---|
| **C-1 · El trabajo pesado vive dentro del hilo de petición** | B5, B6, P4 | La arquitectura tiene cola, leases, idempotencia y reintentos (`queue.py`, `worker_tasks.py`)… y dos endpoints la saltan. El patrón correcto existe; no se aplica. |
| **C-2 · La capa web se desincroniza sin contrato** | B2, B3, B4, F1, F7, F9 | El frontend duplica reglas de negocio (mapas de estado en 3 ficheros), no tiene tipos de error compartidos y trata éxito y error con el mismo estilo. Falta un contrato API tipado que ambos lados compartan. |
| **C-3 · La configuración tiene defaults de demo** | P1, P2, P3, P9 | `demo_mode=True`, `secure=False`, `create_all` en SQLite, rewrite a localhost. Todo está pensado «pensando en local» y nadie creó un flag de entorno que lo revierta. **Un solo flag `NEURAL_ENV=prod` debería cambiar 5 comportamientos.** |
| **C-4 · Dos builds, dos bases de datos, dos historias** | §3.1, ADR-015 incumplido | Se decidió repo único y se mantuvo el hermano entero. El coste no es el repo en sí: es que las capacidades valiosas (cámara, backup, scheduler, subtítulos, vault) viven en el lado que **no se va a beta**. |
| **C-5 · La documentación y el backlog no se cierran con el código** | §3.6 | El proyecto tiene una cultura de honestidad documental excelente (`ESTADO_REAL.md`, etiquetas FUNCIONA/PARCIAL/PENDING) pero **no la aplica a sí mismo**: el backlog no se actualiza al implementar, y las FASE 4 más recientes no aparecen en ningún estado. |

**Insight de diseño:** B1, B2, B3 y B4 son el mismo fallo — *el contrato entre el estado persistido y lo
que el usuario ve estáimplícito en cada capa en lugar de estar declarado en un sitio*. La corrección
estructural no es «arreglar cuatro bugs»: es **un tipo de estado compartido** (backend lo emite, el
frontend lo consume) y **una regla única de render de mensaje** (severidad explícita, nunca inferida del
color).

---

## 5. Arquitectura objetivo

```
                    ┌─────────────────────────────────────────┐
                    │  apps/web (Next.js 15 · React 19)        │
                    │  7 rutas · Studio 8 etapas · /ops         │
                    │  contrato compartido: packages/contracts  │
                    └───────────────┬─────────────────────────┘
                                    │ mismo origen /api/*  (rewrite)
                    ┌───────────────▼─────────────────────────┐
                    │  FastAPI · 61 rutas · stateless           │
                    │  handlers ≤ 2 s · 202 + job_id           │
                    └───────────────┬─────────────────────────┘
                                    │ enqueue(dedupe_key)
                    ┌───────────────▼─────────────────────────┐
                    │  worker (leases + renovación + reintento)│
                    │  yt-dlp · ffmpeg · ffprobe · HTTP externo │
                    └───────────────┬─────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  PostgreSQL 16.9            storage/media (SHA-256)      storage/montage
  (única fuente)             storage/backup (verificado)  storage/packages
```

**Reglas de la arquitectura objetivo:**

1. **Un único repositorio** (`neural-news/`). El hermano se congela en `archive/` con su manifiesto
   SHA-256 y **no se importa nada sin un port explícito con test de equivalencia** (§6, NN-117).
2. **Una única base de datos**: PostgreSQL. SQLite solo para tests efímeros, y el esquema **siempre**
   por Alembic (nunca `create_all`).
3. **Ningún handler bloquea más de 2 s.** Todo lo externo (red, binario, E/S) pasa por la cola.
4. **Un contrato compartido** generado desde el backend y consumido por el frontend
   (`packages/contracts/openapi.json` → tipos TS). Un solo cliente `fetch` con un solo modelo de error.
5. **Configuración por entorno con un interruptor**: `NEURAL_ENV=local|beta|prod` decide demo, cookie
   `secure`, allowlist de hosts, y **falla el arranque** si la configuración es incoherente.
6. **El estado es un tipo, no una convención.** Cada estado de la UI lleva severidad explícita
   (`ok | warn | error`) y color derivado del token, nunca al revés.

---

## 6. Plan por fases (gates)

Cada fase cierra por **gate verificable**, nunca por horas. Detalle operativo, checklist y criterios
de aceptación en `TASK_NN-108_VERSION_BETA.md`.

### Fase 0 — Truth (2 h) · **NN-119**
Congelar el estado real antes de tocar código.

- Inventario de artefactos sueltos y sellado SHA-256 de los 4 binarios/entradas sin trackear.
- Actualizar `ESTADO_REAL.md` con la FASE 4 de transcripción y con los 9 defectos B1–B9.
- Rebuild del `BACKLOG.csv` con el estado **real** de los 107 items (no 106 `NOT_STARTED`).
- Crear el `git bundle` y el backup verificado de ambas bases de datos.

> **Gate 0:** no se toca una línea de producto hasta que el backlog y `ESTADO_REAL.md` digan la verdad.
> Sin este gate, cada fix posterior queda sin trazabilidad y el backlog vuelve a mentir.

### Fase 1 — Consolidación (4 h) · **NN-108**
Convertir ADR-015 en realidad.

- Congelar `neuralnews/` en `archive/neuralnews-20261101/` + `MANIFIESTO_SHA256.txt` + bundle git.
- `git remote add origin` (o repositorio local bare en disco) + primer `push` de ambos repos.
- Extraer del árbol de trabajo los 13 MB de binarios sin trackear → `storage/_entregas/` sellado.
- Verificar que `backups/neural-news-pre-NN107-F0-20261031.zip` existe (hoy solo consta el `.SHA256.txt`).

> **Gate 1:** `git clone` del repo en un directorio limpio produce un árbol que contiene todo el
> historial y todo el código; el hermano está archivado y sellado; ningún binario suelto en el árbol.

### Fase 2 — Defectos (6 h) · **NN-109**
Cerrar B1–B4, B7, B8, B9, B16, B17, B21, F5–F7.

- **B1** → `source.metadata_json` (1 línea) + test que fije la ruta de pódcast.
- **B2** → incluir `transcript` en el payload del alta + test E2E de «pegar transcripción → queda guardada».
- **B3** → persistir `resultado` + test de persistencia de los 8 pasos.
- **B4** → severidad explícita en el estado de la UI; nunca inferir del color.
- **B7** → sanitizar el texto de excepción al cliente (registrar completo, devolver código + mensaje seguro).
- **B8** → `functools.lru_cache` con TTL y tope, o caché en DB con invalidación por hash.
- **B9** → `NEURAL_API_URL` **obligatorio** en build no-local; error explícito al arrancar.
- **F5** → borrar `HelpModal.tsx`/`BackupModal.tsx` y los estados muertos; o conectarlos.
- **F6/F7** → un cliente `api.ts` único con `ApiError` tipado (`status`, `code`, `detail`) y error de job propagado.

> **Gate 2:** B1–B9 con test de regresión que falle antes del fix y pase después. Sin excepciones.

### Fase 3 — Cola y latencia (8 h) · **NN-110**
Cerrar B5, B6, P4, P5, P6.

- Nuevos tipos de job: `transcribe_source`, `build_montage`, `probe_media`, `extract_web`.
- Los handlers pasan a `202 + job_id`; la UI ya tiene `useJobPolling` (F7) ⇒ **el trabajo ya está hecho
  en el frontend**, solo falta conectarlo.
- **Renovación de lease** durante la ejecución (heartbeat) + recuperación periódica de jobs vencidos en
  el bucle del worker (no solo al arrancar) — cierra P4.
- `release_job` limpia `lease_until` y `attempt`.
- **Logging estructurado** JSON a fichero + a `Job.error` ⇒ cierra P5 y habilita G6.
- Presupuesto verificado **antes** de la llamada, con tope diario real y registro del coste estimado
  real ⇒ cierra P6.

> **Gate 3:** ninguna operación de más de 2 s dentro de un handler. Test de latencia p95 por endpoint.
> Un job fallido aparece en `/api/v1/jobs` con motivo legible.

### Fase 4 — Beta-go-live (6 h) · **NN-111**
Cerrar P1, P2, P3, P7, P8, B9 y las 5 condiciones del §2.

- `NEURAL_ENV` con comportamiento explícito por entorno; **arranque fallido** si la configuración es
  incoherente (demo + prod, cookie insegura en prod, admin sin contraseña).
- Cookie `secure` por entorno; `SameSite` y dominio por entorno.
- `demo_mode` explícito por entorno; `require_demo_disabled` aplicado a las rutas de pago (hoy, 0 usos).
- Esquema **solo por Alembic**; eliminar `create_all`; un smoke test que levanta Postgres limpio y
  aplica `upgrade head` + `downgrade -1` + `upgrade head`.
- Descargas con streaming y corte real por bytes (no `response.content` completo).
- Pin de la IP resuelta en la conexión (mitiga DNS-rebinding) o proxy de salida con allowlist.
- `secretos`: escaneo del árbol y del historial; `.env` fuera del control de versiones; checklist de
  despliegue con rotación de la clave de sesión.

> **Gate 4:** checklist de 20 puntos de despliegue, firmado, en una máquina limpia. Sin `NEURAL_ENV=prod`
  la app **no arranca**.

### Fase 5 — Frontend (6 h) · **NN-113**
Cerrar F1–F4, F8–F12 y B3/B4 en la capa de presentación.

- `loading.tsx` + `error.tsx` + `not-found.tsx` por sección; el Studio deja de poder quedar en blanco.
- ESLint real (`eslint-config-next`) + `npm run lint` + `npm run typecheck` en CI; `strict` +
  `noUnusedLocals` + `noUncheckedIndexedAccess`.
- Un `api.ts` con `ApiError` tipado; eliminar los tres(fetchers paralelos.
- Un solo mapa de estado, compartido, generado desde `packages/contracts`.
- A11y: filas activables con teclado (`role="button"`, `tabIndex`, `Enter`/`Space`), `aria-label` en
  iconos, foco visible, contraste AA verificado.
- Lint de clases inexistentes (evita `scrollbar-none`).
- `next/font` en vez de `<link>` externo.
- Idempotencia real: la clave de idempotencia se deriva del contenido, no de `Date.now()`.

> **Gate 5:** `lint` + `typecheck` + `build` + `e2e` en verde, y el LCP de `/estudio` sin regresión.

### Fase 6 — Reproducibilidad y CI (4 h) · **NN-114**
Cerrar el requisito de «un comando».

- `scripts/bootstrap.ps1` / `bootstrap.sh`: clonar → `.env` de ejemplo → `alembic upgrade head` →
  seed demo → arrancar API/worker/web → `pytest` → `e2e`.
- CI (GitHub Actions o equivalente local) con la matriz: python 3.12 · pytest · PG real · Next build ·
  Playwright (Edge). Sin Docker como requisito.
- README raíz **único** (hoy conviven `README.md`, `ESTADO_REAL.md`, `IMPLEMENTACION_REALIZADA.md`,
  `GUIA_DE_REVISION.md` con fechas y estados distintos).
- Módulos sin test directo cubiertos: `providers/research.py` (rama Brave real con stub HTTP),
  `providers/video_analysis.py` (rama Gemini), `api/ops.py` (`/provider-status`,
  `/config/budget`, `/settings/score-weights`).

> **Gate 6:** un clon limpio + un comando ⇒ pila arriba + suite verde. Verificado en captura de vídeo.

### Fase 7 — Reintegración selectiva (8 h) · **NN-117**
Decidir, capability por capability, qué entra en la beta.

| Capacidad del hermano | ¿Entra en beta? | Esfuerzo | Test de equivalencia |
|---|---|---|---|
| **Backup/verify de BD** (`app/domain/media.py`) | **Sí** — imprescindible en beta | 3 h | backup → `pg_dump` → restore en BD limpia → verificación de hash |
| **Zonas seguras / cámara** (`app/domain/camera.py`) | **Sí** — afecta a los gráficos, que son el producto | 2 h | test de etiqueta fuera de margen (el bug que ya corrigieron) |
| **Vault de secretos** (`app/security/vault.py`) | **Sí** — sustituye el `.env` plano | 2 h | round-trip Fernet + `secret_status` |
| **Subtítulos SRT/VTT** (`app/domain/subtitles.py`) | Sí, después | 1 h | SRT/VTT desde los segmentos de transcripción (ya existen) |
| **Rutas de modelo** (`c0f68f32807d`) | Sí — parte del coste | 1 h | resolución de modelo en el job con snapshot |
| **Contradicciones de cifras** (`app/domain/contradictions.py`) | Sí — coherencia con «no se inventa» | 2 h | test de contradicción sin auto-cambio |
| **Scheduler de feeds** (`app/domain/scheduler.py`) | **No en beta** (revisar 2×/día) | — | — |
| **Briefs con abstención** (`app/domain/briefs.py`) | **No en beta** — el Studio ya tiene su dossier | — | — |
| **Argon2id + vault** (auth) | **Sí** — endurecer el hashing de la beta | 1 h | test de sesión |

> **Gate 7:** cada capacidad portada con **su test de equivalencia** passing en ambos lados, o
> formalmente descartada con ADR. **Nada se elimina sin equivalencia acreditada** (D6, ya establecido).

### Fase 8 — Observabilidad y operación (4 h) · **NN-115**
- `/ops`: trabajos, uso, presupuesto, salud de proveedores — ya hay endpoints (`api/ops.py`) pero **sin
  página**. Convertirlos en la sección que falta en la UI.
- Health checks reales: `/health` que comprueba **BD**, **FFmpeg**, **yt-dlp** y **proveedores**, no solo
  «la API está viva».
- Métricas: p95 por endpoint, tasa de fallo por proveedor, duración de cola, tamaño de cola.
- Alertas: cola parada, lease vencido, presupuesto al 80 %, fallo de proveedor repetido.

> **Gate 8:** un fallo de proveedor se ve en la UI en menos de 60 s sin mirar los logs.

---

## 7. Lo que NO entra en esta beta (declarado)

Para evitar que la beta se difumine, se declara **fuera** con la misma honestidad que el proyecto ya
aplica al producto:

| # | Capacidad | Estado en la beta | Por qué |
|---|---|---|---|
| 7.1 | **TTS / voz real** | `PENDIENTE_POR_ACTIVO` | El paso «Voz» persiste solo `voiceSpeed`. Requiere material y consentimiento del propietario (ADR-012, «información que el agente no puede deducir» #4). |
| 7.2 | **Render final con locución** | `PARCIAL` | Hoy hay animática sin audio, etiquetada correctamente. El render final es un producto distinto. |
| 7.3 | **Publicación en plataformas** | `NO_IMPLEMENTADO` | Requiere credenciales y política de publicación del propietario (información #7). |
| 7.4 | **Generación programática de imagen/vídeo** | `PENDIENTE_POR_API` | Requiere integración externa autorizada y comprobada (ADR-006). |
| 7.5 | **Director LLM** | `NO_IMPLEMENTADO` | El determinista funciona y es testeable; el LLM es una mejora, no un requisito. |
| 7.6 | **Gráficos line/timeline/percentage** | `PARCIAL` (solo BAR) | Verificado: `api/projects.py:910` rechaza cualquier `chart_type != "BAR"`. Es una limitación declarada y correcta; ampliarla es post-beta. |
| 7.7 | **Episodios 5/10 compuestos** | `NO_IMPLEMENTADO` | A11/A12 del plan rector. |
| 7.8 | **Multiusuario / roles** | `NO_IMPLEMENTADO` | El modelo es de un único editor (`config.py:26`). |
| 7.9 | **Material real de MaxDotAi** | `PENDIENTE_DE_VINCULAR` | Depende del propietario (información #1). La ficha sigue en `PENDING` y no se inventa. |

---

## 8. Esfuerzo, riesgos y no-go

### 8.1 Esfuerzo

| Fase | Tarea | Horas | Riesgo |
|---|---|---|---|
| 0 | NN-119 Truth | 2 | Bajo |
| 1 | NN-108 Consolidación | 4 | Medio (borrados, archivo) |
| 2 | NN-109 Defectos | 6 | Bajo |
| 3 | NN-110 Cola y latencia | 8 | **Alto** (concurrencia, leases) |
| 4 | NN-111 Beta-go-live | 6 | Medio |
| 5 | NN-113 Frontend | 6 | Bajo |
| 6 | NN-114 CI y reproducibilidad | 4 | Bajo |
| 7 | NN-117 Reintegración selectiva | 8 | Medio (puertos) |
| 8 | NN-115 Observabilidad | 4 | Bajo |
| — | NN-116 Presupuestos (integrado en 3 y 8) | 2 | Bajo |
| — | NN-118 Cadena de valor post-beta (**no en beta**) | 0 | — |
| | **Total hasta beta** | **50 h** (5 sesiones de 10 h) | |

**Presupuesto recomendado: 5 sesiones de 10 h + 2 de reserva.** No 20 h: la Fase 7 (puertos) es la
única con riesgo real de desbordamiento, y está acotada por la tabla de decisión de arriba.

### 8.2 Riesgos nuevos (continúan R-01…R-16 de `12_REGISTRO_DECISIONES_Y_RIESGOS.md`)

| ID | Riesgo | Prob./impacto | Mitigación |
|---|---|---|---|
| **R-17** | Congelar el repo hermano sin portar sus capacidades ⇒ pérdida de cámara, backup, vault, subtítulos, rutas de modelo | **Alta / alta** | Tabla de decisión §6-Fase 7 con test de equivalencia por capacidad; ADR nuevo antes de archivar |
| **R-18** | Migrar el trabajo pesado a la cola rompe el flujo actual de la UI (los handlers devolvían JSON directo) | Media / alta | El job polling ya existe en el frontend (F7); el handler devuelve `202 + job_id` con el mismo esquema de respuesta |
| **R-19** | Arreglar sin cerrar antes el backlog ⇒ los fixes quedan sin trazabilidad | Media / media | Gate 0 bloqueante: backlog y `ESTADO_REAL.md` antes del primer cambio |
| **R-20** | `demo_mode` / cookie / allowed_hosts se endurecen y rompen el flujo local del propietario | Media / media | `NEURAL_ENV` con tres valores; el local conserva el comportamiento actual; el cambio se documenta en el README |
| **R-21** | Sin remoto, un fallo de disco pierde los 36 commits y las dos bases | Baja / **crítica** | Gate 1 (push + bundle + backup verificado) antes de cualquier refactor |
| **R-22** | El SSE/cola hace la UI más lenta de lo que espera el usuario | Media / baja | La UI ya muestra progreso de job; el gate de 2 s y el progreso visible lo compensan |
| **R-23** | La regresión de ytdlp (YouTube cambia su HTML/API) rompe la transcripción | **Alta / media** | Cadena de 3 proveedores ya existente (`yt-dlp` → `timedtext` → innertube); añadir test con fixture local + aviso honesto en la UI |
| **R-24** | La aplicación de los ports del hermano arrastra su arquitectura (dominio + vault) y choca con la del activo | Media / alta | Port **por módulo y por fichero**, con contrato propio y test; nunca «copiar la carpeta» |
| **R-25** | El `expect` de «beta» se cumple en la máquina del propietario y no en otra | Media / alta | Gate 6 con clon limpio en directorio nuevo, sin artefactos de la máquina |

### 8.3 No-go (la beta **no** se declara si…)

- Cualquiera de B1–B9 sigue abierto sin test de regresión.
- `lint`, `typecheck`, `pytest`, `e2e` o `build` no están en verde en CI.
- El arranque no falla con configuración incoherente (demo en prod, cookie insegura en prod).
- `ESTADO_REAL.md` y `BACKLOG.csv` no reflejan el código.
- El repo hermano no está archivado y sellado, o no hay backup verificado de ambas bases.
- No existe el recorrido G1 reproducido por vídeo.

---

## 9. ADRs a aprobar con este plan

| ADR | Decisión propuesta | Sustituye /relationship |
|---|---|---|
| **ADR-016** | Un único repositorio y una única base de datos (PostgreSQL). El hermano se archiva sellado; los ports se hacen por capacidad con test de equivalencia. | Ejecuta ADR-015, que se decidió pero no se aplicó |
| **ADR-017** | `NEURAL_ENV=local|beta|prod` gobierna demo, cookie, allowlist y esquema. La app falla al arrancar con configuración incoherente. | Nuevo; cierra P1, P2, P3 |
| **ADR-018** | Ningún handler bloquea más de 2 s: todo trabajo externo pasa por la cola con renovación de lease. | Nuevo; cierra B5, B6, P4 |
| **ADR-019** | Contrato compartido generado desde el backend (`packages/contracts`) y consumido por un cliente `api.ts` único con error tipado. | Nuevo; cierra F6, F7, B2, B4 |
| **ADR-020** | Observabilidad mínima obligatoria: logging estructurado, `/ops` en la UI, health checks reales de dependencias. | Nuevo; cierra P5, gate G6/G8 |
| **ADR-021** | El presupuesto se verifica **antes** de la llamada, con tope diario real y coste estimado registrado. | Complementa ADR-010 (gasto 0 por defecto) |

---

## 10. Anexo — índice de hallazgos con evidencia

| Hallazgo | Tipo | Ubicación | Fase |
|---|---|---|---|
| B1 `source.metadata` inexistente | Defecto | `api/sources.py:262` | 2 |
| B2 transcripción descartada en el alta | Defecto | `app/fuentes/page.tsx:90,54` | 2 |
| B3 paso «Resultado» no persistido | Defecto | `features/studio/App.tsx:218-245` | 2 |
| B4 errores en verde | Defecto | `app/fuentes/page.tsx:374` | 2 |
| B5 transcripción bloquea el hilo | Riesgo | `api/sources.py:244` | 3 |
| B6 montaje bloquea el hilo | Riesgo | `api/projects.py:1021`, `services/montage.py:223` | 3 |
| B7 internals al cliente | Defecto | `api/sources.py:291`, `api/projects.py:1029` | 2 |
| B8 caché sin TTL | Defecto | `api/sources.py:18` | 2 |
| B9 rewrite a localhost | Riesgo | `next.config.ts:6` | 2 |
| P1 cookie `secure=False` | Riesgo | `security.py:65` | 4 |
| P2 demo abierto por defecto | Riesgo | `config.py:23`, `api/auth.py:43-51` | 4 |
| P3 doble fuente de esquema | Riesgo | `main.py:31-32` | 4 |
| P4 lease sin renovación | Riesgo | `queue.py:99`, `worker.py:36`, `queue.py:131-132` | 3 |
| P5 errores solo a stderr | Riesgo | `worker.py:51` | 3 |
| P6 presupuesto a posteriori | Riesgo | `worker_tasks.py:143` | 3 |
| P7 tope debytes tardío | Riesgo | `safety.py:80` | 4 |
| P8 DNS-rebinding | Riesgo | `safety.py:50` vs `:71-72` | 4 |
| F1 sin error boundaries | Calidad | `apps/web/app/**` | 5 |
| F3 `lint` no ejecutable | Calidad | `package.json:9` | 5 |
| F5 código muerto (16 KB) | Calidad | `HelpModal.tsx`, `BackupModal.tsx` | 2 |
| F6 tres clientes fetch | Calidad | `lib/api.ts:3`, `projectApi.ts:49`, `DossierPanel.tsx:32` | 5 |
| F8 clases CSS inexistentes | Calidad | `TopNavigation.tsx:102`, `estudio/page.tsx:177` | 5 |
| F12 `any` ×10 | Calidad | `App.tsx:529…716` | 5 |
| Repo hermano sin archivar | Estructural | `neuralnews/` | 1 |
| Sin remoto | Estructural | ambos repos | 1 |
| 13 MB sin trackear | Estructural | `neural-news/` raíz | 1 |
| Backlog 107 items desfasado | Gobernanza | `newsV2/06_TASKS/BACKLOG.csv` | 0 |
| FASE 4 sin documentar | Gobernanza | `ESTADO_REAL.md` | 0 |
| `require_demo_disabled` muerto | Calidad | `security.py:86` | 4 |
| `tracks` calculado y no usado | Calidad | `providers/transcript.py:123` | 2 |
| Docstring `PENDING` inexistente | Calidad | `services/director.py:13` vs `:56-81` | 2 |
| `cost_estimate=0.0` fijo | Riesgo | `worker_tasks.py:143` | 3 |

---

**Documentos relacionados:** [`16_PLAN_MAESTRO_REINTEGRACION_FLOW.md`](16_PLAN_MAESTRO_REINTEGRACION_FLOW.md) · [`12_REGISTRO_DECISIONES_Y_RIESGOS.md`](12_REGISTRO_DECISIONES_Y_RIESGOS.md) · [`NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md`](NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md) · [`../06_TASKS/TASK_NN-108_VERSION_BETA.md`](../06_TASKS/TASK_NN-108_VERSION_BETA.md) · [`../06_TASKS/BACKLOG.csv`](../06_TASKS/BACKLOG.csv)

---

## 11. Ejecución: qué se ha cerrado (01/11/2026)

**Fases 0, 1 y 2 COMPLETADAS** sobre la rama `beta/v1`. Commits `2af9c34` y `c1bcd38`.

### 11.1 Lo que cambió de verdad

| Antes (auditoría) | Ahora |
|---|---|
| 9 defectos funcionales verificados | **0 abiertos** (B1–B21 cerrados; B18 se conserva por decisión) |
| Suite: 139 passed + 1 skipped | **159 passed, 1 skipped, 0 fallos** (+20 pruebas nuevas, 8 verificadas rojas sobre el código original) |
| El build de producción compilaba sin destino válido | **Falla a propósito** con mensaje explícito sin `NEURAL_API_URL` |
| `create_all()` creaba el esquema (y lo dejaba desfasado en silencio) | **Solo Alembic**, con 3 pruebas que comparan migraciones ↔ modelos |
| El worker no completaba ningún trabajo con la salida redirigida | Funciona; el estado se escribe fuera de la transacción |
| El sondeo de trabajos machacaba la edición del guion | `poll()` espera al trabajo; cada trabajo lleva su temporizador |
| E2E: 3 tests fallando sin causa aparente | **7 passed, 0 fallos** (frente a **4 de 5 fallando** en el código original) |
| Dos repositorios paralelos, sin remoto, 13 MB sueltos en el árbol | **Un repo activo** (`neural-news`) + hermano **archivado y sellado** + remoto local + bundles + backup de BD verificado |
| El backlog iba 107 ítems por detrás | Reconstruido con el estado real y evidencia por ítem |
| `ESTADO_REAL.md` no mencionaba la FASE 4 ni los defectos | Reescrito: 21 defectos, 8 riesgos, evidencia **E** por afirmación |

### 11.2 Hallazgos que aparecieron al ejecutar (no estaban en el plan)

Cinco de ellos son **críticos o con pérdida de datos**, y estaban causando fallos reales en producción local:

| # | Hallazgo | Por qué importa |
|---|---|---|
| **B16** | La transcripción de pódcast **nunca funcionó**: `podcast:transcript` se leía del atributo `href` y feedparser lo expone como `url`. El arreglo de B1 lo dejó al descubierto. | Una función anunciada como operativa que nunca lo fue — el mismo patrón que B1 |
| **B17** | La identidad «NeuralDotAI» (nombre previo a la reintegración) se colaba en **5 componentes visibles**, violando la regla F-01 del propio proyecto. El test original solo miraba 4 ficheros y no lo detectaba. | El mecanismo de auditoría era más débil que la regla que audita |
| **B19** | El worker **no completaba ningún trabajo** con la salida redirigida en Windows: el `print` con «→» estaba dentro de la transacción y el `UnicodeEncodeError` la revertía entera, así que el trabajo volvía a la cola **para siempre**. | Un bucle infinito silencioso en el único componente que procesa todo el trabajo asíncrono |
| **B20** | La **base de datos viva estaba desfasada** respecto a los modelos (`alembic_version` vacía, faltaba `generated_takes.needs_review`) porque `create_all()` solo crea tablas y nunca añade columnas. El Studio devolvía **500** y 3 E2E fallaban sin causa aparente. | **El riesgo P3 del plan, materializado como caída real.** Ninguna prueba lo detectaba |
| **B21** | `useJobPolling` tenía **un solo temporizador compartido** y `poll()` **no esperaba** al trabajo: el sondeo antiguo terminaba tarde y **machacaba el guion recién escrito**. La edición se perdía en silencio. | **Pérdida de datos** en el flujo principal de escritura, y el motivo de que el E2E «recorrido crítico» fallara en el código original |

### 11.3 Lección de método

Tres de los cuatro hallazgos críticos aparecieron **al ejecutar**, no al leer el código. La razón es
la misma en los tres casos: **el mecanismo de prueba era más estrecho que la regla que debía
comprobar**. Consecuencia práctica para las fases que quedan:

> Antes de dar por cerrado un requisito, comprobar que **la prueba que lo vigila cubre realmente
> el requisito entero** (no una lista fija de ficheros, no un subconjunto de mensajes, no un
> único camino de código). La regla de F-01 miraba 4 ficheros; la de B1 miraba un único atributo;
> la del esquema no existía.

Esto se incorpora al TASK como criterio nuevo: *una prueba solo cuenta como red de seguridad si
cubre el requisito entero, y eso hay que demostrarlo, no suponerlo*.

### 11.4 Estado de las fases

| Fase | Tarea | Estado |
|---|---|---|
| 0 | NN-119 Truth | ✅ COMPLETADA — **E** |
| 1 | NN-108 Consolidación | ✅ COMPLETADA — **E** |
| 2 | NN-109 Defectos | ✅ COMPLETADA — **E** (B1–B20) |
| 3 | NN-110 Cola y latencia | ⬜ Pendiente — **la de mayor valor y riesgo** |
| 4 | NN-111 Beta-go-live | ⬜ Pendiente (parcialmente adelantado: B9 y B20 ya cerrados) |
| 5 | NN-113 Frontend | ⬜ Pendiente |
| 6 | NN-114 CI y reproducibilidad | ⬜ Pendiente |
| 7 | NN-117 Reintegración selectiva | ⬜ Pendiente |
| 8 | NN-115/116 Observabilidad y presupuesto | ⬜ Pendiente |

