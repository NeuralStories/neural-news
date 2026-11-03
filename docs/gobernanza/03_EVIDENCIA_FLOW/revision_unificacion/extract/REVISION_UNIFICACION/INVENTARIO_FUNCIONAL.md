# Inventario funcional y procedencia

Fecha de corte: 29-10-2026. Proyecto activo: `C:\Users\haxth3\Documents\news_Neural`. Esta revisión describe el árbol de trabajo actual, incluidos cambios sin confirmar, y las pantallas observadas en `https://desktop-hta6ms6.tailf8096f.ts.net:8443`. No equivale a una propuesta de implementación aprobada.

## Las dos aplicaciones y el código recuperado

1. **neural.news editorial**: `apps/web` (Next.js/React) y `apps/api` (FastAPI/SQLAlchemy), con worker, esquemas en `packages/contracts`, migraciones y pruebas. Tiene datos persistentes, fuentes, candidatas, investigación, guiones versionados, aprobación, lotes, storyboard y paquetes editoriales.
2. **NeuralStories Studio**: `apps/studio` (Vite/React). Tiene otra redacción de noticias, referencias, canon de personaje/plató/voz, división de guion, prompts de toma, plan audiovisual y controles de render. Hoy se carga dentro de `apps/web/app/estudio/page.tsx` con un `iframe`; sigue siendo otro frontend y otro estado de aplicación.
3. **Recuperación de Flow**: `flow-recovery/source` conserva 17 archivos TS/TSX, más `flow-recovery/reports/manifest.json` y el ZIP original recuperado. `apps/studio/src/studio` adapta/copió esa base; `apps/studio/src/flow-sdk` es un adaptador local. El inventario y SHA-256 originales están en `INVENTARIO_FLOW.md`. La procedencia de los activos y la licencia del código recuperado siguen pendientes de confirmar antes de reutilizarlo para publicación.

## Módulos de neural.news

| Módulo | Función observable o implementada | Código principal |
|---|---|---|
| Acceso/demo | Entrada demo; API de sesión | `apps/web/app/page.tsx`, `apps/api/src/neuralnews/api/auth.py` |
| Fuentes | URL, texto/archivo, transcripción manual, búsqueda y estados | `apps/web/app/fuentes/page.tsx`, `apps/api/src/neuralnews/api/sources.py`, `services/sources.py` |
| Ingesta | Manual, web/RSS, YouTube, Spotify y análisis de vídeo; varios conectores solo preparados | `apps/api/src/neuralnews/providers/{manual,web_rss,youtube,spotify,video_analysis}.py` |
| Extracción/deduplicación | Candidatas automáticas y similitud | `services/sources.py`, `services/dedupe.py`, `providers/llm.py` |
| Investigación/verificación | Afirmaciones, evidencias, clasificación y puntuación | `services/research.py`, `providers/research.py`, `services/editorial_status.py` |
| Guionización | Borrador determinista demo o adaptador LLM, edición, versiones y aprobación humana | `services/scripts.py`, `providers/llm.py`, `apps/web/app/noticias/[id]/page.tsx` |
| Storyboard | Escenas orientativas, duración, rótulos y prompt de imagen; no genera medios | `providers/image_prompt.py`, `api/stories.py` |
| Lotes y exportación | Selección 5/10, bloqueos, orden, ZIP editorial | `apps/web/app/lotes/page.tsx`, `services/batches.py`, `api/batches.py` |
| Traspaso | Contrato `production_handoff.v1`, hash y guion aprobado | `services/handoff.py`, `packages/contracts/production_handoff.v1.schema.json` |
| Presupuestos/trabajos | Límite diario, techo de lote, cola y registros | `services/budget.py`, `services/av_jobs.py`, `queue.py`, `worker_tasks.py` |
| Montaje local simulado | MP4 FFmpeg con fondo de color, rótulos y tono; sin imagen/voz editorial real | `services/av_render.py`, `api/av.py` |
| Configuración | Proveedores, gasto y pesos de puntuación | `apps/web/app/configuracion/page.tsx`, `api/ops.py` |

