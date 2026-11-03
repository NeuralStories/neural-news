NEURAL.NEWS — LÓGICA FUNCIONAL COMPLETA Y REGLAS DE IMPLEMENTACIÓN
Estado: especificación funcional rectora propuesta para la construcción nueva. No es código ejecutado ni una integración de Google Flow verificada. 
0. Regla superior: Flow es el corazón creativo, no un apéndice
La nueva aplicación se construye desde cero. El código recuperado en flow-recovery.rar contiene 17 fuentes TS/TSX y describe un estudio organizado en ocho pestañas: noticias, personaje, fondo, guion, voz, movimiento, referencias, resultado. Ese orden, sus controles y su utilidad deben reproducirse funcionalmente y mejorarse. No basta con presentar esas pestañas sin implementación, adjuntar el RAR o usarlo como inspiración estética. Las capturas/constantes heredadas no implican activos aprobados ni APIs disponibles.

Producto: una única plataforma que convierte noticias en un informe verificable, un guion de locución, una planificación audiovisual y una pieza montada; soporta una noticia o programas de 5/10 noticias y versiones 9:16 / 16:9.

Presentador autorizado: maxDotAi en Flow, una vez confirmados el identificador y referencias reales, o vídeos aportados por el propietario. No crear un tercer presentador. NeuralDotAI en el código recuperado es un identificador heredado, no personaje nuevo. Ni la voz «Algenib» ni un fondo de ejemplo cuentan como activos aprobados hasta su validación.

Fórmula de producto: CAPTACIÓN → DOSSIER VERIFICADO → GUION + DIRECCIÓN → ESTUDIO FLOW (8 PASOS) → TOMAS / GRÁFICOS → PREVISUALIZACIÓN → MONTAJE → REVISIÓN → SALIDA.
1. Los cuatro niveles, una sola fuente de datos
1. Redacción: descubre, guarda, agrupa, contrasta, decide y prepara noticias. Los hechos no se extraen del generador de vídeo.
2. Dirección editorial: transforma un dossier en versiones de guion, pronunciación, locución, estructura temporal y mensajes visuales; conserva enlaces de cada afirmación a su evidencia.
3. Estudio de producción basado en Flow: permite editar de verdad los ocho pasos; cada cambio se guarda y afecta los prompts, el storyboard y/o las salidas correspondientes.
4. Producción y operaciones: gestiona vídeos de usuario, exportaciones manuales a Flow, gráficos programáticos, modelos configurables, previsualización, montaje, costes, estados y aprobaciones.
Un mismo project_id y revisiones versionadas unen los niveles. No crear dos aplicaciones, dos editores ni datos duplicados.
2. Inicio: configuración mínima y activos reales
Primera ejecución: crear propietario local, configurar directorios, base PostgreSQL y almacenamiento de medios; alta opcional de proveedores LLM/API. Permitir modo sin APIs usando fixtures DEMO explícitos. La interfaz de Configuración admite credenciales cifradas, nombres de modelos, endpoints, límites de coste, timeout, estado de salud y capacidades efectivamente comprobadas. .env queda para parámetros de arranque, no como editor web arbitrario de secretos.

Crear Biblioteca canónica con fichas independientes de: (a) personaje maxDotAi y referencia/handle verificable, (b) vídeos aportados (origen declarado, voz, labios, plano, duración, derechos y hash), (c) platós y fondos aprobados, (d) voces autorizadas, (e) estilos gráficos, tipografías, rótulos, logotipo y guías, (f) música/efectos con licencia y (g) material documental. Cada activo comienza PENDIENTE salvo aprobación explícita. Un descriptor textual no sustituye a una imagen, vídeo, mediaId o archivo.

Los archivos audiovisuales van a un repositorio de medios/almacenamiento de objetos y a PostgreSQL solo sus metadatos y referencias; no guardar vídeo en base64 en filas.
3. Captación de noticias
Entrada: RSS, APIs oficiales, feeds y sitios cuya extracción esté autorizada, URL introducida, documento, texto, transcripción aportada. Primera etapa: conectores sencillos reales, no scraping masivo obligatorio.

