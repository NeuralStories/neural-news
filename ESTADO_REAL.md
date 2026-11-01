# ESTADO REAL — NN-107 Reintegración de la lógica de Flow (31/10/2026)

**Rama:** `nn-107-reintegracion-flow` · **Commits:** F1 `b7ed981` · F2 `1fe68d3` · F3 `59e45d5` · F4-F5 (este commit)
**Especificación rectora:** `newsV2/01_DOCUMENTACION/NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md`
**Etiquetas:** FUNCIONA (probado con test automático) · PARCIAL (funciona con límites documentados) · PENDIENTE_POR_ACTIVO (falta material del propietario) · PENDIENTE_POR_API (falta integración externa autorizada) · NO_IMPLEMENTADO (fuera de la primera ventana, Etapa B/C).

## Recorrido de producción audiovisual

| Módulo | Estado | Evidencia |
|---|---|---|
| Proyectos de producción con persistencia PostgreSQL/SQLite vía API (CAS 409, revisiones inmutables por paso) | FUNCIONA | `tests/test_projects_studio.py` (11 tests; entrega obligatoria crear→editar→reiniciar→recuperar) |
| Biblioteca de medios: subida idempotente por SHA-256, almacén direccionado por contenido, ffprobe opcional, aprobación humana | FUNCIONA | mismos tests (`test_take_media_upload_is_idempotent_and_never_autoapproved`) |
| Studio Flow de 8 etapas integrado en Next.js **sin iframe**, una sola navegación y una sola redacción | FUNCIONA | E2E `studio-reintegration.spec.ts` (ocho etapas + persistencia tras recargar) |
| Pestaña Noticias conectada al motor editorial (dossier con fuentes y estados de afirmaciones) | FUNCIONA | `tests/test_editorial_graphics.py::test_dossier_shares_the_editorial_newsroom` + panel en UI |
| Director audiovisual determinista (cap. 7): beats continuos sin cortes impuestos, tomas por capacidad del proveedor, reglas DOCUMENTARY/DATA_GRAPHIC/FLOW_MAXDOTAI/GENERATIVE_BROLL con justificación | FUNCIONA | `tests/test_director_package.py` (7 tests, determinismo incluido) |
| Prompts versionados por toma (orden fijo, constraints, checklist, hash) | FUNCIONA | `test_prompt_versions_accumulate_and_take_becomes_prompt_ready` |
| FlowManualPackage.v1 exportable (personaje maxDotAi, referencias mediaId vs PROMPT_ONLY, checklist, avisos) | FUNCIONA | `test_flow_manual_package_requires_prompt_and_carries_full_instructions` + descarga en E2E vertical |
| Importación de MP4 externo asociado a toma y revisión; aprobación/rechazo humano | FUNCIONA | E2E `vertical-production.spec.ts` (recorrido completo con persistencia) |
| Gráficos programáticos: GraphicSpec + SVG determinista con valores exactos y pie de fuente trazable al claim | FUNCIONA (PARCIAL: solo plantilla BAR en primera ventana) | `tests/test_editorial_graphics.py` |
| Invalidación dirigida (cap. 13): cambio del guion → gráficos derivados INVALIDADO + auditoría | FUNCIONA (PARCIAL: regla factual→derivados; las otras 3 reglas en Etapa B) | `test_script_change_invalidates_derived_graphics` |
| Correcciones de auditoría F-01…F-10 (identidad maxDotAi, nada aprobado por defecto, Algenib hipótesis, traspaso no verifica, dedup canónica etiquetada, export ≠ backup BD…) | FUNCIONA | `tests/test_regressions_f01_f10.py` (10 tests de fichero + comportamiento) |
| Runtime de Flow fuera del editor | PARCIAL (por diseño): todo BLOCKED con paquete manual; download nativo; dentro del editor delega en `window.Flow` | adaptador `flow/adapter.ts`; E2E verifica banner BLOCKED |
| Render/montaje FFmpeg local | NO_IMPLEMENTADO (Etapa B) — **el motor FFmpeg del 29/10 no se portó**; solo su modelo de datos (`RenderOutput`) y la cola de jobs están listos. El botón de render no existe: fuera de Flow todo es BLOCKED/importación manual | ausencia verificada en `services/` y en la UI |
| Regresiones heredadas R-BUG-1/2/3/4 | FUNCIONA (corregidas y cubiertas por tests y E2E) | ver TASK_NN-107 |

## PENDIENTE_POR_ACTIVO (dependen del propietario)

- Handle real de maxDotAi en Flow y ficha/hoja maestra: la ficha queda `PENDIENTE_DE_VINCULAR`.
- MP4 real generado en Flow para la toma: la importación está probada con archivo de prueba; con material real el flujo es idéntico.
- Referencias visuales aprobadas (las de ejemplo arrancan `pendiente`).

## PENDIENTE_POR_API

- Generación programática de imágenes/vídeo: requiere integración externa autorizada y comprobada (futuro adaptador con prueba real); fuera del editor todo queda BLOCKED con paquete manual.
- ~~Prueba real contra PostgreSQL~~ → **FUNCIONA sin Docker**: PostgreSQL 16.9 local (binarios nativos sin instalador en `../pglocal/`, servidor en 127.0.0.1:5433, BD `neuralnews`). `tests/test_postgres_projects.py` PASSED (ciclo crear→editar→CAS→MP4→reiniciar→recuperar sobre PG real) y migraciones Alembic `d38b9d62cb47 ↔ d4ce8c95781e` verificadas en PG. Arranque: `../pglocal/pgsql/bin/pg_ctl.exe -D ../pglocal/data -l ../pglocal/logfile.log -o "-p 5433" start`.

## NO_IMPLEMENTADO (Etapa B/C, declarado)

- Animática completa, render FFmpeg real con B-roll/voz, TTS, episodios 5/10 con export compuesto (A11/A12), director LLM completo (el determinista sí funciona), gráficos line/timeline/percentage, publicación en plataformas.

## Pruebas totales al cierre

- API: **114 passed, 0 fallos** (+ `test_postgres_projects.py` PASSED contra PostgreSQL 16.9 local; el único skip queda en el suite por defecto porque la URL de PG se inyecta con `NEURAL_TEST_POSTGRES`, y con ella el test pasa: 1 passed).
- E2E navegador real (Edge): **2 passed** (`studio-reintegration`, `vertical-production`).
- `tsc --noEmit` y `next build` limpios.
