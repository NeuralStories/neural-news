# TASK NN-107 — Reintegración de la lógica de Flow (NeuralStories Studio) en apps/web

**Creada:** 31/10/2026 · **Rev. 3:** 31/10/2026 (veredicto del propietario) · **Actualización F0:** 31/10/2026 — **F0 SUPERADO con autorización del propietario** («puede comenzar»; F1–F5 autorizadas sin nueva aprobación por fase) · **Estado:** `IMPLEMENTADA — PENDIENTE DE REVISIÓN DEL PROPIETARIO (NO APROBADO)`

> **NO APROBADO.** La ejecución F0–F5 está cerrada con evidencia y se entrega como instantánea inmutable para revisión del propietario. Ningún cambio se fusiona a `main` ni se da por definitivo hasta su aprobación explícita. · **Prioridad:** P0 · **Ventana:** CORE (2 sesiones de 10 h)
**Plan rector:** [`01_DOCUMENTACION/16_PLAN_MAESTRO_REINTEGRACION_FLOW.md`](../01_DOCUMENTACION/16_PLAN_MAESTRO_REINTEGRACION_FLOW.md) (rev. 3)
**Especificación rectora:** [`01_DOCUMENTACION/NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md`](../01_DOCUMENTACION/NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md)
**Matriz diferencial:** [`01_DOCUMENTACION/17_MATRIZ_DIFERENCIAL_PRELIMINAR.md`](../01_DOCUMENTACION/17_MATRIZ_DIFERENCIAL_PRELIMINAR.md) · **Decisión:** ADR-FLOW-001 (`12_REGISTRO_DECISIONES_Y_RIESGOS.md`)

## 0. Condición de entrada a F1 — RESUELTA (F0 superado el 31/10/2026)

