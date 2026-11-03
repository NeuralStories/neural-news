# PLAN MAESTRO V3 — neural.news como una única aplicación

**Versión:** V3.0 · **Fecha:** 29-10-2026 · **Estado:** PROPUESTA PARA REVISIÓN CONJUNTA — no se implementa nada hasta que se apruebe.
**Base de evidencia:** paquete de revisión `REVISION_UNIFICACION/` (inventario, matriz, mapa de navegación, estado real observado en `https://desktop-hta6ms6.tailf8096f.ts.net:8443`, 42 capturas) y las verificaciones de las sesiones 2026-10-28/29 (126 Python · 14 Studio · 5 extractor · 10 E2E).

---

## 0. Qué es V1, V2 y V3

- **V1 (hecho):** dos productos. neural.news editorial (FastAPI + Next.js) y NeuralStories Studio (Vite/React) recuperado de Flow. Cada uno con su propia redacción y estado.
- **V2 (estado actual, verificado):** Studio embebido en la web mediante iframe y traspaso `production_handoff.v1` con verificación de contrato, hash y deduplicación. Pipeline audiovisual simulado con FFmpeg real, presupuesto por trabajo y por lote. Funciona, pero siguen existiendo **dos redacciones, dos estados de verificación y dos navegaciones** (hallazgos 1-3 de `ESTADO_REAL.md`).
- **V3 (este plan):** **una sola aplicación**. Un frontend (apps/web), un núcleo de datos (apps/api), un flujo único `Investigar → Verificar → Seleccionar → Guion IA → Storyboard → Recursos → Producción → Montaje → Revisión → Exportar`. Studio deja de ser una segunda aplicación y se convierte en utilidades integradas.

## 1. Principios V3 (derivados de la matriz y el estado real)

1. **Una sola verdad por dato.** Etapa, verificación, aprobación y procedencia se calculan en el backend (`services/editorial_status.py`) y toda la interfaz las muestra tal cual. Se retira cualquier estado editorial paralelo (hallazgo 3).
2. **El backend es el núcleo.** Modelos, versiones, aprobación, contratos, cola, presupuesto y FFmpeg ya probados permanecen. Studio aporta utilidades, no un segundo sistema.
3. **Un objeto de trabajo: la pieza.** Una noticia con ID estable y su revisión de guion aprobada abre cada fase. El lote es agrupación opcional, no otra redacción.
4. **Nada se pierde.** Todo el trabajo actual (incluidos cambios sin confirmar) se conserva; la migración es aditiva y por fases con puerta de revisión conjunta.
5. **Lo simulado se declara.** FFmpeg de color/rótulo/tono, evidencias `.invalid` y prompts deterministas se etiquetan como simulación hasta que haya proveedor real autorizado.
6. **Seguridad editorial y de costes.** Aprobación humana en origen; `CONTRADICTED` bloquea producción; presupuestos por trabajo y lote; ninguna llamada de pago sin autorización explícita.

## 2. Qué se reutiliza sin reconstruir (inventario de decisión)

| De | Se conserva tal cual | Se fusiona | Se retira tras migrar |
|---|---|---|---|
| **apps/api** | Modelos y versiones, `editorial_status.py`, contratos (`production_handoff.v1`), cola persistente, presupuesto (diario + trabajo + lote), `av_render.py` FFmpeg, auditoría | Nuevos modelos: escena unificada, recurso audiovisual, proyecto AV persistido | — |
| **apps/web** | Shell único, Fuentes, Noticias (bandeja + estado), detalle con cabecera de decisión, Lotes con readiness, Configuración | Nuevas rutas V3: Escaleta, Recursos, Producción, Revisión | — |
| **apps/studio** | `scriptAnalyzer.ts` (partición ~8 s), `productionProject.ts` (plan editable + consistencia), `avProfiles.ts` (canon), catálogo de movimientos, modelo de referencias, `HandoffImport` (validación/hash) | Compilador de prompts por escena → dentro del modelo de escena unificado | `NewsEditorialTab` (redacción duplicada), `ResultTab` (prompts Flow no probados) |
| **flow-recovery (17 archivos)** | `scriptAnalyzer`, `newsDeduplication`, `constants` (canon), `types` | Lo demás como referencia de diseño | El `iframe` y el `flow-sdk` stub desaparecen de la app final (el stub pasa a documentación) |

Eliminaciones explícitas en V3 (solo tras aprobar la migración): redacción duplicada de Studio, doble contador de verificación, `iframe`, y los dos controles de presupuesto separados (quedará uno contextual).

## 3. Fases V3 y puertas de aceptación

### V3-F0 — Congelación y línea base (inmediato, sin código)
- Congelar el ZIP de revisión actual como punto de partida (ya existe: `REVISION_UNIFICACION_NEURAL_NEWS.zip` + manifiesto SHA-256).
- Decisión conjunta sobre la matriz: aprobar/matar cada fila de «Propuesta».
- **Puerta:** propietario aprueba el alcance V3 sobre este documento.

