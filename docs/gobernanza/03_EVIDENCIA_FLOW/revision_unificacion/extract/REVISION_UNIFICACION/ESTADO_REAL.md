# Estado real observado y riesgos de integración

**Corte:** 29-10-2026, URL publicada `https://desktop-hta6ms6.tailf8096f.ts.net:8443`, sesión DEMO. Se usaron contenidos inequívocamente ficticios. No se activaron servicios de pago, no se publicaron noticias, no se borraron datos ni se editaron piezas preexistentes. La última prueba de composición local quedó en `QUEUED` antes del cambio de dirección; no se continuó investigando ni se afirma que exista MP4 final.

## Qué se comprobó en ejecución

| Paso | Resultado | Evidencia |
|---|---|---|
| Acceso y rutas principales | `/`, `/fuentes`, `/noticias`, `/noticias/12`, `/lotes`, `/configuracion`, `/estudio` cargan | [mapa](MAPA_NAVEGACION_ACTUAL.md) |
| Fuente de texto ficticia | Alta aceptada; trabajo #185; estado pasó de pendiente a lista | [19](CAPTURAS/19-fuente-ficticia-resultado.png), [20](CAPTURAS/20-fuente-ficticia-analizada.png) |
| Candidata | Creó noticia #12 y extrajo 4 afirmaciones sin verificar | [21](CAPTURAS/21-noticia-ficticia-listado.png) |
| Investigación | Trabajo #186 completó sin inventar evidencia; 0/4 confirmadas | [24](CAPTURAS/24-noticia-ficticia-investigada.png) |
| Guion | Trabajo #187 creó v1, 98 palabras, con advertencia de incertidumbre y editor | [26](CAPTURAS/26-noticia-ficticia-guion.png) |
| Storyboard editorial | 5 escenas, rótulos y prompts de imagen preliminares; no medios | [27](CAPTURAS/27-noticia-ficticia-storyboard.png), [28](CAPTURAS/28-noticia-ficticia-prompt-imagen.png) |
| Aprobación | Permitió aprobar internamente la revisión v1 con 0/4 afirmaciones confirmadas; advirtió del problema | [29](CAPTURAS/29-noticia-ficticia-aprobacion.png) |
| Paso a Studio | Handoff `production_handoff.v1` importado, 1 fuente, guion íntegro | [30](CAPTURAS/30-studio-prueba-importada.png) |
| Selección para producción | Hizo falta pulsar «Producir en Vídeo» en la redacción duplicada para activar la pieza | [31](CAPTURAS/31-studio-prueba-activa.png) |
| Escenas Studio | 5 fragmentos editables; 98 palabras conservadas | [31](CAPTURAS/31-studio-prueba-activa.png), [32](CAPTURAS/32-studio-editar-escena.png) |
| Plan | Se creó y guardó v1 en almacenamiento del navegador; prompts editables | [34](CAPTURAS/34-studio-plan-ficticio-creado.png), [35](CAPTURAS/35-studio-plan-ficticio-guardado.png) |
| Composición local | Solicitud FFmpeg encolada; resultado no observado | [36](CAPTURAS/36-studio-composicion-accion.png) |

## Hallazgos reproducibles y causa localizada