**F0 ampliado cerrado con evidencia material:** el propietario aportó `REVISION_UNIFICACION_NEURAL_NEWS.zip` (SHA-256 verificado `d710c9f8…1d70c`, 226 entradas, foto 29/10). La auditoría diferencial comparó (a) repo activo `neural-news`, (b) 17 fuentes de Flow y (c) la integración del ZIP: **12 idénticas + 5 modificadas + 0 ausentes (confirmado por hash)**; 5 módulos de API exclusivos del ZIP (`av_generation`, `av_jobs`, `av_render`, `editorial_status`, `handoff` + `api/av.py`), contrato `production_handoff.v1` probado en ambos lados, 7 tests exclusivos y 11 hallazgos reproducibles del `ESTADO_REAL.md` (R-BUG-1 #2 y R-BUG-2 #5 confirmados con causa localizada; nuevos R-BUG-3 verificación inflada y R-BUG-4 duración 8 s/8,8 s). Decisiones cerradas en [`01_DOCUMENTACION/17_MATRIZ_DIFERENCIAL_DEFINITIVA.md`](../01_DOCUMENTACION/17_MATRIZ_DIFERENCIAL_DEFINITIVA.md); ADR-FLOW-001 actualizado + ADR-015 (repo único `neural-news`, el hermano `neuralnews` como fuente de reutilización); backup verificable del repo activo `backups/neural-news-pre-NN107-F0-20261031.zip` (`c08d99b4…77d69d`); manifiesto completo en [`03_EVIDENCIA_FLOW/revision_unificacion/F0_MANIFIESTO_EVIDENCIAS.md`](../03_EVIDENCIA_FLOW/revision_unificacion/F0_MANIFIESTO_EVIDENCIAS.md).

**Nota de portabilidad (para F1):** los módulos av del ZIP requieren los modelos `BatchBudget` y `RenderOutput` (ausentes en el activo) + migración + router `api/av.py`. Los 9 módulos compartidos divergentes mandan en su versión del activo (más nueva); los del ZIP se portan solo en los módulos exclusivos.

## 1. Resumen

Reintegrar el Studio de Flow (17 fuentes, 4.774 líneas) como módulo `/estudio` de `neural-news/apps/web` con: persistencia en PostgreSQL vía API (D2), una sola redacción compartida con las páginas editoriales (D7), adaptador runtime para `flow-sdk` (D3), compilador de prompts determinista, importación de tomas MP4 con hash+ffprobe en almacén direccionado por contenido (§5 del plan), CAS de revisiones, selección de recursos del cap. 7 y corrección de las regresiones R-BUG-1/R-BUG-2. Nada se elimina sin equivalencia acreditada (D6).

> **Estimación:** 20 h (2×10 h) es **presupuesto inicial**, re-estimado al cierre de F0. Las fases se cierran por **gates**, no por horas; el mínimo aceptable de entrega es **F0–F3 completo** (con menos, la tarea se declara PARCIAL).

## 2. Campos de backlog

| Campo | Valor |
|---|---|
| id | NN-107 |
| milestone | A (sprint en curso) |
| priority | P0 |
| area | flow |
| dependencies | F0 (auditoría diferencial + ZIP del 29/10 + decisión de repo único) es puerta de F1 |
| estimate_minutes | 1200 (presupuesto inicial, rev. en F0) |
| status | NOT_STARTED |
| evidence | matriz diferencial definitiva + ADR-FLOW-001/ADR-015 + backup SHA-256 + suites + `ESTADO_REAL.md` |

## 3. Entregables

1. `apps/web/features/studio/**` + `app/estudio/page.tsx` + enlace en `app-shell` (8 pestañas operativas).
2. Backend: migraciones del subconjunto mínimo; `/v1/projects`, `/v1/projects/{id}/studio/{step}` (CAS), `/v1/projects/{id}/takes/{take_id}/media`, `/v1/media` (hash + ffprobe, almacén `storage/media/`).
3. Adaptador `FlowRuntime` (hosted/manual); compilador de prompts determinista (prompt_en + explanation_es + constraints + checklist por toma); FlowManualPackage; importación de toma MP4.
4. Selección de recurso por toma según cap. 7 (tabla determinista USER_VIDEO/FLOW_MAXDOTAI/DOCUMENTARY/DATA_GRAPHIC/GENERATIVE_BROLL/TITLE_CARD/PENDING) con narración continua.
5. Correcciones F-01…F-10 y regresiones R-BUG-1 (noticia importada auto-seleccionada) y R-BUG-2 (ratio estable al crear plan).
6. Pruebas: vitest + Playwright para la matriz única del plan §7 (A1, A3–A8, A13–A16 COBERTO; A2/A9/A10 PARCIAL declarado) + E2E de deep links (iframe→`/estudio`, por noticia/proyecto/revisión).
7. Documentación: matriz diferencial definitiva, ADR-FLOW-001/ADR-015, `ESTADO_REAL.md` con etiquetas FUNCIONA/PARCIAL/PENDIENTE_POR_ACTIVO/PENDIENTE_POR_API/NO_IMPLEMENTADO.

## 4. Checklist operativo (gates en negrita; sesiones de 10 h)

**Sesión 1 — Studio editable y persistente**

- [x] **F0 (2 h) — GATE CERRADO 31/10/2026.** ✅ Hashes 17 fuentes verificados · ✅ auditoría diferencial completada (ZIP `d710c9f8…1d70c` verificado; 12 idénticas + 5 modificadas + 0 ausentes por hash; decisiones cerradas en matriz definitiva) · ✅ ADR-015 (repo único `neural-news`) · ✅ backup ZIP+SHA-256 `c08d99b4…77d69d` (rama por crear al iniciar F1) · ✅ A1–A16 congelados · ✅ portabilidad acotada (BatchBudget + RenderOutput + migración + router av; 9 módulos compartidos divergentes mandan en el activo) · ⏳ re-estimación fina de F1–F5 se congela al arrancar F1 (presupuesto 20 h sin cambios por ahora)
- [x] **F1 — GATE CERRADO 31/10/2026** (rama `nn-107-reintegracion-flow`, commit F1). ✅ Migración `d4ce8c95781e` con subconjunto cap. 13 + `BatchBudget`/`RenderOutput` portados (upgrade/downgrade verificado) · ✅ endpoints `/v1/projects`, `/v1/projects/{id}/studio/{step}` (CAS 409), beats/shots, tomas con aprobación humana, prompts versionados, `/v1/media` idempotente por SHA-256 + ffprobe opcional · ✅ **entrega obligatoria probada: crear → modificar → reiniciar (motor nuevo) → recuperar sin pérdida** · ✅ R-BUG-1 y R-BUG-2 al nivel API · ✅ suite completa 85 passed + 1 skip · ⏳ bloqueo de entorno: prueba real contra PostgreSQL requiere Docker Desktop operativo (`NEURAL_TEST_POSTGRES` deja el test listo; `infra/docker-compose.yml` define el servicio)
- [x] **F2 — GATE CERRADO 31/10/2026** (commit `1fe68d3`). ✅ 17 fuentes portadas a `apps/web/features/studio/` (hash verificado) + ampliaciones fusionadas · ✅ página nativa `/estudio` sin iframe, enlace en app-shell, deep-links `?project=&story=&revision=` · ✅ guardado real vía `/v1/projects` con CAS (hidratación sin eco, 409 → recarga); sin localStorage como fuente de verdad ni almacén paralelo del plan · ✅ adaptador `flow/` fusionado con el shim del ZIP: fuera del editor todo es BLOCKED, download nativo · ✅ F-01 (maxDotAi único, cero NeuralDotAI), F-02/F-03 (nada aprobado por defecto), F-04 (Algenib = hipótesis), F-08 (importar ≠ verificado) · ✅ R-BUG-1/2/3/4 corregidos en UI y API · ✅ `tsc` y `next build` verdes; **E2E `studio-reintegration.spec.ts` 1 passed** (ocho etapas + persistencia tras recargar + ratio intacto + noticia activa)

**Sesión 2 — motor creativo y entrega**

- [x] **F3 — GATE CERRADO 31/10/2026** (commit `59e45d5`). ✅ director determinista (`services/director.py`, cap. 7): beats sin cortes impuestos (F-05) + tomas por capacidad del proveedor, reglas DOCUMENTARY/DATA_GRAPHIC/FLOW_MAXDOTAI/GENERATIVE_BROLL con justificación; `POST /v1/projects/{id}/director/plan` persiste beats/shots · ✅ prompts versionados por toma · ✅ `FlowManualPackage.v1` descargable (personaje maxDotAi, referencias mediaId vs PROMPT_ONLY, checklist, avisos; jamás llama a Flow) · ✅ importación de MP4 externo asociado a toma (hash+ffprobe, IMPORTADA nunca APROBADA) + previsualización + aprobación/rechazo humano · ✅ R-BUG-2 verificado al planificar · ✅ `test_director_package.py` 7/7; **E2E `vertical-production.spec.ts` 1 passed** (recorrido completo con persistencia; ambas E2E verdes; suite API 92 passed + 1 skip)
- [x] **F4+F5 — GATE CERRADO 31/10/2026** (commit `96a5bfd`). ✅ dossier editorial vía `/v1/projects/{id}/dossier` (D7: una sola redacción) · ✅ GraphicSpec + SVG determinista con valores exactos y fuente trazable (solo BAR en primera ventana) · ✅ invalidación dirigida: cambio de guion → gráficos derivados INVALIDADO + audit log · ✅ F-09 (dedup canónica antes que léxica, etiquetada heurística con revisión) y F-10 (export JSON ≠ backup BD) · ✅ regresiones F-01…F-10 consolidadas en `test_regressions_f01_f10.py` (10/10) · ✅ `test_editorial_graphics.py` 5/5 · ✅ E2E studio-reintegration + vertical-production en verde con dossier y gráfico · ✅ `ESTADO_REAL.md` con FUNCIONA/PARCIAL/PENDIENTE_POR_ACTIVO/PENDIENTE_POR_API/NO_IMPLEMENTADO · ✅ **entrega final: `REVISION_NN107_FLOW.zip`** (190 entradas: código trackeado sin secretos, historial git bundle, gobernanza, evidencia de 114 tests + PG real + 2 E2E + migraciones + build + recorrido audiovisual; sha256 `dcf67e2c…beb2`; estado NO APROBADO) · ✅ prueba real contra PostgreSQL SIN Docker: PG 16.9 local (`../pglocal`, puerto 5433) — `test_postgres_projects.py` PASSED y migraciones `d38b9d62cb47 ↔ d4ce8c95781e` verificadas en PG
- [ ] **F5 (3 h) — GATE: matriz de cobertura.** vitest + Playwright de §7 (A1, A3–A8, A13–A16; A14: doble envío→una ejecución + reclaim, distinto de anti-doble-cobro del proveedor) · E2E de transición y deep links · GraphicSpec mínimo (barra SVG, A9 PARCIAL) · invalidación dirigida básica (A2/A10 PARCIAL) · `ESTADO_REAL.md` · informe con hashes de cierre

## 5. Criterios de aceptación

Los del plan rector §8: gates cerrados, 8 pestañas persistentes en PostgreSQL, una sola redacción (D7), cero `flow-sdk`, importación MP4 con hash/ffprobe, matriz §7 en su estado declarado, evidencia intacta, backup registrado, **nada eliminado sin equivalencia acreditada (D6)**.

**Definición de fallo:** gate declarado sin cumplir; hash de evidencia alterado; generación fuera del contexto hosted; estado solo en navegador; criterio sin prueba; eliminación de la implementación anterior antes de acreditar equivalencia; declaración de terminado sin prueba funcional de cada criterio comprometido.

**Fuera de alcance (PENDIENTE_ETAPA_B):** A9/A10 completos, A11, A12, render FFmpeg/Remotion completo (el servicio anterior se conserva y verifica, nunca se presenta como render completo), animática, TTS, API de generación externa, publicación.

## 6. Riesgos operativos

Detalle en plan rector §9. Los dos que condicionan la ejecución: **R-15** (dos builds paralelos del mismo spec e integración anterior no localizada → puerta F0) y **R-16** (pérdida funcional al sustituir → matriz diferencial + pruebas de equivalencia).