### V3-F1 — Persistencia del proyecto audiovisual en el backend
- Migrar el plan de producción de `localStorage` (`productionProject.ts`) a modelos de base de datos (proyecto AV con versión de guion aprobada, escenas, prompts, estado).
- La ficha de noticia abre el proyecto; el deep-link `?story=` deja de necesitar importación.
- **Puerta:** un proyecto AV sobrevive a limpiar el navegador y es recuperable por API; pruebas de integración.
- Riesgo: esquema de escena — resolver antes el modelo único (texto, afirmación vinculada, duración, plano, transición, prompts, recursos, estado).

### V3-F2 — Un modelo de escena y escaleta única
- Fusionar storyboard editorial (`providers/image_prompt.py`) + partición Studio (`scriptAnalyzer.ts`) + plan (`productionProject.ts`) en **un esquema de escena**: texto, afirmación vinculada (trazabilidad factual), duración coherente con el formato, plano/transición del catálogo, prompts de imagen/vídeo, recursos y estado de revisión.
- Resolver los hallazgos 4 y 5 (duracion 8,8 s vs 8 s y formato 16:9 vs 9:16) con una sola selección de formato que gobierne todo.
- **Puerta:** la misma escaleta se ve idéntica en editorial y producción; duraciones y ratio coherentes; B-roll como recurso nuevo con procedencia (diseño incluido).

### V3-F3 — Biblioteca de recursos audiovisuales
- Unificar referencias Studio + evidencia editorial en una gestión de recursos con **procedencia**: original / archivo licenciado / ilustración IA / simulado; autor, licencia, hash, versión y aprobación.
- Resolver R05/R07 (licencias del personaje y voz) aquí — es bloqueo real de producción honesta.
- **Puerta:** cada recurso distingue material original de ilustración generada; los 0 `mediaId` reales quedan visibles como pendiente, no como activo.

### V3-F4 — Un solo frontend (retirar el iframe)
- Migrar las secciones útiles de Studio (escaleta editable, personaje, fondo, voz, movimiento, referencias, producción) a rutas/components de `apps/web` con los tokens compartidos.
- Retirar `NewsEditorialTab` duplicado y el `iframe`; la navegación será la del flujo único (10 pasos) con el mismo shell.
- **Puerta:** recorrido completo en una sola navegación, escritorio y móvil, sin doble scroll ni doble menú; E2E del flujo completo en verde.

### V3-F5 — Producción, montaje y voz
- Montaje FFmpeg real: sustituir color/rótulo/tono por recursos aprobados de la biblioteca + pista de voz cuando se decida el motor TTS (Algenib u otro); narración continua sin cortes artificiales.
- Generadores reales (imagen/vídeo) solo como adaptadores con presupuesto y consentimiento por trabajo, tras validar SDK, costes y licencias (R06).
- **Puerta:** un MP4 montado con materiales reales, sincronizado, revisable; coste y procedencia en el manifiesto.

### V3-F6 — Revisión final y exportación única
- Una revisión final ligada al artefacto (vídeo + guion + evidencia + fuentes), con decisión editorial registrada.
- Un exportador: paquete con manifiesto (guion aprobado, storyboard, procedencia de medios, MP4, avisos). Los exportes técnicos (ZIP editorial, JSON del plan) quedan como secundarios.
- **Puerta:** exportación única trazable aceptada por revisión humana → hito operativo V3.

## 4. Riesgos y decisiones que toma el propietario

| # | Decisión | Impacta | Cuándo |
|---|---|---|---|
| D1 | Aprobar el alcance V3 y el orden de fases | Todo | V3-F0 |
| D2 | Modelo de escena único (propuesta en V3-F2) | Escaleta, prompts, render | V3-F2 |
| D3 | Licencias/activos del personaje y voz (R05/R07) | Recursos, producción honesta | V3-F3 |
| D4 | Motor TTS y proveedor de generación real (R06, presupuesto) | Voz, imagen, vídeo | V3-F5 |
| D5 | Retirada definitiva de `NewsEditorialTab` e `iframe` | Experiencia única | V3-F4 |

## 5. Qué NO cambia en V3

- Ninguna publicación automática.
- Ninguna llamada de pago sin autorización explícita y presupuesto.
- Los 17 archivos recuperados permanecen en `flow-recovery/source` como referencia; su reutilización pasa por la validación de procedencia/licencia.
- El trabajo sin confirmar del árbol se conserva: cada fase arranca de un checkpoint Git aprobado.

## 6. Referencias

- Paquete de revisión: `REVISION_UNIFICACION/` (inventario, matriz, mapa, estado real, propuesta de flujo, 42 capturas, manifiesto SHA-256) y `REVISION_UNIFICACION_NEURAL_NEWS.zip`.
- Estado verificado del sistema: `docs/informes/AUDITORIA_IMPLEMENTACION.md`, `UPDATE.md`, `docs/ACCESO.md`.
- Reglas editoriales vigentes: `docs/EDITORIAL_STYLE.md` · Riesgos: `RIESGOS.md` · Decisiones: `DECISIONES.md`.
