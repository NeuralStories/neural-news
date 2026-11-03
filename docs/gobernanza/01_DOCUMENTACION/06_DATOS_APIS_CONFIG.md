# Datos, contratos, endpoints y configuración

## DB: PostgreSQL como fuente de verdad
Todas las tablas `id uuid`, `created_at timestamptz`, `updated_at`, `revision integer`, claves foráneas e índices explícitos. No eliminar historias: soft-delete/evento auditado donde sea necesario. Esquema inicial mínimo y ampliación por Alembic. Los ejemplos se ofrecen como especificación, NO migraciones ya ejecutadas.

### Diccionario relacional
| Tabla | Campos nucleares | Índices / controles |
|---|---|---|
| `users` | login, password_hash Argon2id, role, active | unique login |
| `sessions` | user, token_hash, expiry, revoked | no token en claro; índice vencimiento |
| `source_feeds` | url, domain, policy, enabled, interval, last_run | unique canonical URL |
| `source_items` | feed_id, canonical_url, external_id, published_at, title | unique(feed, external_id) cuando exista |
| `snapshots` | item, fetched_at, final_url, raw_sha256, text_sha256, raw_path, extract_status | unique item + hash; nunca sobrescribir |
| `snippets` | snapshot, ordinal, text, offsets, hash | unique(snapshot, ordinal) |
| `stories` | title, locale, first_seen, latest_at, status, main_source_id | index status,date |
| `story_sources` | story, snapshot, independence_group, is_primary | unique(story,snapshot) |
| `claims` | story, statement, claim_type, current_status, revision | index story,status |
| `claim_evidence` | claim, snippet, stance, quote, reviewed_by | unique(claim,snippet,stance) |
| `brief_revisions` | story, version, json_document, input_hash, approved_by | unique(story,version) |
| `script_revisions` | story, brief_revision, format, narration, hash, state, approved_by | unique story,format,version |
| `narration_beats` | script_revision, ordinal, start_ms, end_ms, text, claim_ids | unique(revision,ordinal), nonoverlap checked app |
| `production_plans` | story, script_revision, style_revision, format, version, status, hash | unique story,format,version |
| `shots` | plan, ordinal, start_ms, end_ms, source_kind, media_id, purpose, graphic_spec_id | positive duration, foreign keys |
| `media_assets` | owner, kind, source, sha256, mime, path, dimensions, fps, duration, rights, status | unique checksum within org if permitted |
| `identity_profiles` | name=`maxDotAi`, handle_status, description, revision, approved_by | only selected official active |
| `visual_presets` | kind, title, config_json, reference_assets, status, version | names unique/versioned |
| `graphic_specs` | plan, data_json, source_claim_ids, template, duration, status, hash | input links mandatory |
| `prompt_packages` | plan, shot, compiler_revision, prompt_en, prompt_es, refs_json, limitations | unique plan,shot,revision |
| `episodes` | name, date, format, status, total_duration | date status |
| `episode_items` | episode, story, script_rev, plan_rev, order, transition | unique episode,order |
| `provider_connections` | name, type, canonical_endpoint, enabled, policy_id, config_revision | unique provider name |
| `provider_secrets` | provider, ciphertext, key_version, updated_by | no plaintext in responses/logs |
| `model_routes` | task, provider_id, model_id, priority, config_revision, enabled | unique task,priority |
| `budget_policies` | scope, cap_amount, currency, period, paid_allowed | no unknown-rate paid calls |
| `usage_ledger` | job, provider, model, units, estimate, actual, invoice_ref | unique billed operation |
| `jobs` | type, payload_ref, status, idempotency_key, lease_owner, lease_until, attempts, next_run, cost_reservation | unique scoped idempotency key |
| `job_events` | job, when, status_from/to, message, error_class, trace | append-only, sanitize |
| `approvals` | entity_type, entity_id, revision_hash, approver, approved_at | unique entity/revision/action |
| `audit_events` | actor, action, target, old_hash,new_hash, time, details_sanitized | never secret |

### Integridad y riesgos
- `claim_evidence.snippet_id` apunta a texto persistido. Dos snippets de misma nota sindicada comparten grupo de independencia, nunca se cuentan como dos pruebas independientes.
- Archivos por SHA256 y ruta interna no ejecutable; verificación checksum al usar. `approved` solo por persona/rol, nunca por migración/seed.
- `jobs` usa lease y chequeo de idempotencia. Un trabajo de gasto con respuesta remota incierta queda `UNKNOWN_REMOTE_RESULT` y exige conciliación antes de reintentar; evitar doble consumo.
- Edición concurrente con `If-Match` revision_hash / `expected_revision`; un 409 nunca se subsana silenciosamente.
- Configuración por revisión: un job guarda `model_route_revision`, hash de prompt y precio/capability conocido al crearlo; no cambia a medio proceso.

