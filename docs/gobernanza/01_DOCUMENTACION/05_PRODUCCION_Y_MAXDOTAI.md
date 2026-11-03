# Dirección audiovisual, identidad MaxDotAi y producción rentable

## Regla de identidad definitiva
El **único personaje generativo autorizado como presentador es `maxDotAi`**, nombre literal proporcionado por el propietario. Otra opción es reutilizar **vídeos originales aportados por el propietario**, que pueden ser grabaciones reales o clips generados; no deducir su origen sin metadatos. No recrear un actor alternativo ni escribir rasgos inventados. El `@` y el identificador exactos de la cuenta Google Flow se verificarán visualmente por el operador; el sistema puede mostrar `@maxDotAi` como **etiqueta orientativa pendiente de verificación**, no como handle confirmado. `NeuralDotAI`, Algenib y el fondo CRT textual del archivo recuperado son referencias históricas, no identidades activas.

## Biblia audiovisual canónica, versión 0 antes de disponer de medios
- `identity`: `maxDotAi`, `source_kind=FLOW_CHARACTER`, `status=UNVERIFIED_EXTERNAL`.
- `owned_videos`: sin vídeos incluidos en este paquete => biblioteca vacía, `PENDING_ASSET`.
- `stage`: referencia deseada estética CRT solo si se aporta material aprobado; `UNAPPROVED_REFERENCE`.
- `voice`: no confirmada por el archivo. `REQUIRES_SAMPLE`; no clonar ni imponer Algenib.
- `visual_style`: informativo tecnológico dinámico; entradas laterales, plano de pecho preferente, variaciones de perspectiva, efectos glitch RGB breves sin pérdida de inteligibilidad; no repetir idéntica transición en todas las tomas.
- `screen_text`: «NeuralStories News» fue pedido para las pantallas del prototipo; nombre de marca final visible y recursos requieren aprobación. Los rótulos legibles se componen en postproducción, no se confían a IA generativa.
- `ratio`: 9:16 (shorts) y 16:9 (programas); cada encuadre se valida manualmente, no recortar ciegamente cabezas/texto.
- `identity_lock`: hash/versiones de material aprobado y matriz de compatibilidad por perfil, nunca solo una descripción de personaje.

## Biblioteca de vídeos de usuario
Ingesta autorizada de MP4/MOV; extraer duración, FPS, resolución, pistas, codec con `ffprobe`; SHA-256; etiqueta procedencia (`USER_ORIGINAL`, `USER_GENERATED`, `FLOW_CHARACTER_OUTPUT`), derechos, idioma/voz, rol de toma, expresión, gesto, set/ropa/iluminación, ratio, posibilidades de reutilizar sin audio, in/out points, si boca coincide con texto; thumbnails privados, aprobación humana. Al reutilizar vídeo viejo NO se le atribuye locución nueva en labios. Si la noticia requiere una frase no pronunciada, elegir B-roll no sincro, locución fuera de campo autorizada, o exportar prompt para toma nueva. Nunca sincronización labial ficticia sin consentimiento/tecnología acreditada.

## Selección de material: jerarquía
1. Evidencia visual auténtica/legible relacionada con noticia (captura oficial, vídeo autorizado, gráfico real), sin contextualizar falsamente.
2. Material aprobado de usuario/MaxDotAi apropiado para el mensaje, encuadre y voz.
3. Gráfica exacta o UI recreada **marcada como representación**, si comunica datos verificables.
4. Imagen/clip generativo para ilustrar conceptos abstractos — siempre rotular como recreación cuando pueda confundirse con hechos.
5. Toma nueva con `maxDotAi` en Flow manual, si material disponible/handle aprobado.
6. `BLOCKED` con motivo si no existe solución honesta, no inventar recurso.

## Lenguaje de dirección de planos
Un `NarrationBeat` representa unidad de sentido con texto continuo y tiempos sugeridos. Un `Shot` es ventana audiovisual que se superpone a uno o más beats, con `source_type`:
`USER_VIDEO | FLOW_CHARACTER_MANUAL | REAL_BROLL | GENERATED_BROLL | EXACT_GRAPHIC | SCREEN_RECORDING | TITLE_CARD | PENDING`. Cada plano añade `start_ms`, `end_ms`, `purpose`, `claim_ids`, `asset_id`, `asset_approval`, `identity_version`, `background_version`, `camera_preset`, `transitions`, `prompt_package_id`, `estimated_cost`, `status`.

