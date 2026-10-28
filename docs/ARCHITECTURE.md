# ARCHITECTURE.md — Arquitectura del MVP neural.news

## 1. Vista general

```
┌─────────────┐     HTTP (cookie de sesión)     ┌──────────────┐
│  apps/web   │ ──────────────────────────────▶ │   apps/api   │
│  Next.js    │   proxy /api/* → API v1         │  FastAPI     │
└─────────────┘                                 └──────┬───────┘
                                                │ encola
                                                ▼
                                        ┌──────────────┐
                                        │  jobs (BD)   │◀── apps/worker (lease + reintentos)
                                        └──────┬───────┘
                                               │ handlers idempotentes
                        ┌──────────────────────┼──────────────────────┐
                        ▼                      ▼                      ▼
                  conectores             investigación           exportación
              (manual/web/YT/Spotify)   (claims + evidencia)     (ZIP/MD/JSON)
```

- **apps/api**: FastAPI + Pydantic v2 + SQLAlchemy 2.0. Paquete `neuralnews` (código en `apps/api/src/neuralnews`). También define los manejadores del worker.
- **apps/worker**: proceso separado (`neuralnews-worker` / `python -m neuralnews.worker`) que reclama trabajos de la tabla `jobs`. Arranque por entrypoint; usa el mismo paquete.
- **apps/web**: Next.js (App Router) + TypeScript + Tailwind. Las peticiones al backend pasan por el proxy de rewrites (`/api/*` → API), así la cookie de sesión es same-origin.
- **packages/contracts**: esquemas JSON de los contratos editoriales (extracción, investigación, redacción) reutilizables por agentes externos.
- **infra/**: docker-compose (PostgreSQL + API + worker + web), Dockerfiles, migraciones Alembic.
- **fixtures/**: contenidos ficticios reproducibles para demo y pruebas.
- **tests/**: pytest (unitarias + integración + E2E de API del recorrido crítico).

## 2. Módulos del paquete `neuralnews`

| Módulo | Responsabilidad |
|---|---|
| `config.py` | Ajustes por entorno (NEURAL_*); estado de claves; nunca guarda secretos |
| `models.py` | Entidades SQLAlchemy (§6 del encargo) + tipo `UTCDateTime` (fechas UTC seguras) |
| `states.py` | Estados y **transiciones permitidas** de fuente/noticia/trabajo + etiquetas de usuario en español |
| `db.py` | Motor/sesiones; SQLite con WAL y foreign keys ON |
| `security.py` | PBKDF2, sesiones en BD, cookie HttpOnly, dependencia `get_current_actor` |
| `queue.py` | Enqueue con dedupe, claim con lease, reintentos con backoff, recuperación tras reinicio |
| `worker_tasks.py` | Manejadores: `process_source`, `analyze_video`, `research_story`, `draft_script`, `export_batch` |
| `providers/` | Adaptadores: `manual`, `web_rss`, `youtube`, `spotify`, `video_analysis` (Gemini), `llm` (editorial), `research`, `image_prompt`, `safety` (SSRF), `base` (contratos tipados), `fixtures` (demo) |
| `services/` | `sources` (alta/dedupe/obtención/extracción), `research` (claims, evidencia, scoring), `scripts` (versiones, concurrencia, aprobación), `batches` (lotes + paquete), `budget` (presupuesto y consumos) |
| `api/` | Routers v1: auth, sources, stories, batches, ops (jobs, usage, provider-status) |

## 3. Modelo de datos (entidades principales)

`sources` → `source_contents` → `source_segments`; `stories` ↔ `story_sources` (N:M con segmento opcional); `claims` → `evidence`; `script_versions` (único por story+version, `content_hash`); `approvals` (vinculadas a versión exacta; ACTIVE/INVALIDATED/REVOKED); `batches`/`batch_items` (posición); `jobs` (dedupe_key única, lease, reintentos); `production_packages` (versión + sha256 + estado); `usage_events`/`audit_logs`; `sessions`; `app_settings` (presupuesto y pesos de puntuación).

Índices/consistencia: único (provider, external_id) en fuentes; `content_hash` en contenidos; dedupe por `topic_key` en noticias y por `dedupe_key` en trabajos; fechas UTC; borrado protegido por claves ajenas; archivos del paquete en disco (`storage/packages`), no en filas.

## 4. Estados y transiciones (definidos en `states.py`, probados)

- Fuente: `NEW → FETCHING → READY | PARTIAL | METADATA_ONLY | FAILED` (refetch permitido desde cualquier estado no FETCHING).
- Noticia: `CANDIDATE → RESEARCHING → REVIEW_REQUIRED → SCRIPT_DRAFT → APPROVED | REJECTED` (reinvestigar permitido desde REVIEW_REQUIRED/SCRIPT_DRAFT; editar tras aprobar devuelve a SCRIPT_DRAFT e invalida la aprobación).
- Trabajo: `QUEUED → RUNNING → DONE | RETRYABLE_FAILED | FAILED | UNKNOWN` (RETRYABLE_FAILED → RUNNING con backoff; máx. 3 intentos).
- Paquete: `DRAFT → EXPORTED` (el paquete anterior pasa a DRAFT al exportar una nueva versión).

Etiquetas de usuario (sin tecnicismos): «Pendiente», «Analizando», «Sin transcripción», «Revisar», «Aprobada», «Error», etc. (`states.py`).

## 5. Cola de trabajos

- **Idempotencia**: `dedupe_key` única; repetir una llamada con la misma clave devuelve el trabajo original. POST /sources admite `Idempotency-Key`.
- **Lease**: al reclamar, `lease_until = ahora + 300 s`. Al arrancar, el worker recupera los RUNNING con lease vencido como reintenables.
- **Reintentos**: backoff exponencial corto (30 s × intento); máx. 3. Los manejadores son idempotentes (dedupe de contenidos por hash, de noticias por topic_key, de evidencia por (claim, URL)).
- **Operaciones de pago**: nunca se reintentan a ciegas tras timeout — el bloqueo de presupuesto produce fallo definitivo con mensaje claro; el consumo se registra en `usage_events` antes y después.

## 6. Adaptadores de proveedores (interfaz común)

`FetchResult`/`ContentDraft`/`StoryDraft`/`ResearchDraft`/`ScriptDraft`/`StoryboardDraft` (Pydantic, `providers/base.py`). Cada adaptador tiene modo real y modo demo; en demo todo se marca (`demo: true`, URLs `.invalid`, textos «DEMO»). Ver PROVIDER_STATUS.md para el estado real de cada uno.

## 7. Seguridad aplicada (resumen; detalle en SECURITY.md)

SSRF (resolución DNS + bloqueo de rangos privados + allowlist + tope de bytes/redirecciones/tiempo), saneado de HTML (el contenido es dato, nunca instrucciones), contraseñas PBKDF2, cookie HttpOnly SameSite=Lax, sin secretos en logs ni export, servicios de pago desactivados por defecto con presupuesto configurable.