## Modelo de estado de proveedor
`DISABLED | NOT_CONFIGURED | READY | TEST_FAILED | RATE_LIMITED | BLOCKED_POLICY | UNKNOWN`. Para servicios locales, endpoint `http://127.0.0.1:1234/v1` puede estar permitido solo con política explícita admin; nunca autorizar cualquier host `localhost` proporcionado por usuario remoto. Para externos HTTPS + dominio allowlist; bloquear IP privada, DNS rebinding y redirects externos.

## `.env` vs interfaz
`.env`: `DATABASE_URL`, `APP_MASTER_KEY`, `SESSION_SECRET`, `PUBLIC_BASE_URL`, `MEDIA_STORAGE_ROOT`, `BOOTSTRAP_ADMIN_*` solo durante bootstrap, `ALLOWED_ORIGINS`, `LOG_LEVEL`, `DEFAULT_BUDGET_CEILING=0`, `ENVIRONMENT`. Prohibido que el navegador abra o modifique `.env`; configuración de proveedor en DB; claves de escritura/reemplazo cifradas con una master key externa al DB. Rotación de clave requiere procedimiento y backup.

## Rutas API (especificación REST inicial)
| Método | Ruta | Uso/autorización |
|---|---|---|
| POST | `/api/auth/login` | sesión admin segura |
| GET | `/api/health` | salud, sin secretos |
| GET/POST | `/api/feeds` | listar/registrar fuentes, editor/admin |
| POST | `/api/ingest/url` | URL autorizada -> job/ID |
| GET | `/api/jobs/{id}` | progreso, error sanitizado |
| GET | `/api/stories` | lista filtrada |
| GET | `/api/stories/{id}` | detalle, claims y fuentes |
| POST | `/api/stories/{id}/briefs` | generar propuesta revisable |
| POST | `/api/stories/{id}/scripts` | versión guion |
| POST | `/api/scripts/{revision_id}/approve` | exige hash esperado, editor |
| POST | `/api/scripts/{revision_id}/production-plan` | crear plan/escenas |
| PUT | `/api/plans/{id}/shots/{id}` | edición con concurrencia |
| POST | `/api/plans/{id}/flow-manual-package` | export sin gasto |
| POST | `/api/graphics/{id}/preview` | SVG/video programático local |
| POST | `/api/assets` | adjuntar medio autorizando derechos |
| POST | `/api/assets/{id}/approve` | admin/realizador |
| GET/POST/PATCH | `/api/admin/providers` | admin, sin leer secretos |
| POST | `/api/admin/providers/{id}/test` | test policy/timeout |
| PUT | `/api/admin/providers/{id}/secret` | solo reemplazar |
| GET/PUT | `/api/admin/model-routes` | enrutamiento tarea/modelo |
| GET/PUT | `/api/admin/budgets` | presupuesto, admin |
| POST | `/api/episodes` | lote 5 o 10 |
| GET | `/api/audit` | admin, paginado, filtrado |

## Respuestas y errores
`422` solo por payload inválido con mensaje amigable, `401` sin sesión, `403` acceso insuficiente, `409` conflicto de revisión, `429` límite, `402/403` política de gasto, `503` proveedor no disponible; incluir `request_id`, `error_code` estable y `message_es` sin secretos. Cualquier generación externa retorna `job_id` y estado, nunca un vídeo inexistente.

## API provider adapters
```
ProviderCapabilities = {chat,structured_output,images,video,audio,vision,transcription,pricing_known,allowed_ratios,allowed_durations}
ModelRoute = {task,provider_id,model_id,timeout,max_retries,budget_policy,enabled,revision}
```
Capacidades se verifican en prueba del proveedor y pueden cambiar; si no soporta imagen de referencia, no se prometerá continuidad. OpenAI-compatible NO implica compatibilidad video/structured output de todos los modelos. Integración remota usa conector propio, nunca concatenación directa de URL de usuario en llamada privilegiada.

## Contratos
Ver `02_CONTRATOS/news_story.schema.json`, `production_plan.schema.json`, `graphic_spec.schema.json`, `provider_config.schema.json`, `flow_manual_package.schema.json`. Si OpenAPI generado deriva de Pydantic, mantener una sola fuente de verdad y probar equivalencia. JSON Schema válido NO equivale a veracidad factual.
