# Plan Maestro de Reintegración de la Lógica de Flow — neural.news

**Fecha:** 31/10/2026 (rev. 3 — incorpora el veredicto del propietario; **F0 SUPERADO** el 31/10/2026 con evidencias registradas)
**Mandato:** Reintegrar **toda** la lógica de Flow eliminada (NeuralStories Studio, 17 fuentes TSX/TS verificadas) en `neural-news/apps/web`, sin pérdida funcional y sin duplicar Neural News.
**Especificación rectora:** [`NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md`](NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md) (20 capítulos). **Matriz diferencial:** [`17_MATRIZ_DIFERENCIAL_DEFINITIVA.md`](17_MATRIZ_DIFERENCIAL_DEFINITIVA.md). **Decisión:** ADR-FLOW-001 + ADR-015 en `12_REGISTRO_DECISIONES_Y_RIESGOS.md`. **Tarea:** NN-107. **Evidencias F0:** [`03_EVIDENCIA_FLOW/revision_unificacion/F0_MANIFIESTO_EVIDENCIAS.md`](../03_EVIDENCIA_FLOW/revision_unificacion/F0_MANIFIESTO_EVIDENCIAS.md).

---

## 0. Condiciones del veredicto del 31/10 y dónde se resuelven

El veredicto condiciona la ejecución a doce correcciones. Cada una queda incorporada:

| # | Condición del propietario | Resolución en este plan |
|---|---|---|
| C1 | Auditoría diferencial antes de inventariar/implementar | **RESUELTA — F0 superado el 31/10:** ZIP recibido y verificado por SHA-256 (`d710c9f8…1d70c`), 12 idénticas + 5 modificadas confirmadas por hash, matriz definitiva en doc 17, backup del repo activo creado y ADRs actualizados |
| C2 | Primera sesión F0–F3 suma 14 h, no 10 h | Sesiones redefinidas **10 h + 10 h** (§4); condición de éxito del cap. 19 cierra con F3 en la sesión 2 |
| C3 | Mínimo de contingencia (F0–F2 + adaptador) no cumple la condición de éxito | Mínimo aceptable redefinido: **F0–F3 completo** (compilador de prompts + exportación manual + importación de toma + persistencia) |
| C4 | Estimación 20 h es presupuesto, no compromiso | Punto de **re-estimación obligatorio** al cierre de F0 (§4, paso 6 del protocolo); las fases se cierran por **gates**, no por horas (C9) |
| C5 | Falta definir importación y almacenamiento persistente de MP4 | §5: endpoint de subida, almacén direccionado por hash, ffprobe, metadatos y relación con la toma |
| C6 | Las 8 pestañas pueden reproducir una segunda redacción | D7: Noticias y Studio consumen **las mismas entidades editoriales y estados de aprobación** vía `/v1/stories`; sin estado editorial cliente (§3) |
| C7 | Concurrencia de revisiones insuficientemente definida | §6: versiones, control de conflictos (CAS), trazabilidad y rechazo de guardados obsoletos |
| C8 | El paso de iframe a componentes puede romper enlaces | §7 (regla de enlaces): `/estudio` accesible por noticia, proyecto y revisión; E2E de la transición; iframe anterior solo SUSTITUIR con equivalencia probada |
| C9 | A14 debe probar idempotencia real, no prevenirla | §7, fila A14: doble envío con misma clave → **una sola ejecución**; reclaim tras caída de worker; distinta de la política anti-doble-cobro del proveedor |
| C10 | A9 figura parcial y pendiente a la vez | §7: **una sola matriz** de cobertura con un único estado por criterio (COBERTO / PARCIAL / PENDIENTE_ETAPA_B) |
| C11 | Margen para integración y regresiones | §4: gates obligatorios, F5 intocable como buffer, recorte de alcance antes que recorte de pruebas |
| C12 | Dirección creativa no puede limitarse a prompts de maxDotAi | §7 (dirección creativa): tabla de decisión de recursos del cap. 7 (USER_VIDEO, FLOW_MAXDOTAI, DOCUMENTARY, DATA_GRAPHIC, GENERATIVE_BROLL, TITLE_CARD, PENDING) con cobertura real declarada |
| — | No eliminar la implementación anterior sin equivalencia acreditada (instrucción 8) | D6 + matriz Bloque C + copia de seguridad verificable en F0 |