Para cada hallazgo guardar: source_id, url_original, canonical_url, título, fecha de publicación declarada, fecha de obtención, autor si existe, contenido extraído, fragmentos con offsets, idioma, hash y licencia/condiciones. Guardar snapshot/procedencia. La fecha de recolección no debe sustituir a la de publicación.

Normalización: eliminar HTML irrelevante, conservar citas y vínculos, detectar idioma, desambiguar fechas y entidades, y etiquetar indicios de contenido incompleto.

Deduplicación: primero URL canónica, GUID/hash y título; después similitud semántica para agrupar coberturas del mismo evento, distinguiendo actualización legítima de copia. Si hay contradicción, no fusionarla silenciosamente. Cada artículo conserva origen; la unidad editorial es una Story/historia agrupada.

Priorización: frescura, relevancia para noticias IA, novedad, importancia, diversidad temática, evidencia disponible y potencial visual. La prioridad se propone, no equivale a veracidad.

Seguridad: todo lo extraído es dato no fiable; nunca ejecutar instrucciones contenidas en páginas, documentos o transcripciones. Respetar robots/licencias, límites de petición y datos personales.
4. Extracción de hechos y aprobación editorial
Un rol LLM extrae afirmaciones atómicas: qué, quién, cuándo, cifras, condiciones, opiniones y citas. Cada afirmación lleva claim_id, fragmento exacto de respaldo, source_id, fecha y grado de respaldo. El sistema debe poder señalar qué frase del guion proviene de qué afirmaciones.

Estados sugeridos por afirmación: SIN_EVIDENCIA, RESPALDADA, CONTRADICHA, DESACTUALIZADA, DESCARTADA. Los estados de noticia y su aprobación humana son independientes. La comparación con fuentes adicionales no es sinónimo de verificación perfecta: un comunicado identifica una afirmación atribuida, no siempre una verdad independiente.

Salida: dossier con titular propuesto, 5W, resumen fiel, cronología, contexto, fuentes, discrepancias, cifras con unidades, enlaces, riesgos, pronunciaciones y propuesta de relevancia. Nada llega a rotularse como hecho cierto si su afirmación sigue pendiente. El humano puede corregir, aprobar versión o bloquear.

Estados editoriales de la noticia: CAPTURADA → EN_REVISION → LISTA_PARA_GUION → GUION_EN_REVISION → GUION_APROBADO; ramas DESCARTADA / BLOQUEADA. Importar nunca cambia por sí solo a APROBADA.
5. Crear proyecto y formatos
Desde Redacción: «Crear vídeo de esta noticia» o «Crear programa» (selección/ordenación de 5 o 10, y posibilidad de otra cantidad). El proyecto hereda un snapshot editorial concreto; permite Short 9:16, Informativo 16:9 y variantes de duración, relación y plataforma. No forzar una única duración a todas las noticias.

La ficha del proyecto contiene project_id, story_revision_ids, format_profile, visual_bible_revision, language, voice_mode, ratio, target_duration, budget_limit, workflow_revision, owner, status. Los bloques comparten intro, intersticiales y cierre sin rehacer las noticias.

Se abre el Estudio Flow como flujo principal, no una pantalla minimalista de guion. Debe disponer de guardado automático, volver/avanzar, vista previa, indicador de incompletos y acceso a todas las etapas.
6. Estudio Flow: ocho etapas funcionales obligatorias
PASO 1 — NOTICIAS (NewsEditorialTab)
Propósito: elegir la noticia/bloque, orden, fuente y alcance editorial del vídeo.

Controles: bandeja de noticias, filtros fecha/estado/tema, ver fuentes/afirmaciones, elegir noticia activa, crear bloque 5/10, reordenar, elegir formato, vincular dosier aprobado. Opción manual para una noticia demostrativa etiquetada DEMO.