## Módulos de Studio

| Módulo | Función observable o implementada | Código principal |
|---|---|---|
| Noticias/Redacción | Lista propia, filtros, bloques, aprobación, importación manual/lote y activación de noticia | `studio/components/NewsEditorialTab.tsx`, `studio/App.tsx` |
| Handoff | Importa noticia aprobada, valida esquema/hash e idempotencia; agrega copia a redacción Studio | `components/HandoffImport.tsx`, `lib/handoffConsumer.ts` |
| Personaje | Ficha canónica, prompt de hoja maestra, selección/solicitud de imagen | `studio/components/CharacterSheetTab.tsx`, `studio/App.tsx` |
| Fondo CRT | Presets de escenario/ratio y selección de fondo | `studio/components/BackgroundTab.tsx` |
| Voz Algenib | Ficha de voz y ajuste de cadencia; sin síntesis TTS conectada | `studio/components/VoiceTab.tsx` |
| Guion y escenas | Texto continuo, partición ~8 s, edición de fragmentos | `studio/components/ScriptTab.tsx`, `studio/utils/scriptAnalyzer.ts` |
| Movimiento | Catálogo de cámara y efectos para prompts | `studio/components/MovementTab.tsx` |
| Referencias | Bibliotecas editorial y audiovisual, selección y export/import | `studio/components/ReferencesTab.tsx` |
| Producción y vídeo | Prompt de toma; llamada `Flow.generate.video` con autorización de créditos | `studio/components/ResultTab.tsx`, `studio/App.tsx`, `flow-sdk/index.ts` |
| Plan de producción | Escenas, prompts editables, consistencia y versiones locales | `components/ProductionPlanPanel.tsx`, `lib/productionProject.ts` |
| Composición local | Solicita al backend FFmpeg y descarga MP4 de activos simulados | `components/ProductionPlanPanel.tsx`, `lib/apiClient.ts` |
| Perfil canónico | Referencias lógicas de NeuralDotAI, CRT y voz, sin activos licenciados incorporados | `data/avProfiles.ts` |

## Los 17 archivos recuperados de Flow

Se conservan en `flow-recovery/source/`:

| # | Archivo | Papel recuperable |
|---:|---|---|
| 1 | `types.ts` | Modelo tipado de noticia, escenas y referencias |
| 2 | `constants.ts` | Presets y datos de ejemplo |
| 3 | `utils/scriptAnalyzer.ts` | Duración y partición de guion |
| 4 | `utils/newsDeduplication.ts` | Detección de duplicados local |
| 5 | `data/sourceManifest.ts` | Metadatos/hash del backup |
| 6 | `App.tsx` | Orquestación de estado y llamadas Flow |
| 7 | `components/TopNavigation.tsx` | Pestañas |
| 8 | `components/NewsEditorialTab.tsx` | Redacción propia |
| 9 | `components/CharacterSheetTab.tsx` | Hoja de personaje |
| 10 | `components/BackgroundTab.tsx` | Platos CRT |
| 11 | `components/VoiceTab.tsx` | Perfil de voz |
| 12 | `components/ScriptTab.tsx` | Guion y escenas |
| 13 | `components/MovementTab.tsx` | Movimiento |
| 14 | `components/ReferencesTab.tsx` | Referencias |
| 15 | `components/ResultTab.tsx` | Prompt y resultado vídeo |
| 16 | `components/HelpModal.tsx` | Ayuda |
| 17 | `components/BackupModal.tsx` | Copia/importación de configuración |

`INVENTARIO_FLOW.md` conserva tamaño y SHA-256 de cada archivo. Los 17 se incluyen en el ZIP de revisión como código de estudio. No hay en esa recuperación un scaffold ejecutable, CSS/activos definitivos ni contrato de licencia de `flow-sdk`.
