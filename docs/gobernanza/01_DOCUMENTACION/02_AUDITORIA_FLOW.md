# Auditoría independiente de flow-recovery.rar — 30/10/2026

## Evidencia, no inferencias
**Archivo examinado:** `03_EVIDENCIA_FLOW/flow-recovery.rar` (idéntico al adjuntado). **Herramienta de extracción propia del archivo:** `extractor/`; `source/` y `reports/` contienen el resultado. Hay 17 fuentes TypeScript/TSX. El informe del extractor dice que el 28/10/2026 leyó 17/17, dos pasadas en editor y sin fallos. Esta inspección verificó SHA256 local de 17/17 **frente al manifiesto aportado**. Es una comprobación de integridad interna, **no** confirmación independiente contra Flow remoto ni prueba de compilación.

## Inventario y resultado técnico
| Pieza | Confirmado en fuentes | Aprovechar como requisito | Prohibido heredar |
|---|---|---|---|
| `types.ts` | 8 pestañas, artículo, bloque, escena, refs, voz | entidades y relaciones | contrato monolítico antiguo, etiquetas/versiones heredadas |
| `constants.ts` | NeuralDotAI, plató CRT, voz Algenib, cámara, URLs demo | vocabulario visual y presets editables | identidad antigua, URLs stock «aprobadas», noticias ficticias |
| `utils/scriptAnalyzer.ts` | texto calculado por palabras y fragmentos de ~8 s | segmentación semántica y estimación temporal | cortar audio obligatoriamente cada 8s, ritmo fijo universal |
| `utils/newsDeduplication.ts` | IDs, URL canonical y Jaccard de titulares | primera barrera de duplicado | equiparar similitud léxica a misma noticia |
| `App.tsx` | estado React, flujos y funciones `Flow.generate.*`, `Flow.media.select`, `Flow.download` | recorrido interactivo y export manual | depender de runtime propietario fuera de Flow |
| `NewsEditorialTab.tsx` | agrupación, importación, filtros, estados | selección de bloque y editor | elevar material importado a verificado automáticamente |
| `CharacterSheetTab.tsx` | hoja maestra/gestión de personaje | references + aprobación | recrear rostro por descripción textual |
| `BackgroundTab.tsx` | plató/fondo, 9:16/16:9 | biblioteca de platós/presets | fondos genéricos equivalentes al original |
| `VoiceTab.tsx` | perfil Algenib y velocidad | voz configurable y duración | imponer Algenib a maxDotAi sin validación |
| `MovementTab.tsx` | movimientos + transiciones | catálogo de dirección | repetir movimientos en cada toma |
| `ReferencesTab.tsx` | referencias editoriales y visuales, `mediaId` | assets con procedencia/URI y hash | tratar `mediaId` interno como universal, afirmar consistencia por texto |
| `ResultTab.tsx` | compilación por escena, prompt, refs reales vs texto, export | paquete manual por toma | llamar «verificado» a prompt textual sin referencia real |
| `BackupModal.tsx` | importación/exportación UI | recuperación de paquete | confundir JSON de ajustes con backup de PostgreSQL |
| `TopNavigation`, `HelpModal`, `sourceManifest` | 8 pestañas, ayuda e inventario | orientación UX y trazabilidad | duplicación de interfaces, nombres heredados |

## Fallos concretos identificados
F-01: `constants.ts` fija `NEURALDOTAI_CANONICAL` y `@neuraldotai`; **nuevo personaje oficial: `maxDotAi`**, handle en Flow pendiente de comprobar. F-02: `INITIAL_VISUAL_REFERENCES` usa imágenes Unsplash con estado `aprobado` aunque no son assets aprobados por usuario. F-03: `INITIAL_EDITORIAL_REFERENCES` contiene URLs y extractos de demostración; no usarlos como noticias. F-04: perfil Algenib 1.18 y 2.85 palabras/s son hipótesis del prototipo, no calibración confirmada para MaxDotAi. F-05: `scriptAnalyzer` genera escenas de 8s y prompts con locución embebida; separar audio, beats, tomas y duración de clip según modelo. F-06: llamada `Flow.generate.video()` existe **dentro del editor**, no demuestra acceso oficial externo. F-07: medio por `mediaId` y medio por descriptor textual son semánticamente diferentes; solo el primero constituye referencia de galería para ese entorno. F-08: `NewsEditorialTab` necesita revisión de estados; importación ≠ verificación. F-09: deduplicación Jaccard falla ante reescrituras semánticas y continuaciones de historias. F-10: backup JSON es export, no recuperación transaccional de DB.

## Lo que no está en el RAR
No está acreditada una instalación compilable/independiente, login o credenciales de Flow, archivos binarios de vídeos del usuario, el activo de MaxDotAi, aprobación de plató/voz, servicio público de generación Flow a terceros, modelos/coste autorizados, derechos de contenido, fuentes de noticias actuales ni API operativa. **No inventar estos recursos.**

## Protocolo de aprovechamiento
1. Conservar original + hashes; nunca ejecutar scripts del extractor automáticamente.
2. Crear un inventario de funcionalidades, no copiar los componentes como base.
3. Usar las pruebas de regresión `F-01...F-10` como requisitos obligatorios.
4. Preparar `FlowManualPackage`: prompt EN/ES, referencias con hashes y disponibilidad, actuación/encuadres, duración/capability, instrucciones para pegar el `@maxDotAi` real solo cuando se confirme en cuenta, checklist y ruta de importación del MP4 resultante.
5. Una conexión API futura se presenta como **nuevo adaptador independiente** con prueba real y credenciales autorizadas. La documentación de Google Flow acredita uso de su interfaz y menciones `@`, pero no autoriza a concluir que `flow-sdk` pueda instalarse fuera.