Salida: snapshot/versiones editoriales que nutren el proyecto. Regla: noticia importada ≠ verificada; si no está aprobada se puede planificar un borrador, no publicar como noticia contrastada.
PASO 2 — PERSONAJE (CharacterSheetTab)
Propósito: establecer quién presenta y qué material controla su identidad.

Controles: maxDotAi / «Usar mis vídeos» / combinación por toma; ficha canónica con imágenes/vídeos auténticos, mediaId de Flow solo si confirmado, hoja maestra si fue aportada, historial de versiones, encuadre, vestuario y validación del rostro. Inventario de clips importados con miniaturas, in/out y procedencia. Ninguna identidad alternativa predeterminada.

Salida: presenter_profile_revision y disponibilidad de recursos. Regla: seleccionar el nombre «maxDotAi» no equivale a tener conectado Flow; cuando falten archivos o handle, mostrar PENDIENTE_DE_VINCULAR, generar paquete de instrucciones condicionado y no inventar un rostro.
PASO 3 — FONDO (BackgroundTab)
Propósito: controlar el plató y cómo se verá en cada formato.

Controles: biblioteca de sets aprobados (incluido CRT si se aporta la referencia real), elegir 9:16/16:9, zonas seguras para rótulos, recorte, capas de monitores, versión, prueba de fondo con el personaje; fallback «pendiente» sin afirmar que es el definitivo.

Salida: stage_revision + parámetros de composición. Regla: conservar la referencia visual verdadera del usuario; el texto de un prompt solo no garantiza recreación exacta del fondo.
PASO 4 — GUION Y ESCENAS (ScriptTab y scriptAnalyzer)
Propósito: preparar locución y desglose visual conjunto.

Controles: guion continuo editable con fuentes por frase; propuestas de apertura, desarrollo, cierre; estimación temporal calibrada por voz; detectar palabras/cifras/nombres; seleccionar distintos ritmos y duraciones; edición individual de bloques narrativos; editor de storyboard con orden y duración de tomas; comprobación de no perder frases al dividir.

Regla crítica: separar NarrationBeat (unidad de sentido), Shot (ventana visual) y GeneratedClip (salida del modelo). La locución puede ser continua aunque los clips generativos duren ~8 s; no cortar el audio por obligación cada ocho segundos. Los límites temporales son capacidades del proveedor, no límites narrativos.

Salida: script_revision, beats con claim_ids, duración y storyboard inicial. Toda edición que altere hechos requiere nueva revisión editorial; cambios solo de estilo no reabren automáticamente los hechos.
PASO 5 — VOZ (VoiceTab)
Propósito: fijar voz, cadencia, pronunciación y método de obtención.

Controles: voz de tomas existentes, voz aprobada de MaxDotAi/Flow, locución original aportada o servicio TTS autorizado; ritmo, pausas, énfasis, diccionario de nombres, idioma, muestra escuchable si existe. La voz «Algenib» del prototipo no se impone como configuración real.

Salida: voice_profile_revision, narration_track o «pendiente». Regla: una voz nueva sobre un clip viejo con labios visibles es una incoherencia salvo sincronía real y consentimiento; preferir voz en off y B-roll, plano sin habla, o generar toma correcta. Glitch únicamente en imagen, sin distorsionar la voz del presentador.
PASO 6 — MOVIMIENTO (MovementTab)
Propósito: dirección de cámara y dinamismo, no efectos repetitivos.

Controles: editor de plano por plano, primeros planos de pecho, acercamiento, ángulo lateral, aparición lateral, zoom, cortes, inversión horizontal de imagen con protección de textos, glitches CRT/RGB breves; intensidad, duración y orden, biblioteca de presets aprobados.

Salida: shot_direction por toma. Regla: movimientos elegidos por intención: destacar dato, explicar, introducir, concluir; prohibido un patrón idéntico aplicado automáticamente a todas las tomas. La imagen puede invertirse, pero nunca los títulos legibles. El rostro no debe cambiar por usar la inversión.
PASO 7 — REFERENCIAS (ReferencesTab)
Propósito: hacer explícitas las evidencias y los activos audiovisuales vinculados a cada toma.