1. **Dos aplicaciones siguen presentes.** `/estudio` carga `/studio/index.html` en un `iframe`. El origen y cookie se comparten, pero Studio tiene router visual, estado React y redacción propios. Causa: `apps/web/app/estudio/page.tsx:70`, `apps/studio/src/studio/App.tsx:43-88`. Reproducción: entrar desde noticia #12, abrir Studio y ver segunda navegación.
2. **Traspaso importado ≠ pieza activa.** El deep link importa la pieza pero «Guion y Escenas»/«Producción» siguen mostrando la noticia de ejemplo inicial hasta pulsar «Producir en Vídeo». Causa: `apps/studio/src/studio/App.tsx:73,88,192-204`; `HandoffImport.tsx` agrega el artículo sin activar el ID. Reproducción: [05](CAPTURAS/05-estudio-trapaso.png) → [09](CAPTURAS/09-studio-guion-escenas.png), luego [31](CAPTURAS/31-studio-prueba-activa.png).
3. **Verificación duplicada/inconsistente.** La noticia #12 mantiene 0/4 afirmaciones confirmadas en neural.news, pero Studio aumenta su contador de «verificadas con fuentes» al importarla. Causa probable: `storyToArticle` en `apps/studio/src/lib/handoffConsumer.ts` y cómputo de `studio/components/NewsEditorialTab.tsx` usan un criterio distinto al de `services/editorial_status.py`. El contador se observó pasar a 3 verificadas con fuentes de 4 noticias, incluyendo la importada. [30](CAPTURAS/30-studio-prueba-importada.png).
4. **Tiempo de toma incoherente.** En la prueba, Studio etiqueta cinco tomas de 8 s pero calcula las tomas 4 y 5 en 8,8 s. Causa: `studio/utils/scriptAnalyzer.ts` divide por frases/palabras sin imponer 8 s rígidos; `lib/productionProject.ts:137` copia la duración y `studio/components/ResultTab.tsx` habla de render fijo 8 s. El FFmpeg local admite hasta 30 s (`services/av_render.py:41,95`), por lo que puede aceptar un plan que no cabe en Omni 8 s. [31](CAPTURAS/31-studio-prueba-activa.png), [33](CAPTURAS/33-studio-plan-ficticio-previo.png).
5. **Formato desincronizado.** La vista de producción mostraba CRT 16:9 y prompt de toma 16:9; al crear plan, `ProductionPlanPanel.tsx:48` fuerza `9:16`. El storyboard editorial también usa 9:16. Reproducción: [33](CAPTURAS/33-studio-plan-ficticio-previo.png) → [34](CAPTURAS/34-studio-plan-ficticio-creado.png).
6. **Referencias canónicas sin activos transferibles.** Studio muestra tres referencias activas, pero su auditoría declara 0 `mediaId` reales, hoja maestra ausente y solo directrices en prompt. Causa: `studio/components/ResultTab.tsx:61-63,124-159`, `data/avProfiles.ts:5-7`. [13](CAPTURAS/13-studio-produccion.png).
7. **Guion demo de estilo genérico.** El borrador de prueba usa «Esto acaba de pasar», «Por qué importa» y cierre repetible; no demuestra adaptación editorial de NeuralDotAI ni citas integradas por afirmación. Causa: `providers/llm.py`/`services/scripts.py`; el adaptador real no se probó con claves. [26](CAPTURAS/26-noticia-ficticia-guion.png).
8. **Storyboard repetitivo y sin B-roll informativo.** En la noticia de prueba, las escenas editoriales repiten el presentador/CRT y rótulo recortado; no hay entidad de recurso de apoyo con procedencia/afirmación vinculada. Causa: `providers/image_prompt.py:25-62` y plantillas de `lib/productionProject.ts:53-66`. [27](CAPTURAS/27-noticia-ficticia-storyboard.png).
9. **El montaje actual es una simulación técnica.** El backend FFmpeg está programado para color, rótulos y tono seno; no monta imágenes reales, B-roll ni voz Algenib. Causa: `services/av_render.py:1-15,176-228`. El botón se pulsó para la pieza ficticia, pero se detuvo la inspección con el trabajo en cola. [36](CAPTURAS/36-studio-composicion-accion.png).
10. **Estado de proveedores contradictorio.** Configuración indica «Producción de vídeo fuera del MVP», mientras Studio ofrece un render Flow de 12 créditos/toma. No se activó por prohibición expresa de gasto. El `flow-sdk` local es un stub que rechaza la generación externa, así que el control visible no prueba un proveedor conectado. Causa: `api/ops.py:76-147`, `studio/components/ResultTab.tsx:241-256`, `apps/studio/src/flow-sdk/index.ts`. [17](CAPTURAS/17-configuracion.png), [13](CAPTURAS/13-studio-produccion.png).
11. **Acumulación/visibilidad de datos.** Fuentes muestra 50 registros listos con ejemplos repetidos; una pieza preexistente tenía 88 fuentes y 42 guiones. La lista de fuentes de esa pieza es muy larga y dificulta encontrar evidencia útil. La página de Fuentes pide `api.listSources()` sin paginación visible (`apps/web/app/fuentes/page.tsx:34-36`), mientras el endpoint tiene límite por defecto; el contador 50 es lo recibido, no garantía de total global. [01](CAPTURAS/01-fuentes.png), [04](CAPTURAS/04-noticia-detalle.png).

## Funcionalidad real frente a anunciada

- **Operativo en demo:** fuentes manuales, candidata, investigación que conserva incertidumbre, borrador, versiones/aprobación, storyboard textual, handoff, activación de pieza en Studio, edición de escenas, creación/guardado de plan, ZIP editorial ya existente.
- **Parcial:** experiencia de pieza única, verificación entre módulos, ratio/duración, referencias, revisión audiovisual, composición local y exportación MP4 (no confirmada en esta sesión).
- **Simulado:** evidencias `.invalid`, contenido de ejemplo de Studio, storyboard/prompts deterministas, vídeo FFmpeg de color/rótulo/tono.
- **No validado con proveedor real:** LLM, búsqueda, YouTube/Spotify/Gemini, generación de imagen y vídeo Flow. **Ausente en el flujo probado:** generación de B-roll informativo, voz sintética real, montaje de activos audiovisuales reales y aprobación final de vídeo.

## Consola, red, móvil y pruebas

El registro de consola de la pestaña devolvió `[]` para niveles `warn`/`error` durante la navegación inspeccionada. No se capturó una traza HTTP completa con status de cada petición; por tanto los errores de red no están descartados. Las capturas de esta revisión corresponden a viewport de escritorio; no se realizó una nueva prueba móvil tras la orden de detener la auditoría. El repositorio contiene E2E Playwright, pero no se ejecutó la suite en esta intervención para preservar el estado del trabajo. No se confirma aquí su estado actual.

## Estado del árbol de trabajo

Antes de crear esta carpeta, `git diff --stat` mostraba **37 archivos seguidos con diferencias**, entre ellos 2 eliminados de `apps/studio/dist` (artefactos generados), más múltiples archivos nuevos sin seguimiento. No se hizo commit, reset, clean, checkout ni borrado. El ZIP incluye una **copia de los archivos fuente actuales**, por lo que conserva los cambios sin confirmar en esos archivos; no incluye `.git`, bases de datos, datos de navegador ni dependencias instaladas. La carpeta original `auditoria-funcional-real/capturas` también permanece intacta.