La auditoría de la especificación funcional (rev. 2, veredicto «ADOPTABLE») se mantiene: los 8 pasos coinciden con las fuentes recuperadas y F-01…F-10 quedan cubiertos por sus capítulos 0, 2, 3, 6, 8 y pruebas A1–A16.

## 1. Decisiones fijas (ADR-FLOW-001, rev. 3)

- **D1 — Evidencia inmutable.** `03_EVIDENCIA_FLOW/` y `flow-recovery/` nunca se editan; hashes del manifiesto verificados en F0 y al cierre.
- **D2 — Persistencia servidor-side.** El Studio guarda en PostgreSQL vía API; `localStorage` solo borrador automático. Los proyectos no viven únicamente en el navegador (cap. 1, 6 y 8 de la spec).
- **D3 — Un solo punto de contacto con el runtime de Flow.** `flow-sdk` eliminado del código integrado; adaptador local `features/studio/flow/` (`FlowHostedAdapter` delega en `window.Flow` dentro del editor; `FlowManualAdapter`: descarga nativa vía Blob, generación → `BLOCKED` con paquete manual).
- **D4 — Regresión obligatoria.** F-01…F-10 y A1…A16 con la cobertura declarada en §7; sin funcionalidad etiquetada FUNCIONA sin prueba (cap. 20).
- **D5 — Sin credenciales, sin API externa.** Generación no alojada → `BLOCKED` + FlowManualPackage; estados reales `FUNCIONA | PARCIAL | PENDIENTE_POR_ACTIVO | PENDIENTE_POR_API | NO_IMPLEMENTADO`.
- **D6 — Nada se elimina sin equivalencia acreditada.** Copia de seguridad verificable (ZIP + SHA-256) y rama antes de cambios estructurales; implementación anterior eliminada solo tras pruebas funcionales de las funcionalidades migradas (C8/C12 del veredicto).
- **D7 — Una sola redacción.** Las páginas editoriales existentes y el Studio comparten `/v1/stories`, estados CAPTURADA→…→GUION_APROBADO y el mismo control de aprobación; el Studio no mantiene un almacén editorial propio (C6).
- **D8 — Medios en almacén direccionado por contenido.** Archivos en `storage/media/` (nunca base64 en filas, nunca en git); en DB solo metadatos y hash (cap. 2 de la spec; detalle §5).
- **D9 — Presupuesto con gates.** Las 20 h son presupuesto inicial; el cierre de F0 re-estima; ninguna fase se declara cerrada por cumplir horas (C4/C9/C11 del veredicto).

**Superficie del adaptador** (4 puntos de contacto de `Flow.*` en las 17 fuentes: `media.select` ×3, `generate.image` ×1, `generate.video` ×2, `download` ×2): interfaz `FlowRuntime { media.select; generate.image; generate.video; download }`, con `detectFlowHost()` y errores tipados `FlowUnavailableError` que la UI existente muestra en su barra de errores.

## 2. Inventario de las 17 fuentes (destino `apps/web/features/studio/`)

Sin cambios respecto a rev. 2 (tabla completa en el historial del documento y matriz del doc 17, Bloque B): `App.tsx` 855 · `types.ts` 190 · `constants.ts` 380 · `utils/scriptAnalyzer.ts` 226 · `utils/newsDeduplication.ts` 155 · `data/sourceManifest.ts` 82 · componentes 8 pestañas + TopNavigation + HelpModal + BackupModal 2.906. Total 4.774 líneas. Nuevos desde cero: `app/estudio/page.tsx` y enlace en `app-shell`. **Salvo decisión contraria de la auditoría diferencial F0**, que puede cambiar ADAPTAR por FUSIONAR/REUTILIZAR para los 5 archivos modificados y los componentes de traspaso (doc 17, Bloques C–D).

## 3. Arquitectura unificada (una sola fuente de verdad)