Controles: dos bibliotecas separadas: editorial (fuentes y evidencia) y audiovisual (personaje, fondo, B-roll, logos, gráficos, vídeos, imágenes). Añadir, etiquetar, previsualizar, categorizar, versionar, aprobar/descartar, fijar por proyecto/episodio/toma y comprobar disponibilidad.

Salida: approved_asset_links con hash, uso y estado. Regla: mediaId solo tiene significado confirmado para la galería concreta de Flow. Referencias solo textuales deben figurar PROMPT_ONLY, nunca presentarse como archivos adjuntos.
PASO 8 — RESULTADO Y PRODUCCIÓN (ResultTab)
Propósito: construir paquetes de producción concretos a partir de todo lo anterior.

Controles: resumen de noticia, guion, ratio, voz, referencias, tomas, coste y pendientes; selector de toma; prompt editable por toma, EN para generador y explicación ES; ficha de composición/alternativas; botones «Copiar», «Exportar proyecto», «Preparar para Flow», «Importar vídeo generado», «Aprobar toma», «Previsualizar montaje» y «Renderizar» solo si los servicios están disponibles realmente.

Salida: ProductionPackage, FlowManualPackage, GraphicSpec y finalmente medios importados/compuestos. Regla: prompt preparado ≠ vídeo generado; exportar JSON ≠ hacer backup de BD; referencia textual ≠ referencia adjunta. No afirmar compatibilidad de flow-sdk externo por su aparición en el editor recuperado.

Todos los pasos: tienen entrada, controles que realmente alteran datos, guardado en PostgreSQL, estado y revisiones, validaciones, vista previa y pruebas de interacción. Si un paso está pendiente por falta de credenciales o activos, el resto del estudio debe seguir funcionando.
7. Motor automático de dirección: seleccionar por plano, no un generador para todo
El «director» recibe guion, hechos, medios autorizados, recursos canónicos, formato, presupuesto y preferencias de dirección. Devuelve una escaleta por unidad de sentido y ventana temporal.

Para cada toma decide qué comunica, por qué se ve eso, de dónde saldrá y cómo comprobar que es correcta. Categorías:
- USER_VIDEO: fragmento de grabación/clip aportado. Comprobar que no atribuye palabras distintas a labios visibles.
- FLOW_MAXDOTAI: nueva intervención del personaje maxDotAi a partir de su ficha y referencias reales; manual Flow por defecto.
- DOCUMENTARY: captura, clip o imagen auténtica con derechos y fuente; para demostraciones de productos reales.
- DATA_GRAPHIC: gráfico explicativo reproducible con datos exactos, SVG/animación; nunca pedir a vídeo generativo que invente cifras.
- GENERATIVE_BROLL: vídeo/imágenes conceptuales para ilustrar, sin simular evidencia de hechos reales; etiquetar recreación si pudiera confundirse.
- TITLE_CARD: titulares, nombres, fechas, rótulos, subtítulos y transiciones creados de manera programática.
- PENDING: material o autorización ausentes.
Decisión práctica: (1) ¿hay que demostrar un hecho? evidencia auténtica; (2) ¿un número exacto? gráfico programático; (3) ¿debe hablar el presentador? comprobar clip existente válido o maxDotAi; (4) ¿es abstracto? B-roll generativo justificado; (5) ¿texto exacto? tipografía programática. La variante más barata válida prevalece, pero no por encima de veracidad/continuidad.

Nunca reemplazar un vídeo original por clip de IA sin explicar que es ilustrativo. No regenerar personaje/fondo por una variación de rótulo.
8. Guion y línea de tiempo: desacoplar voz, edición y clips
El proyecto tiene tres pistas temporales sincronizadas:
1. Contenido: frases, afirmaciones, pausas, beats y marcas de énfasis.
2. Audio: pista de locución master aprobada o segmentos compatibles con marcas de tiempo; música y SFX en pistas separadas.
3. Vídeo: tomas de cámara/presentador, capturas, B-roll, gráficos y rótulos.
Un Shot puede superponerse a varios beats; un beat puede ilustrarse con varios planos. La suma de ventanas de vídeo debe cubrir el vídeo final sin huecos inesperados; el audio no se concatena sin control de ritmo, pausas, nivel e inteligibilidad. Los clips generativos usan duraciones permitidas por cada proveedor; recortar o encadenar no obliga a cortar frases.

