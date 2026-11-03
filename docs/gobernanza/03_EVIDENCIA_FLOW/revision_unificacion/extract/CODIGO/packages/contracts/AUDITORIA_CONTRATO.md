# Auditoría del contrato `production_handoff.v1` — Fase 1 (G1)

**Fecha:** 2026-10-28 · **Ámbito:** compatibilidad entre el borrador del contrato y los datos editoriales reales de `apps/api/src/neuralnews`.
**Clasificación:** las afirmaciones marcadas [VERIFICADO] se reprodujeron sobre código y pruebas reales de este repositorio.

## 1. Modelos editoriales localizados

- [VERIFICADO: `apps/api/src/neuralnews/models.py:111-135`] **Noticia:** `Story` (id entero, `topic_key`, `title` no nulo, `summary` **anulable**, `status`, puntuación editorial, fechas).
- [VERIFICADO: `apps/api/src/neuralnews/models.py:52-108,138-149`] **Fuentes:** `Source` (`provider` youtube|spotify|web_rss|manual, `external_id` anulable, `canonical_url` **anulable**, `title` **anulable**, `published_at` anulable, `imported_at` **no nulo** por defecto) y enlace `StorySource` (`relevance` primary|supporting|mention, anulable).
- [VERIFICADO: `apps/api/src/neuralnews/models.py:184-212`] **Guiones y aprobación:** `ScriptVersion` (número de versión, `content`, `language` por defecto `es-ES`, `content_hash` SHA-256 del contenido) y `Approval` (`actor_id`, `approved_at`, `status` ACTIVE|INVALIDATED|REVOKED, ligada a una versión exacta).
- [VERIFICADO: `apps/api/src/neuralnews/services/scripts.py:26-47`] Crear una versión nueva anula la aprobación vigente; `active_approval()` devuelve sólo `ACTIVE` más reciente.
- [VERIFICADO: `apps/api/src/neuralnews/services/sources.py:71-140,215-216,312-333`] Creación de fuentes: con URL siempre queda `canonical_url` normalizada; una fuente **sólo texto** puede quedarse sin URL (`canonical_url=None`, `provider="manual"`). El título se rellena al obtener contenido; si no, puede seguir nulo. `Story.summary` se rellena con `neutral_summary` del borrador de investigación cuando existe.

## 2. Mapa campo a campo (T108)

| Campo del contrato | Procedencia real | Clasificación | Decisión |
|---|---|---|---|
| `schema_version` | Constante del contrato | Existente | `production_handoff.v1` |
| `handoff_id` | Derivado del productor: `hn1-s{story_id}-v{revision}-{hash_payload12}` (single) / `hn1-b{batch_id}-{hash12}` (batch) | Derivable | Determinista: mismo contenido → mismo id (idempotencia); cualquier cambio de contenido → id nuevo. No es el id de `ProductionPackage` (`models.py:261-272`). |
| `created_at` | Momento de emisión | Derivable | UTC con zona horaria. |
| `mode` | Parámetro del productor (`single` / lote de `Batch`) | Existente | Lote sólo con 5 o 10 noticias aprobadas. |
| `output_format` | Parámetro del productor (decisión de producción) | Parámetro | `9:16` por defecto; no es dato editorial. |
| `style_profile` | Parámetro del productor; valores por defecto declarados en `flow-recovery/source/constants.ts` (NeuraldotAI, CRT, Algenib) | Parámetro | Son **identificadores lógicos de referencia**, no assets licenciados (ver RIESGOS.md R05/R07). |
| `story_id` | `Story.id` convertido a cadena | Existente | Sin prefijos: trazabilidad directa a la base editorial. |
| `revision` | `ScriptVersion.version` de la versión aprobada | Existente | Entero ≥ 1. |
| `title` | `Story.title` | Existente | No nulo en el modelo. |
| `summary` | `Story.summary` | Existente pero **anulable** | **Obligatorio en el contrato; el productor bloquea** la emisión si falta o está vacío (no se inventa; el contenido pendiente se corrige en editorial). Ver §4. |
| `language` | `ScriptVersion.language` (por defecto `es-ES`) | Existente | `const es-ES` en v1; ampliable si el editorial produce otros idiomas. |
| `approved_script` | `ScriptVersion.content` de la versión con aprobación `ACTIVE` | Existente | Texto íntegro, sin recortes. |
| `script_version_id` (añadido) | `ScriptVersion.id` | Existente | Trazabilidad exacta de la fila aprobada. |
| `content_hash` (añadido) | `ScriptVersion.content_hash` = SHA-256 del texto | Existente | El consumidor lo recomputa y rechaza cualquier alteración. |
| `sources[].title` | `Source.title` | Anulable | En el borrador era obligatorio; ahora **anulable** para no inventar títulos. |
| `sources[].url` | `Source.canonical_url` | Anulable | En el borrador era obligatorio; ahora **anulable** (fuentes manuales sin enlace). Las URLs no nulas deben ser `http(s)`. |
| `sources[].accessed_at` | `Source.imported_at` | Existente (no nulo) | Fecha en que la fuente entró en el sistema editorial (momento de acceso/registro). Único valor truthful disponible; `Evidence.retrieved_at` queda para evidencias de afirmaciones, que el contrato v1 no transporta. |
| `sources[].provider` (añadido, opcional) | `Source.provider` | Existente | Enum youtube/spotify/web_rss/manual. |
| `sources[].external_id` (añadido, opcional) | `Source.external_id` | Existente | Permite identificar fuentes sin URL. |
| `sources[].relevance` (añadido, opcional) | `StorySource.relevance` | Existente | Enum primary/supporting/mention. |
| `sources[].published_at` (añadido, opcional) | `Source.published_at` | Existente | Anulable. |
| Identificabilidad de fuente | — | Restricción nueva | Cada fuente debe aportar al menos uno de `url` / `external_id` / `title` no vacíos (`anyOf` del esquema); el productor bloquea fuentes sin ningún identificador. |
| `storyboard` (añadido, opcional) | `build_storyboard` (orientativo, ya usado por `services/batches.py`) | Derivable | Opaque en v1 (array); Studio decide su uso. No se exige. |
| `editorial_approval.status` | `Approval.status == "ACTIVE"` | Existente | El contrato sólo acepta `approved`; el productor verifica en base de datos en el momento de emitir (mitiga RIESGOS.md R03). |
| `editorial_approval.approved_by` | `Approval.actor_id` | Existente | |
| `editorial_approval.approved_at` | `Approval.approved_at` | Existente | |
| `approvalStatus` importado por Studio | `flow-recovery/source/components/NewsEditorialTab.tsx:161-180` | Incompatible como prueba de aprobación | El valor del JSON es falsificable; la validez la establece el productor (consulta DB) y el consumidor verifica hash. RIESGOS.md R03. |