```
apps/web (Next.js)                    apps/api (FastAPI)                      PostgreSQL
├─ /noticias, /lotes, /configuracion  /v1/stories  (ÚNICA fuente editorial)    Story / Claim / Evidence
├─ /estudio ──► features/studio/      /v1/projects (CRUD, estados cap. 13)    ProductionProject
│    8 pestañas ── leen/escriben ──►  /v1/projects/{id}/studio/{step}         NarrationBeat / Shot
│    (sin redacción propia)           /v1/projects/{id}/prompts               CharacterProfile / VoiceProfile
│    flow/ (adaptador runtime)        /v1/projects/{id}/takes/{id}/media      SetProfile / MediaAsset
│    handoff: solo consulta API       /v1/media + validaciones hash/ffprobe   PromptPackage / GraphicSpec
└─ app-shell (+ «Estudio»)            /v1/jobs (leases + idempotencia)        GeneratedTake / Render…
                                      validaciones deterministas + presupuesto + auditoría
```

Reglas de unicidad: (1) todo dato editorial que muestre el Studio proviene de la API; (2) toda aprobación es una `Approval` de la misma DB; (3) el traspaso de la integración anterior (si el ZIP lo aporta) se convierte en llamadas a estos endpoints, no en un segundo almacén (D7, C6).

## 4. Fases y planificación corregida (C2/C3/C4/C11)

**Sesión 1 — 10 h (Studio editable y persistente)**

| Fase | Contenido | Gate de cierre (obligatorio) | Est. |
|---|---|---:|---:|
| **F0 ampliado** ✅ SUPERADO | Hashes 17 fuentes; **auditoría diferencial** (doc 17: ZIP verificado `d710c9f8…1d70c`, 12/5 confirmado por hash, 5 módulos API exclusivos + contrato handoff + 7 tests identificados); backup verificable del repo activo (`c08d99b4…77d69d`); ADR-FLOW-001 actualizado + ADR-015 (repo único `neural-news`); hallazgos heredados registrados (R-BUG-1…4); criterios A1–A16 congelados | **CERRADO 31/10** — matriz definitiva + backup + manifiesto en `03_EVIDENCIA_FLOW/revision_unificacion/` | 2 h |
| **F1** | Migraciones del subconjunto mínimo; endpoints `/v1/projects`, `/v1/projects/{id}/studio/{step}`, `/v1/media` (§5); estados del cap. 13; **CAS de revisiones** (§6) | CRUD de proyecto persiste tras reinicio; 409 en guardado obsoleto | 3,5 h |
| **F2** | 8 pestañas con guardado en API; F-01 (maxDotAi PENDIENTE_DE_VINCULAR); F-08; F-02/F-03; F-04; **R-BUG-1 (noticia importada auto-seleccionada)**; deep links §7 | A1: 8 pestañas editan, validan y persisten; build y `tsc` verdes | 4,5 h |

**Sesión 2 — 10 h (motor creativo y entrega)**

| Fase | Contenido | Gate de cierre | Est. |
|---|---|---:|---:|
| **F3** | Adaptador runtime (4 puntos de contacto); compilador de prompts determinista (cap. 9); NarrationBeat/Shot/GeneratedClip (F-05); mediaId vs descriptor (F-07); FlowManualPackage; **importación de toma MP4 vía §5**; **selección de recurso del cap. 7** (tabla de decisión por toma); **R-BUG-2 (ratio estable al crear plan)** | Condición de éxito cap. 19: crear/abrir proyecto, 8 pasos, paquete de prompts coherente, exportar instrucciones, importar toma, **todo persiste al reiniciar** | 4 h |
| **F4** | Conexión editorial mínima por `/v1/stories` (D7): alta manual/URL, estados editoriales, vínculo story↔proyecto, deduplicación canónica/GUID/hash (F-09), referencia textual = PROMPT_ONLY | A3, A4 en verde; ninguna entidad editorial duplicada | 3 h |
| **F5** | Suites vitest + Playwright de la matriz §7 (A1, A3–A8, A13–A16); E2E de transición iframe→`/estudio` (enlaces por noticia/proyecto/revisión); GraphicSpec mínimo (barra SVG con datos exactos); invalidación dirigida básica; `ESTADO_REAL.md` | Matriz de cobertura completa; informe con etiquetas del cap. 20 | 3 h |

**Reglas de planificación (C4/C11):** las fases se cierran por su gate, no por cumplir horas. Si una fase desborda, se recorta alcance decorativo, nunca los gates ni F5. El **mínimo aceptable de entrega es F0–F3** (incluye compilador, exportación manual e importación de toma): con menos, NN-107 no cumple la condición de éxito y se declara PARCIAL en `ESTADO_REAL.md`. La re-estimación de F0 puede mover las horas (presupuesto, no compromiso); cualquier cambio >±20 % se registra en la tarea.