Si se edita una palabra, se compara contenido: corrección factual vuelve a comprobar fuentes; variación retórica modifica guion y audio sin tirar el material neutro. Al cambiar duración, se recalculan sync y planos pero se reutilizan los activos independientes.
9. Compilador de prompts basado en Flow: determinista y verificable
No pedir a un LLM «escribe un gran prompt» sin plantilla estable. La IA propone ideas; el compilador combina la configuración real del proyecto en un orden fijo:

objetivo de la toma → fuente/identificador del presentador realmente confirmado → referencias adjuntables y sus IDs/hashes → escenario aprobado → relación de aspecto/capacidad del proveedor → encuadre y movimiento → actuación → diálogo literal y política de audio → restricciones de continuidad → comprobaciones.

Generar por toma prompt_en, explanation_es, negative_constraints breves, attachments_manifest, voice_mode, shot_duration, generator, provider_capabilities_verified, cost_quote, checklist. El prompt es editable; cada edición crea una revisión y conserva el origen. Si no hay mediaId/asset real, anotar falta de referencia; no escribir «attached image» si no está adjunta.

Modo Flow manual: mostrar al operador 1) qué personaje escoger en Flow; 2) qué fondo/referencias adjuntar; 3) prompt exacto; 4) aspecto/duración admitidos si confirmados; 5) checklist; 6) número de toma; 7) importación del MP4 resultante. La generación se hace por el operador si la app externa no ofrece una API verificada, sin automatizar una interfaz sin autorización ni declarar completada la tarea antes de importar el archivo.

Modo API futuro: adaptador intercambiable con pruebas reales, capacidades y precios actualizados, manejo de errores, presupuesto, consentimiento y respuesta de proveedor. Debe dar el mismo GeneratedAsset y circuito de revisión que Flow manual.
10. Biblioteca y continuidad audiovisual
Cada vídeo/foto importada se analiza con metadatos reproducibles (hash SHA-256, duración, resolución, FPS, orientación, audio, tamaño, fichero de origen) y se describe con etiquetas editables: quién aparece, plano, ambiente, iluminación, vestuario, expresión, palabras efectivamente dichas, si puede silenciarse, derechos, calidad. Una búsqueda de clips candidatos puede ser automática, pero aprobarlos corresponde al usuario.

La biblia audiovisual con revisiones bloquea maxDotAi (identidad), plató, grafismos, voz, ritmo y reglas de cámara. Un activo solo se marca APROBADO si existe, es accesible, coincide con la referencia y pasó revisión humana. Para dos ratios distintos, validar encuadre real; no recortar siempre 16:9 a 9:16 sin comprobaciones.

Para cada toma el supervisor comprueba identidad, gafas/rostro/cabello según activo real sin inventar rasgos, iluminación, ropa, plató, legibilidad, voz, lipsync, manos, fondo, continuidad de pose y relación con tomas vecinas. La inspección automática recomienda; la aprobación de identidad es humana.
11. Previsualización, gráficos y montaje
Antes de gastar en vídeo generativo, producir una animática con imágenes aprobadas o placeholders claramente DEMO, clips existentes, diseño de gráficos y voz autorizada/guía. Permitir reproducir, cambiar duración y aprobar o corregir la escaleta.

GraphicSpec registra título, afirmación vinculada, valores numéricos con unidad, fuentes, tipo de gráfico, rango/eje, formato, duración, transiciones, colores/tema, subtítulos y pie de fuente. Si cambian las cifras, invalidar el gráfico y rótulos derivados. Generar gráficos programáticamente (SVG/Canvas/Remotion según necesidad); jamás usar imagen generativa para representar datos exactos o capturas reales falsificadas.

