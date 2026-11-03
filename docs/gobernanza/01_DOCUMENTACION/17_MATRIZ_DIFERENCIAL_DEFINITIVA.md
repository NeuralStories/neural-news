# Matriz diferencial DEFINITIVA — NN-107 (F0 superado, rev. definitiva 31/10/2026)

**Estado:** DEFINITIVA — sustituye a la versión preliminar. Auditoría diferencial F0 **superada**; F1 autorizada (autorización del propietario, 31/10/2026).
**Decisión de repo único (ADR-015):** destino `neural-news`; el repo hermano `neuralnews` es fuente de funcionalidades reutilizables, no un segundo producto.
**Objetivo intacto:** una sola aplicación Neural News, las ocho etapas creativas de Flow, persistencia real, dirección audiovisual y sin pérdida de funcionalidades ya desarrolladas.

## A. Evidencia de partida (verificada)

| Hecho | Verificación |
|---|---|
| `REVISION_UNIFICACION_NEURAL_NEWS.zip` (3.166.835 bytes, foto 29/10 22:47) | SHA-256 **d710c9f8ba90fa9bf72b46c055fd596220a913c44de58078c7caa7be79a1d70c** — coincide con el declarado por el propietario. Copia en evidencias: `03_EVIDENCIA_FLOW/revision_unificacion/` (ZIP + extracto de análisis). 226 entradas, integridad correcta |
| Comparación de las 17 fuentes Flow vs Studio integrado en el ZIP | **12 idénticas + 5 modificadas + 0 ausentes — confirmado por hash SHA-256**. Modificadas: `App.tsx`, `TopNavigation.tsx`, `constants.ts`, `utils/scriptAnalyzer.ts`, `data/sourceManifest.ts` |
| Contenido del ZIP | `CODIGO/apps/studio` (app Vite con las 17 fuentes + HandoffImport + ProductionPlanPanel + avProfiles + apiClient + handoffConsumer + productionProject + shim `flow-sdk` + 2 tests), `apps/web/app/estudio/page.tsx` (iframe con deep-link), `apps/api` con 5 módulos extra, `packages/contracts` (production_handoff.v1 + consumidor Python), `fixtures/handoff`, 16 tests, 30 capturas, `ESTADO_REAL.md` con 11 hallazgos reproducibles |
| Repo activo `neural-news` (backup previo creado) | ZIP de seguridad `backups/neural-news-pre-NN107-F0-20261031.zip` — SHA-256 **c08d99b4b0fea383bea0c8b4ee77775e6d19ff0822cd7858bebb39116f77d69d**, 189 ficheros, manifiesto junto al ZIP. Rama de trabajo por crear en F1 |

## B. Las 17 fuentes → decisión definitiva