## 5. Importación y almacenamiento persistente de medios (C5, D8)

- **Endpoint:** `POST /v1/projects/{id}/takes/{take_id}/media` (multipart; también `POST /v1/media` para la biblioteca). Idempotente por hash: si el SHA-256 ya existe, se reutiliza el `MediaAsset`.
- **Validaciones:** tipo MIME y tamaño máximos; códec reproducible; **ffprobe** para duración, resolución, FPS, orientación y presencia de audio (metadatos reproducibles del cap. 10).
- **Almacén:** `storage/media/{sha256[0:2]}/{sha256}{ext}` direccionado por contenido, fuera del web root y fuera de git (R-14); en PostgreSQL solo metadatos.
- **Estado:** `MediaAsset` con `provenance = imported_flow_manual`, derechos declarados pendientes de aprobación; `GeneratedTake.imported_media_id` y estado de la toma `IMPORTADA` (nunca `APROBADA` automáticamente); comparación con lo planificado (prompt, versión, referencias) antes de la aprobación humana (cap. 6.8 y 10 de la spec).
- **Prior art verificado (Bloque D del doc 17):** el repo hermano `neuralnews` ya implementó biblioteca de medios con ffprobe real y importación Flow con confirmación de derechos (NN-063/064); si la auditoría F0 decide portarlo, se marca REUTILIZAR con su prueba correspondiente.

## 6. Concurrencia, revisiones y trazabilidad (C7)

- Toda escritura del Studio (`PUT /v1/projects/{id}/studio/{step}`, guion, prompts) exige la revisión esperada (`expected_revision` o `If-Match`): conflicto → **409** con la revisión vigente (patrón CAS ya probado en el backlog NN-010 y en el repo hermano).
- Las revisiones aprobadas son inmutables: editar crea revisión nueva conservando origen (`input_hash`, autor, fecha) — cap. 13 de la spec.
- Rechazo explícito de guardados obsoletos: el cliente recibe 409, refresca y re-aplica; ninguna escritura silenciosa sobrescribe aprobaciones.
- Trazabilidad: cada cambio deja registro de qué revisión padre lo originó (cap. 13) y alimenta la invalidación dirigida (4 reglas, nunca regeneración total).

## 7. Matriz única de cobertura (C8/C9/C10/C12) — un solo estado por criterio

Estados: **COBERTO** (fase que lo garantiza) · **PARCIAL** (qué falta) · **PENDIENTE_ETAPA_B**.

| Criterio | Estado | Cobertura |
|---|---|---|
| A1 persistencia de las 8 pestañas | COBERTO | F2/F5 (E2E recarga + API) |
| A2 cambios propagan a prompts/planes dependientes | PARCIAL | F3/F5: invalidación dirigida (4 reglas del cap. 13); grafo completo en Etapa B |
| A3 importada no aparece aprobada | COBERTO | F2 (F-08) |
| A4 afirmación ↔ evidencia | COBERTO | F4 |
| A5 texto reconstruible sin corte 8 s | COBERTO | F3 (F-05) |
| A6 textual ≠ adjunto; mediaId no inventado | COBERTO | F3 (F-07) |
| A7 solo maxDotAi, sin NeuralDotAI | COBERTO | F2 (F-01) |
| A8 export/import manual sin Flow | COBERTO | F3 (F-06 + §5) |
| A9 gráficas con datos exactos | PARCIAL | F5: barra SVG desde claims; line/timeline/percentage + invalidación completa en Etapa B (único estado, sin contradicción) |
| A10 invalidación por cambio de cifra | PARCIAL | F5: regla factual→gráfico/rótulos/guion; resto Etapa B |
| A11 vídeos propios sin diálogos ajenos | PENDIENTE_ETAPA_B | Requiere biblioteca catalogada (prior art NN-063/064) |
| A12 programa 5/10 noticias | PENDIENTE_ETAPA_B | Cap. 12 de la spec, Etapa B |
| A13 configuración de endpoint segura | COBERTO | F5 (verificación de lo existente: provider-status, budget) |
| A14 reanudación sin duplicar trabajo | COBERTO | F5: prueba real — misma clave de idempotencia → una sola ejecución; reclaim de lease tras caída de worker; **distinta** de la política anti-doble-cobro del proveedor, que se documenta y no se asume |
| A15 render falla con mensaje claro | COBERTO | F5: mensaje BLOCKED por medios/audio/aprobación ausente |
| A16 tests automatizados reales | COBERTO | F5 (vitest + Playwright) |
| R-BUG-1 noticia importada auto-seleccionada | COBERTO | F2 (matriz doc 17, Bloque D) |
| R-BUG-2 ratio estable al crear plan | COBERTO | F3 (matriz doc 17, Bloque D) |
| **Dirección creativa (cap. 7)** | PARCIAL | F3: tabla de decisión determinista por toma (¿evidencia auténtica? → DOCUMENTARY; ¿cifra exacta? → DATA_GRAPHIC; ¿habla el presentador? → clip válido o FLOW_MAXDOTAI; ¿abstracto? → GENERATIVE_BROLL etiquetado; ¿texto exacto? → TITLE_CARD; falta material → PENDING) + narración continua sobre pista de audio única; el director LLM completo queda en Etapa B. La cobertura real de esta lógica en la primera ventana queda así declarada, no sobreentendida |
| Enlaces iframe→`/estudio` | COBERTO | §4 F5: deep links `/estudio?proyecto=&story=&revision=&paso=`; E2E desde `/noticias/[id]` → Studio con historia preseleccionada |