Render final cuando están todos los materiales requeridos, el audio correcto, aprobaciones, presupuesto y derechos. FFmpeg (o motor equivalente) compone, exporta subtítulos, rótulos, audio y versiones 9:16/16:9. El producto distingue PREVIEW de FINAL. Validaciones: cobertura de timeline, formato, sincronía, sonoridad, textos correctos, cifras y fuentes visibles, ausencia de medios pendientes.
12. Programas de 5/10 noticias y reutilización
Episode contiene lista ordenada de referencias a revisiones de historias/proyectos; no copia diez noticias a un único texto sin trazabilidad. Añade intro/outro canónicos, transiciones y rótulos, calcula duración total y reutiliza medios/identidad. Permite exportar noticia individual y programa compuesto. Si se actualiza una noticia, marcar solo sus salidas derivadas para revisión; la versión publicada anterior se conserva.

Para distribuir: archivos MP4, subtítulos, miniatura, titular, descripción, hashtags solo sugeridos y citas verificables. Nunca publicación automática antes de aprobación y credenciales oficiales.
13. Datos, estados y reglas de actualización
Entidades mínimas: NewsSource, FetchRun, SourceDocument, Story, Claim, Evidence, EditorialDossier, ScriptRevision, Episode, ProductionProject, NarrationBeat, Shot, VisualBible, CharacterProfile, VoiceProfile, SetProfile, MediaAsset, MediaApproval, MediaUse, PromptPackage, GraphicSpec, GenerationJob, GeneratedTake, TimelineRevision, Render, ApprovalEvent, ProviderConfig, SecretReference, BudgetLedger, AuditEvent.

Las relaciones más importantes son Claim → Evidence, ScriptSegment → Claim, Shot → ScriptRevision/Beat/Claim/Asset, Prompt → Shot/Identity/Set/Assets/Model, GeneratedTake → Prompt/Provider, Render → TimelineRevision/Assets. Todos los resultados conservan input_hash, revisión de padres, versión de herramienta, estado, creación/modificación y autor. Las revisiones aprobadas no se editan in situ; un cambio crea revisión nueva.

Estados separados:
- Noticia: CAPTURADA | EN_REVISION | LISTA_PARA_GUION | DESCARTADA.
- Guion: BORRADOR | EN_REVISION | APROBADO | OBSOLETO.
- Toma: PLANIFICADA | RECURSO_PENDIENTE | PROMPT_LISTO | EN_PRODUCCION | IMPORTADA | APROBADA | RECHAZADA.
- Trabajo automático: EN_COLA | EJECUTANDO | ESPERA_EXTERNA | REINTENTABLE | COMPLETADO | FALLIDO | CANCELADO.
- Render: BORRADOR | PREVISUALIZACION | FINAL_PENDIENTE_QA | APROBADO | PUBLICADO.
No deducir un estado de otro: un prompt listo no significa vídeo generado. Rechazar cambios sobre una revisión obsoleta; solicitar refresco del proyecto.

Invalidación dirigida: cambio factual → dossier/guion/audio/gráfico/rótulos/tomas que dependan de ese hecho; cambio de personaje → solo tomas de presentador/prompts correspondientes; cambio de fondo → composiciones que usen ese set; cambio de ratio → crops, gráficos, rótulos y exports, sin invalidar evidencias. Nunca regenerar todo por defecto.
14. Orquestador LLM y trabajos
No crear ocho agentes conversando libremente entre sí. Construir pipeline pequeño con tareas especializadas e interfaces tipadas: ingest, cluster, extract_claims, verify_or_flag, summarize, write_script, plan_beats, assign_shots, compile_prompts, quality_check. La IA propone; verificaciones deterministas y aprobaciones deciden. Salidas estructuradas validadas con esquemas, límites de reintentos, modelos por capacidad, versiones de prompts y registro de coste.

