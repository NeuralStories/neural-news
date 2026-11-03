# Matriz diferencial preliminar — NN-107 (entregable F0, rev. 3)

> **SUPERADA.** Este documento fue la versión preliminar emitida antes de disponer del ZIP. La **matriz definitiva** está en [`17_MATRIZ_DIFERENCIAL_DEFINITIVA.md`](17_MATRIZ_DIFERENCIAL_DEFINITIVA.md) (F0 superado el 31/10/2026: ZIP verificado por SHA-256, 12 idénticas + 5 modificadas confirmadas por hash, decisiones cerradas). Se conserva solo como registro histórico del protocolo.

**Fecha:** 31/10/2026 · **Estado:** PRELIMINAR (histórico)
**Objetivo:** una sola aplicación, una sola fuente de verdad y ninguna pérdida de funcionalidad útil. Decisiones válidas: **REUTILIZAR · ADAPTAR · FUSIONAR · SUSTITUIR · PENDIENTE**.

## Bloque A — Verificación de acceso a las fuentes (hechos del 31/10/2026, verificados en el workspace)

| Fuente | Estado verificado | Consecuencia |
|---|---|---|
| `REVISION_UNIFICACION_NEURAL_NEWS.zip` (fotografía 29/10) | **NO localizado.** Búsqueda en `NeuralStories/`, `Documents`, `Downloads`, `Desktop` y dentro de todos los `.zip/.rar` del workspace; cero referencias en toda la documentación | Las afirmaciones sobre su contenido (12/17 idénticos, 6 componentes, 2 bugs) quedan **PENDIENTE_VERIFICACIÓN**. Acción del propietario: aportar el ZIP o confirmar que no existe |
| Repo activo `neural-news` | Solo `apps/{api,web,worker}`. **No existen** `apps/studio`, `apps/web/app/estudio/page.tsx`, `HandoffImport`, `handoffConsumer`, `ProductionPlanPanel`, `productionProject`, `avProfiles` ni `services/av_render.py` (búsqueda con 0 resultados) | No hay integración anterior que conservar en el árbol activo; el riesgo R-16 se materializa solo si el ZIP aporta código distinto |
| 17 fuentes de Flow (`03_EVIDENCIA_FLOW/source/`) | Presentes, 4.774 líneas, hashes verificables contra `reports/manifest.json` | Base del puerto (decisión ADAPTAR, ver Bloque B) |
| Repo hermano `neuralnews` (git, 8 commits 31/10) | Existe y es un **segundo build del mismo spec** (arquitectura distinta: UI «noticia → producción» con pestañas; sin `apps/studio`). Contiene artefactos reales verificados en su log: biblioteca de medios con ffprobe (NN-064), ZIP Flow con manifiesto SHA-256 (NN-062), importación Flow con confirmación de derechos (NN-063), zonas seguras (NN-055), presets de cámara y límites de glitch (NN-052), gráficos line/timeline/percentage (NN-054), model_routes (NN-019), CAS 409 en guion, feeds+SSRF (NN-024…027), scheduler (NN-028), briefs versionados (NN-033/035/036/040) | **Riesgo R-15 materializado: dos builds paralelos del mismo spec.** F0 debe decidir el repo único de destino (o qué módulos se portan) antes de que NN-107 escriba una tercera línea de código |

## Bloque B — Matriz de las 17 fuentes de Flow (verificadas; decisión de la rev. 2 se mantiene)

| Grupo (líneas) | Decisión | Destino | Nota |
|---|---|---|---|
| `App.tsx` (855) | ADAPTAR | `features/studio/App.tsx` | Adaptador D3; `'use client'`; estado → API |
| `types.ts` (190) · `constants.ts` (380) | ADAPTAR | idem | + estados cap. 13; F-01/F-02/F-03 |
| `utils/scriptAnalyzer.ts` (226) · `utils/newsDeduplication.ts` (155) | ADAPTAR | `features/studio/utils/` | F-05 (NarrationBeat/Shot/GeneratedClip); F-09 + cap. 3 |
| `data/sourceManifest.ts` (82) | ADAPTAR | idem | manifiesto de reintegración |
| 8 pestañas + TopNavigation + 2 modales (2.906 líneas) | ADAPTAR | `features/studio/components/` | correcciones F-01…F-10 y cap. 6 |
| Evidencia original (`03_EVIDENCIA_FLOW/`, `flow-recovery/`) | **REUTILIZAR (inmutable)** | — | D1: sin modificar, hashes intactos al cierre |

## Bloque C — Matriz de la integración anterior (según revisión del propietario; componentes no verificables en el workspace)