F-01…F-10 mantienen su tabla de correcciones de la rev. 2 (equivalencias con la especificación en §0 de la rev. 2 y en la auditoría del 31/10).

## 8. Definition of DONE de NN-107

1. Gates de F0–F5 cerrados con su criterio de salida; build y `tsc` verdes; migraciones aplicables.
2. `/estudio` navegable: 8 pestañas que **persisten en PostgreSQL** y sobreviven al reinicio (A1); misma redacción que `/noticias` (D7).
3. Cero `flow-sdk`; adaptador operativo; compilador de prompts y FlowManualPackage sin conectividad Flow; importación de MP4 vía §5 con hash y ffprobe.
4. Matriz §7 en el estado declarado; suites vitest + Playwright en verde; `ESTADO_REAL.md` con etiquetas del cap. 20.
5. Evidencia: hashes de partida y cierre intactos (D1); backup verificable registrado (D6); matriz diferencial definitiva y ADRs en el registro.

**Definición de fallo:** gate sin cumplir declarado como cumplido; hash de evidencia alterado; llamada de generación fuera del contexto hosted; estado solo en navegador; regresión o criterio sin prueba; implementación anterior eliminada sin equivalencia acreditada (D6).

## 9. Riesgos (además de R-01…R-16 del registro)

R1 monolito `App.tsx` · R2 `flow-sdk` no instalable (adaptador) · R3 React 19/Next 15 (`"use client"`, `ssr:false`) · R4 iconos Material Symbols · R5 solapamiento editorial (resuelto por D7) · R6 recorte de alcance (mínimo F0–F3, C3) · **R-15 mitigado: ZIP recibido y verificado, ADR-015 fija repo único `neural-news`** · **R-16 activo con mitigaciones verificadas: matriz definitiva + equivalencia antes de eliminar (D6)** · R7 invalidación mal acotada (solo 4 reglas) · R8 subconjunto de entidades congelado antes de migrar.

## 10. Fuera de alcance de la primera ventana

Credenciales o login de Flow; API de generación externa (adaptador futuro con prueba real, cap. 9); render FFmpeg/Remotion completo (cap. 11 — el servicio anterior se conserva y verifica, nunca se presenta como render completo); animática completa; A11/A12; publicación; binarios del proyecto remoto de Flow; activo visual de maxDotAi (PENDIENTE_POR_ACTIVO); TTS real.

## 11. Trazabilidad

- Tarea: **NN-107** en `06_TASKS/BACKLOG.{csv,json}`; desglose en `06_TASKS/TASK_NN-107_REINTEGRACION_FLOW.md` (rev. 3).
- Jerarquía: especificación rectora → este plan → matriz diferencial (doc 17) → tareas NN. La entrega única previa es material de contexto.
- Origen: capítulos 6, 7, 8, 9, 13, 18, 19 y 20 de la especificación; auditoría `02_AUDITORIA_FLOW.md`; veredicto del propietario del 31/10 (condiciones C1–C12, §0); ADR-FLOW-001 en `12_REGISTRO_DECISIONES_Y_RIESGOS.md`.