Trabajos pesados fuera de request HTTP. Encolar persistiendo job_id, clave de idempotencia, dependencias, estado, errores, política de reintentos y resultado; bloqueos para que dos workers no ejecuten la misma toma; reanudación ante reinicio. Si un servicio externo falla, guardar progreso y ofrecer reintentar sin duplicar pagos.
15. Seguridad y configuración de APIs/endpoints
UI de configuración por proveedor: nombre legible, tipo (LLM/texto/imagen/vídeo/voz), endpoint URL validado, modelo y capacidades, prueba de conexión, estados, coste, límites, clave enmascarada, rotación/revocación. Credenciales solo en servidor, cifradas con clave fuera de DB; nunca en código fuente, localStorage, exportaciones ni logs. .env contiene valores de arranque necesarios, p. ej. conexión DB y clave maestra del almacén seguro, no un almacén editable desde web.

Prevenir SSRF al verificar URLs externas: restringir esquemas, DNS, redirecciones y destinos internos; accesos locales a Ollama/LM Studio solo mediante permitidos explícitos en entorno confiable. Presupuesto por operación/proyecto y estimated / reserved / actual; coste desconocido obliga a confirmar antes de servicios de pago. Auditar cambios de configuración y accesos.
16. UX operativa: una aplicación, no dos
Navegación superior: Inicio, Noticias, Programas, Estudio, Biblioteca, Producción, Configuración. En Estudio, mostrar las ocho pestañas originales con subtítulos claros y un panel lateral de estado: Guion aprobado, Personaje sin vincular, Fondo pendiente, 3 tomas listas, 2 clips por generar, Coste pendiente. Campos comprensibles en español, ocultando códigos técnicos en vista ordinaria.