## 3. Incompatibilidades resueltas respecto al borrador (T114)

1. **`summary` obligatorio vs columna anulable** → se mantiene obligatorio y el **productor bloquea** (no se rellena con datos ficticios).
2. **`url` obligatorio vs `canonical_url` anulable** → opcional/anulable + `anyOf` de identificabilidad; se añaden `provider`/`external_id`/`relevance`/`published_at` opcionales para no perder trazabilidad (el borrador con `additionalProperties: false` y tres campos la descartaba).
3. **`accessed_at` sin origen** → mapeado a `Source.imported_at`, documentado.
4. **`title` de fuente obligatorio vs columna anulable** → anulable (entra en el `anyOf`).
5. **Falta de verificación de integridad** → añadidos `script_version_id` y `content_hash` obligatorios en la noticia; el consumidor recomputa SHA-256 y rechaza alteraciones.
6. **`$id`/título de borrador** → actualizados a la revisión v1; el historial del borrador queda en el respaldo y en este documento.

## 4. Tratamiento de noticias con información incompleta (T113)

Regla (PLAN_MAESTRO §3.5): ningún dato obligatorio se inventa. El productor emite por noticia o falla **de forma aislada**:

- Sin guion / sin aprobación `ACTIVE` / aprobación de una versión anterior o revocada → **bloquea esa noticia** con mensaje concreto (no emite nada parcial).
- `summary` ausente o vacío → **bloquea esa noticia**; el editorial debe completarla y aprobar de nuevo si procede.
- Fuente sin URL pero con `external_id` o `title` → se emite con `url: null` (caso manual real).
- Fuente sin ningún identificador → **bloquea esa noticia**.
- En modo lote, si alguna noticia bloquea, **no se emite el lote** y se listan todos los problemas juntos (para corregir en una pasada).

El bloqueo de una noticia no detiene otras tareas independientes.

## 5. Restricciones del contrato v1 (T117)

- No transporta afirmaciones/evidencias (`Claim`/`Evidence`) ni puntuación editorial: el consumidor de Studio no las necesita para preproducción y añadir campos sin uso invitaría a suponer semánticas no probadas. Quedan accesibles vía API editorial.
- `language` fijo a `es-ES` (canon actual del noticiario).
- `style_profile` transporta identificadores lógicos; ningún asset ni URL de proveedor cruza la frontera editorial (plan v0.1, regla de frontera).
- La emisión queda registrada: fichero en `storage/handoffs/` y `AuditLog` (`handoff.emitted`) con actor, id y revisión.
- `handoff_id` determinista por contenido: reemitir el mismo snapshot devuelve el fichero ya guardado (idempotencia); editar el guion cambia hash → nuevo id.

## 6. Evidencia de pruebas

Comandos y resultados: ver `ESTADO_PROYECTO.md` y el informe de ejecución; suite completa con `python -m pytest ../../tests -q` desde `apps/api` y `npm test` en `flow-recovery`.