| Archivo | ¿Idéntico a Flow? | Decisión | Correcciones al portar |
|---|---|---|---|
| 12 idénticos (`types.ts`, `constants.ts` no — ver abajo, `BackupModal`, 8 pestañas, `HelpModal`, `MovementTab`, `NewsEditorialTab`, `ReferencesTab`, `ResultTab`, `ScriptTab`, `VoiceTab`, `newsDeduplication.ts`) | SÍ (hash) | **ADAPTAR** (puerto desde el ZIP, equivalente a Flow) | `'use client'`; estado → API (D2); F-02/F-03/F-08 en las pestañas afectadas |
| `App.tsx` | MODIFICADO | **FUSIONAR** — la versión del ZIP añade modo `?embed=1`, `postMessage` al shell y recepción de handoff | Portar ampliaciones; eliminar lo específico de iframe (D7); aplicar D3 |
| `TopNavigation.tsx` | MODIFICADO (reescrito) | **FUSIONAR** — versión del ZIP (badges/props nuevas) | Adaptar a la página nativa |
| `constants.ts` | MODIFICADO | **ADAPTAR** — ⚠️ el ZIP **sigue usando `NeuralDotAI`** (F-01 NO aplicada) | Portar + F-01 (maxDotAi `PENDIENTE_DE_VINCULAR`) + F-02/F-03 |
| `utils/scriptAnalyzer.ts` | MODIFICADO (solo `import type`) | **ADAPTAR** | + F-05: NarrationBeat/Shot/GeneratedClip parametrizable (corrige hallazgo #4) |
| `data/sourceManifest.ts` | MODIFICADO (metadatos) | **ADAPTAR** | Manifiesto de reintegración |

## C. Integración anterior del ZIP → decisión definitiva (con costes de portabilidad verificados)

| Componente | Decisión | Qué aporta (verificado) | Correcciones/coste de portabilidad |
|---|---|---|---|
| `apps/studio/src/lib/handoffConsumer.ts` | **REUTILIZAR (ADAPTAR)** | Valida contra el mismo JSON Schema del backend (`production_handoff.v1`), recomputa SHA-256 del guion aprobado, rechaza duplicados, nunca eleva aprobaciones; funciona en Node y navegador; test `consumer.test.ts` | Corregir R-BUG-3 (hallazgo #3): alinear su criterio de verificación con `services/editorial_status.py` |
| `apps/studio/src/components/HandoffImport.tsx` | **FUSIONAR** | Flujo de traspaso noticia→Studio | Corregir R-BUG-1 (hallazgo #2): importar debe **activar** la pieza (`App.tsx:73,88,192-204`); consumir vía API (D7), no JSON pegado |
| `apps/studio/src/components/ProductionPlanPanel.tsx` | **FUSIONAR** | Edición del plan y acceso a composición | Corregir R-BUG-2 (hallazgo #5): `ProductionPlanPanel.tsx:48` fuerza `9:16`; el ratio debe venir del `format_profile` del proyecto |
| `apps/studio/src/lib/productionProject.ts` | **REUTILIZAR (ADAPTAR)** | Modelo de plan por escena (T405-T411): escenas editables, biblioteca de prompts, encuadres/transiciones, versiones, verificación de consistencia; tests `productionProject.test.ts` | Alinear con NarrationBeat/Shot (F-05); duración por proveedor, no 8 s rígidos; versionado + CAS (§6 del plan) |
| `apps/studio/src/data/avProfiles.ts` | **REUTILIZAR (ADAPTAR)** | Perfiles audiovisuales versionados con procedencia y `assetsLicensed: false` (T400-T404) | Identidad sigue `NeuralDotAI` → F-01; pasar a `CharacterProfile` del cap. 13 con estado PENDIENTE |
| `apps/studio/src/flow-sdk/` (shim local) | **FUSIONAR con el adaptador D3** | Mismo espíritu que `FlowManualAdapter`: generación rechazada con mensaje claro + `Flow.download` nativo del navegador | Fusionar en `features/studio/flow/`; añadir sonda hosted; unificar tipos con la interfaz `FlowRuntime` |
| `services/handoff.py` (API) | **REUTILIZAR** | Productor del handoff verificado en DB | Compatible con modelos activos (importa Claim/Evidence/ScriptVersion/Source/Story) |
| `services/editorial_status.py` (API) | **REUTILIZAR** | `build_story_status`: única fuente de estados editoriales (D7) | Ningún cambio known |
| `services/av_jobs.py` + `providers/av_generation.py` + `api/av.py` | **REUTILIZAR (ADAPTAR)** | Pipeline audiovisual: encolado de composición, generación av | ⚠️ Requiere `BatchBudget` y `RenderOutput` (modelos presentes en el ZIP, **ausentes en el repo activo**) → 2 modelos + migración + registrar router `av.py` (F1) |
| `services/av_render.py` | **REUTILIZAR (honesto)** | Base FFmpeg local: color, rótulos, tono seno, hasta 30 s (hallazgo #9) | Etiquetar **SIMULACIÓN/PARCIAL**: no monta imágenes reales, B-roll ni voz (cap. 11); requiere `RenderOutput` |
| `packages/contracts` + `fixtures/handoff` + `test_handoff_contract.py` | **REUTILIZAR** | Contrato compartido backend↔Studio ya probado en ambos lados | Ninguno |
| 7 tests solo-ZIP (`av_generation`, `av_render`, `batch_budget`, `batches_av`, `editorial_status`, `handoff_contract`, `pilot_e2e`) | **REUTILIZAR (ADAPTAR)** | Cobertura de la funcionalidad recuperada | Los 8 tests compartidos del activo mandan si divergen (activo más nuevo) |
| `apps/web/app/estudio/page.tsx` (iframe) | **SUSTITUIR** con equivalencia | Deep-link `?story=&revision=` y `postMessage` | Portar el deep-link a la página nativa `/estudio` (D7); probar la transición; eliminar el iframe solo cuando `/estudio` nativo pase el E2E de enlaces |
| `apps/studio` como app Vite (doble navegación, hallazgo #1) | **SUSTITUIR** | — | Los 12 archivos idénticos ya se re-portan a `features/studio/`; nada se pierde; se elimina tras acreditar equivalencia (D6) |

## D. Hallazgos del ESTADO_REAL del ZIP (29/10) → registro

| # | Hallazgo | Tratamiento |
|---|---|---|
| 1 | Dos aplicaciones (iframe + segunda navegación) | Resuelto por D7 + SUSTITUIR iframe |
| 2 | Traspaso importado ≠ pieza activa | **R-BUG-1** (F2, corrección localizada) |
| 3 | Studio infla «verificadas con fuentes» respecto a la DB | **R-BUG-3 (nuevo)**: F2/F4 — alinear `handoffConsumer` y `NewsEditorialTab` con `editorial_status.py` |
| 4 | Tomas etiquetadas 8 s pero calculadas 8,8 s; FFmpeg admite 30 s | **R-BUG-4 (nuevo)**: F3 con F-05 — duración por proveedor y validador |
| 5 | `ProductionPlanPanel` fuerza 9:16 | **R-BUG-2** (F3, corrección localizada) |
| 6 | Referencias canónicas sin activos transferibles (0 `mediaId` real) | Cubierto por F-02/F-07 (F3) |
| 7 | Guion demo de estilo genérico | Cubierto por D4/cap. 20 (etiquetado honesto) |
| 8 | Storyboard repetitivo sin B-roll con procedencia | Cubierto por dirección creativa cap. 7 (F3, PARCIAL) |
| 9 | Montaje FFmpeg = simulación técnica | Nota honesta: `av_render.py` se conserva etiquetado PARCIAL/SIMULACIÓN |
| 10 | Estados de proveedor contradictorios (Studio ofrece render Flow 12 créditos con stub) | F3: estados BLOCKED visibles y coherentes con `/v1/provider-status` |
| 11 | Fuentes sin paginación visible (50 recibidos) | Mejora menor → backlog, no bloquea F0–F5 |

## E. Divergencia de módulos compartidos (17/26 idénticos)

Difieren en el activo (más nuevo, con storyboard/reintento seguro/análisis de vídeo de los commits del 31/10): `config.py`, `models.py`, `states.py`, `worker_tasks.py`, `services/{batches,dedupe,research,scripts,sources}.py`. **Regla:** el activo manda; la funcionalidad del ZIP se porta en módulos nuevos (los 5 exclusivos) sin revertir la evolución del activo. Conflictos que surjan al portar se documentan antes de decidir (instrucción del propietario).

## F. Gate F0 — resultado

1. ✅ ZIP obtenido, hash verificado, copia en evidencias, análisis extraído (sin tocar el repo activo).
2. ✅ Comparación 12/5/0 confirmada por hash.
3. ✅ Auditoría diferencial de los tres árboles (Flow / ZIP / activo) con costes de portabilidad concretos (BatchBudget + RenderOutput + migración + router av).
4. ✅ Funcionalidades útiles identificadas (Bloque C) y duplicaciones/incompatibilidades marcadas (shim→adaptador, iframe→página nativa, segunda redacción→D7).
5. ✅ Backup verificable del repo activo creado (A) — previo a cualquier cambio estructural de F1.
6. ✅ Hallazgos heredados registrados (D) y ADR-FLOW-001 actualizado + ADR-015 (repo único).