Acción principal según estado: Revisar hechos, Crear guion, Abrir estudio, Preparar tomas, Exportar a Flow, Importar clip, Previsualizar, Aprobar, Renderizar. Mostrar bloqueos concretos, no botones que aparenten funcionar y luego no hagan nada.
17. Ejemplo de recorrido completo (ficticio y marcado DEMO)
1. Usuario añade una URL de demostración; sistema guarda fuente y estado CAPTURADA.
2. Motor extrae una afirmación y la enlaza a su fragmento; humano confirma el dossier; estado LISTA_PARA_GUION.
3. Agente propone guion breve y lo vincula al claim; humano lo aprueba por revisión.
4. Crear proyecto Short 9:16; el Estudio abre en Noticias.
5. En Personaje, el usuario elige maxDotAi, pero aún no dispone de handle confirmado: queda PENDIENTE.
6. En Fondo, selecciona referencia CRT real si existe, si no marca pendiente.
7. En Guion, se crean beats y varias tomas no rígidas; una intervención del presentador, una gráfica exacta y un plano ilustrativo.
8. En Voz, selecciona locución existente válida o deja audio pendiente; el sistema no inventa una voz ni sincronización labial.
9. En Movimiento, asigna plano de pecho, acercamiento moderado y cambio a gráfica; sin repetir glitch incesantemente.
10. En Referencias, vincula materiales reales y sus hashes; lo no aportado sigue pendiente.
11. En Resultado, se genera un GraphicSpec y un prompt separado para la toma con maxDotAi, exportable aunque la generación no sea automática.
12. Usuario crea clip en Flow y lo importa; sistema guarda metadatos, muestra comparación y permite aprobación.
13. Animática y render final solo si todos los medios y audio están aprobados; el mismo contenido puede usarse después en una edición 16:9 con recuadre revisado.
18. Pruebas de aceptación obligatorias (más que un prototipo bonito)
A1. Puedo abrir las ocho pestañas, editar cada una y cerrar/reabrir sin perder cambios.
A2. Cambiar personaje/ratio/fondo/voz/movimiento/referencias modifica de forma comprobable los prompts y planes dependientes.
A3. Una noticia importada no aparece aprobada por defecto.
A4. Una afirmación de guion enlaza a evidencia; si carece de ella se etiqueta como pendiente.
A5. El texto original puede reconstruirse sin pérdida tras descomponer beats; el audio no se corta cada 8 s.
A6. Referencia textual se distingue visual y técnicamente del medio adjunto; ningún mediaId se inventa.
A7. maxDotAi es el único personaje generativo seleccionable como presentador. No aparece NeuralDotAI como opción vigente.
A8. Sin conectividad Flow, puedo exportar prompts e importar vídeos manualmente; no aparece «vídeo generado» antes de hacerlo.
A9. Gráficas toman cifras y unidades exactas de afirmaciones aprobadas, no del modelo generativo.
A10. Al cambiar una cifra, se invalidan gráfico/rótulos/guion derivados y no el fondo o clips neutros.
A11. Mis vídeos se catalogan y reutilizan sin atribuirles diálogos diferentes.
A12. Un proyecto puede incluir 5/10 noticias y exportarlas individualmente o en programa.
A13. Puedo configurar un endpoint y probarlo; las claves jamás salen de servidor.
A14. Un trabajo fallido se reanuda sin duplicar generación/cobro.
A15. El render final falla con mensaje claro cuando falta locución, un clip requerido o una aprobación.
A16. Hay test automatizado real y un recorrido end-to-end reproducible; no se declara terminado por mostrar una pantalla.
19. Orden de desarrollo en primera ventana de 10 horas
NO prometer producto completo en 10 horas. Construir un recorrido vertical real, con Flow en el centro:
- F0 Inventario y pruebas: leer 17 archivos, extraer interacciones reales y fijar criterios de aceptación. Probar entorno/repositorio, backup y dependencias.
- F1 Persistencia común: crear proyecto nuevo, DB, migraciones, almacenamiento de activos y registros de revisiones.
- F2 Estudio Flow completo: ocho pestañas navegables con campos y validación; preferir un proyecto DEMO persistente antes que varias pantallas decorativas.
- F3 Motor creativo: guion editable, beats/tomas, biblioteca, selección de presentador, prompts reales por toma, exportación Flow manual y reimportación de clip.
- F4 Conexión editorial mínima: agregar noticia manual/URL, estados y evidencia; vincular historia al proyecto. La extracción automatizada avanzada se amplía después.
- F5 Validación: comprobar persistencia, seguridad mínima, coherencia de identidad, integridad del guion, cambios propagados, demo navegable y pruebas; documentar lo pendiente.
Condición de éxito de primera sesión: la aplicación permite crear/abrir un proyecto, recorrer los ocho pasos de Studio, modificar controles, generar un paquete de prompts coherente con la selección, exportar instrucciones de Flow, importar una toma si existe y conservarlo todo al reiniciar. La captación masiva, TTS real y render distribuido son fases posteriores, nunca funcionalidades fingidas.
20. Regla de entrega al agente
La implementación se hace desde cero, pero replica y mejora las funciones creativas recuperadas. Leer flow-recovery.rar y fuentes antes de diseñar. Marcar cada módulo Flow con prueba que demuestre su operación. Mantener tareas, decisiones y bloqueos en TASK.md. Entregar ejecutables/comandos, migraciones, tests, demo, capturas y ESTADO_REAL.md con etiquetas: FUNCIONA, PARCIAL, PENDIENTE_POR_ACTIVO, PENDIENTE_POR_API, NO_IMPLEMENTADO. No añadir agentes, servicios ni pantallas que no alimenten este flujo y no dar por hecho credenciales, voz, handle o vídeos del usuario.
Fuente de diseño auditada: flow-recovery.rar, 17 archivos TypeScript/TSX recuperados, incluidos App.tsx, types.ts, constants.ts, NewsEditorialTab, CharacterSheetTab, BackgroundTab, ScriptTab, VoiceTab, MovementTab, ReferencesTab, ResultTab, scriptAnalyzer.ts y newsDeduplication.ts. Los manifiestos verifican integridad contra el propio material aportado, no funcionamiento remoto en Flow. Los esquemas anteriores sirven solo como insumos no vinculantes; esta especificación explica el comportamiento funcional objetivo.