Todas las filas quedan **PENDIENTE_VERIFICACIÓN** hasta que F0 acceda al ZIP o el propietario confirme su contenido. La «decisión recomendada» del propietario se recoge como punto de partida, no como decisión cerrada.

| Componente (según ZIP 29/10) | Decisión preliminar | Qué debe verificar F0 para cerrarla |
|---|---|---|
| `HandoffImport.tsx` | FUSIONAR → PENDIENTE | Si su traspaso editorial duplica datos que la API ya sirve (`/v1/stories`), se sustituye por datos compartidos conservando sus validaciones; si aporta validaciones ausentes (esquema, versión, identidad de la noticia), se ADAPTA |
| `handoffConsumer.ts` | FUSIONAR → PENDIENTE | Extraer reglas de comprobación de esquema/versión/identidad y migrarlas al cliente unificado; el resto, SUSTITUIR |
| `ProductionPlanPanel.tsx` | FUSIONAR → PENDIENTE | Migrar edición del plan y acceso a composición al Studio unificado; descartar solo la parte que reproduce `ResultTab` |
| `productionProject.ts` | REUTILIZAR → PENDIENTE | Comparar sus modelos de tomas/planes con el subconjunto mínimo del cap. 13; reutilizar tipos compatibles, no duplicar |
| `avProfiles.ts` | REUTILIZAR → PENDIENTE | Migrar como perfiles (personaje/plató/voz) **pendientes de aprobación** (F-02: nada aprobado por defecto) |
| `services/av_render.py` | REUTILIZAR → PENDIENTE | Conservar y verificar como base FFmpeg; etiquetar PARCIAL/NO_IMPLEMENTADO, nunca «render completo» (cap. 11 de la spec) |
| `apps/studio/src/studio/` (8 pestañas) + `apps/web/app/estudio/page.tsx` (iframe) | SUSTITUIR con prueba de equivalencia | Comparar los 5 archivos modificados vs Flow (reclamo 12 idénticos / 5 modificados); el iframe desaparece, pero todo enlace y comportamiento accesible debe quedar cubierto por `/estudio` (ver plan §7) |

**Regla transversal (D6):** ninguna implementación anterior se elimina hasta acreditar equivalencia con pruebas funcionales de las funcionalidades migradas; copia de seguridad verificable (ZIP + manifiesto SHA-256) antes de cambios estructurales.

## Bloque D — Regresiones heredadas de la revisión anterior (tratamiento como requisitos)

| ID | Fallo documentado (procedencia no verificable) | Corrección exigida en NN-107 | Prueba |
|---|---|---|---|
| R-BUG-1 | Una noticia importada no quedaba seleccionada automáticamente para producción | Tras importar/confirmar una noticia en el Studio, la API fija `project.active_story_id` y el flujo continúa con esa historia preseleccionada | E2E: importar → abrir proyecto → noticia activa correcta |
| R-BUG-2 | La proporción podía cambiar de 16:9 a 9:16 al crear el plan | El `ratio` del proyecto se fija en `format_profile` en la creación; crear el plan de producción nunca lo altera; cambiarlo exige acción explícita que dispara la invalidación dirigida del cap. 13 | Unit + E2E: crear plan mantiene el ratio original |

## Bloque E — Protocolo de auditoría diferencial F0 (convierte esta matriz en definitiva)

1. **Obtener el material:** propietario aporta `REVISION_UNIFICACION_NEURAL_NEWS.zip` (o confirma su inexistencia). Verificar SHA-256 y registrar en evidencia.
2. **Comparar árboles:** hashes de las 17 fuentes Flow vs `apps/studio` del ZIP (confirmar o refutar el reclamo 12/5); diff funcional de los 5 modificados.
3. **Cerrar Bloque C:** para cada componente, decidir REUTILIZAR/ADAPTAR/FUSIONAR/SUSTITUIR/PENDIENTE con criterios: ¿hay prueba que lo cubra?, ¿duplica la API?, ¿aporta validaciones ausentes?, ¿compila en el árbol destino?
4. **Decidir repo único (R-15):** `neural-news` vs `neuralnews` como base de NN-107, o portar módulos concretos (Bloque D de prior art). Registrar la decisión como ADR-015.
5. **Re-estimar:** recalcular F1–F5 con el resultado (la estimación de 20 h es presupuesto inicial, no compromiso — veredicto del propietario); congelar el subconjunto de entidades.
6. **Entregables de la puerta:** matriz definitiva (este documento, rev. definitiva), ADR-015, plan actualizado y backup verificable del repo antes de tocar estructura.