No forzar una sola toma por oración ni guion a clips de ocho segundos. Duración del generador depende del modelo **en ese momento**. La pista de audio puede durar 53 segundos mientras las tomas suman 53; verificar continuidad y ±100ms de tolerancia temporal para animática, y ±1 fotograma en render final tras fps definido.

## Plan de cámara/efectos
Presets: `static_chest_up`, `slow_push_in`, `whip_left/right`, `snap_zoom`, `side_angle`, `crt_rgb_glitch`, `horizontal_screen_flip` solo cuando no altere identidad o texto (no invertir rótulos). Cada uno define rango de aplicación, duración, margen seguro, frecuencia máxima, efecto sobre audio (= ninguno). Ejemplo: un glitch aislado 0,15–0,4s sirve de acento; no aplicarlo como ruido permanente. No sustituir a una edición de noticias con movimientos arbitrarios.

## Tres vías de producción
**A. Vídeo ya aportado:** selecciona `media_id`, in/out y audio; recorta, rótulo, subtítulo; no genera nuevo material. **B. Flow manual:** `prompt_en`, traducción, instrucciones de selección de personaje y referencias, imagen/hoja si está verificada, duración y ratio permitidos por modelo, checklist; al terminar usuario importa MP4 y registra `operation_id` manual, coste real si se conoce. **C. Motion graphics:** el renderer produce SVG/frames/clip a partir de `GraphicSpec` tipado. Los renderizados programáticos se ejecutan desde worker y no consumen créditos generativos.

## Compilador de prompts: orden e invariantes
1. Objetivo narrativo (qué explica la escena).
2. Fuente de identidad: `maxDotAi` solo si personaje vinculado; en otro caso bloquear la generación de presentador.
3. Referencias reales aprobadas: assetID, hash, rol y modo de adjuntado. No escribir que adjuntaste imagen si no está.
4. Escenario y vestuario exclusivamente desde referencias canónicas, no reinventarlos.
5. Shot/encuadre/movimiento concretos y duración realmente soportada.
6. Acción y expresión; locución exacta si se confía en audio in-model y modelo lo soporta, o indicar audio aparte. No mezclar de forma ambigua.
7. Restricciones de continuidad: una identidad, un set, sin nuevos personajes, sin duplicar rasgos, coherencia de iluminación; gráficos/rótulos se montan externamente.
8. Negativos útiles, no excesivos; `json` de assets y versión de compilador.
9. Verificaciones: identidad, primer plano, fondo, vídeo presente, labios/voz, legibilidad, ausencia de cambios no solicitados.

## Animática y cálculo de costes
Antes de pagar generación: timeline de stills o placeholders explícitos + clips existentes + SVG animados + audio autorizado o pista silenciosa DEMO. Validar ritmo, cobertura 100% del timeline, variedad visual, zona segura 9:16, cifras y subtítulos. Generar y almacenar `cost_estimate = sum(video_shots * provider_quote + TTS + image + render + storage)`, separado en `estimated`, `reserved`, `actual`; si tarifa desconocida, costo `UNKNOWN` y bloquear ejecución pagada; no establecer valores falsos.

## Invalidez selectiva
Cambiar el valor de un claim afecta guion, TTS, subtitles, gráficos y escenas que citan claim; no necesariamente fondo CRT o clips neutros. Cambiar `identity_version` invalida presentador y sus prompts; no gráficos de datos. Cambiar ratio afecta crops y layout/rótulos, no la verdad editorial. Cada artefacto registra `input_hashes`, `parent_revision`, `generated_with`, `approval` y `output_hash`.

## Especificación de un lote 5/10
Lista ordenada de `story_revision_id` aprobadas. Intro/puentes/cierre/overlays con duración y prioridad; no reescribir 10 noticias en un único prompt. Export de pieza y de conjunto. Mantener tiempos y reutilización de activos; informar duración estimada y recursos pendientes.

## Reglas de verdad visual
Nunca representar una falsa captura de software como si fuera oficial; distinguir metraje ilustrativo del hecho; no falsear cifras en gráfica mediante truncado de eje no señalado; mostrar fuente/unidades; una voz sin autorización no se sintetiza. Los recursos generativos son creativos, no prueba documental.
