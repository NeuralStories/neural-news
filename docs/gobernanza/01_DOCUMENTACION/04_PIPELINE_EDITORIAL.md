# Motor editorial — desde fuentes hasta guion y planificación

## Ruta completa y puertas de control
```
FUENTE (URL/RSS/documento autorizado)
-> SNAPSHOT (HTML/texto/fecha/licencia/hash)
-> EXTRACCIÓN (titular, autor, fecha, cuerpo, referencias)
-> NORMALIZACIÓN y AGRUPACIÓN (mismo hecho vs actualización vs diferente)
-> CLAIMS (afirmación factual + citas exactas)
-> CONTRASTE (independencia fuentes/contradicciones/incertidumbre)
-> BRIEF EDITORIAL (qué/por qué/importa y límites)
-> APROBACIÓN EDITORIAL DE LA REVISIÓN
-> GUION (locución + título + piezas de formato)
-> BEATS TEMPORALES + DECISIONES VISUALES
-> PRODUCTION PLAN (gráficas, A-roll, B-roll, vídeo IA, captura)
-> ANIMÁTICA/QA/EXPORT
```
Cada flecha deja job, versión del prompt/modelo/config, estado, timestamp, coste/uso si disponible, errores; no sobreescribir etapas aprobadas sin revisión.

## Captación
1. El administrador registra feed con categoría, periodicidad, robots/condiciones, país/idioma y relevancia. RSS preferente. Recoger metadatos y texto disponible legalmente; no evadir muros.
2. URLs canónicas: quitar seguimiento conocido sin perder identificadores esenciales; respetar fragmentos/variantes y canonical declarado cuando fiable. Guardar URL original, final, redirecciones y host.
3. Fetch con timeout, límite de tamaño, Content-Type permitido, límites de redirección, DNS + IP pública verificada por conexión, no acceso a IP privada/metadata. HTTPS recomendado; solicitudes a proveedores internos van por ruta separada.
4. Guardar snapshot crudo con hash SHA-256 y fuente; si cambia crear nueva `source_revision`, jamás sobrescribir histórico. Fechas de publicación y de obtención distintas. Respetar licencia y conservar un extracto limitado para citas según derechos.
5. Extraer texto: índice de párrafos / offset y hash para poder apuntar evidencias precisas; fechas relativas, cifras y comillas exigen trazabilidad.
6. RSS repetido produce `source_item` idempotente; no crear 20 noticias iguales.

## Agrupación de noticias
Usar URL, IDs externos, coincidencia de título, entidades y fecha, similitud semántica opcional; registrar `story_grouping_reason` y confianza; ante baja confianza **proponer** en UI. Una noticia nueva sobre actualización posterior mantiene relación (`updates_story_id`) sin eliminar hechos previos. Una copia sindicada de la misma nota no es evidencia independiente.

## Extracción y validación factual
Objeto `Claim`: texto atómico, tipo (dato/fecha/cita/atribución/proyección), validación (`SUPPORTED`, `DISPUTED`, `UNVERIFIED`, `REJECTED`), `evidence_links[]` con `source_snapshot_id`, `snippet_id`, cita/posición y `independence_group_id`; ninguna afirmación nace con `SUPPORTED` por salida de LLM. Hechos contrarios se presentan en columna de conflictos. La ausencia de fuente no se «arregla» redactando con seguridad.

**Reglas particulares para noticias IA:** distinguir demo, anuncio, disponibilidad real, release oficial, rumor, repositorio, benchmark, precio, jurisdicción, usuarios elegibles y modelos retirados. Comprobar fecha del artículo y fecha del hecho. Si se compara rendimiento, registrar hardware, prueba, unidad y metodología.

## Brief editorial
Campos: titular provisional, resumen de 70–120 palabras como recomendación inicial, por qué importa (1–3 puntos), qué cambió respecto al estado anterior, afirmaciones soportadas con IDs, contradicciones, cautelas, nota para lector, enfoque deseado, formato, audiencia, idioma castellano de España. No usar longitud como garantía de calidad.

## Guion y programa
`ScriptRevision`: `story_id`, `approved_brief_revision`, `narration_text`, `hook`, `body`, `closing`, `word_count`, `estimated_sec`, `pronunciation_notes`, `source_claim_ids[]`, `channel_format` (short/vertical, explainer/horizontal, bulletin), `revision_hash`, `review_state`, `reviewed_by`.
- Las frases deben tener correspondencia con `claim_ids` cuando comuniquen hechos.
- Sin frases cebo engañosas, abuso de superlativos ni cifras inventadas. Crear versiones A/B de enfoque sin duplicar investigación.
- Para 5/10 noticias se eligen historias aprobadas y se decide orden/puentes sin alterar hechos. Titulares y despedida pueden ser edición separada.

## Locución y duración
El viejo prototipo asumía 2,85 palabras/s (= 171 ppm) y 8s. Usar esos valores **solo como referencia histórica, no default universal**. Configuración por perfil: `target_wpm` configurable, estimación inicial `words / target_wpm * 60 + pauses_seconds`; calibrar con muestras de voz autorizada. Ejemplo DEMO: 125 palabras a 150 ppm = 50s sin pausas; con 3s = 53s. Cortes de vídeo de 4/6/8s pueden cubrir porciones sin cortar la pista continua. Toda edición de guion invalida la locución dependiente y el subtítulo, no necesariamente el B-roll independiente.

## Estados y aprobaciones
`CAPTURED -> EXTRACTED -> GROUPED -> CLAIMS_PENDING -> REVIEW_REQUIRED -> EDITORIAL_APPROVED -> SCRIPT_DRAFT -> SCRIPT_APPROVED -> PLANNED -> PRODUCTION_REVIEW -> READY_TO_RENDER -> RENDERED -> FINAL_QA -> EXPORT_READY`. Estados `FAILED/BLOCKED` transversales con motivo legible. Cambiar afirmación o fuente usada invalida brief/guion/aprobaciones dependientes. Aprobar requiere rol y revisión exacta; PUT con `expected_revision_hash`, 409 si divergente. Los editores pueden dejar nota y corregir manualmente, preservando historia.

## Resultados mínimos del primer ciclo
Con una fuente DEMO claramente marcada, guardar snapshot y claim; operar manualmente editor->guion->plan; persistencia real PostgreSQL; respuesta de modelo fake solo con etiquetado `DEMO`; aprobaciones sin autopromoción, reabrir y mantener versiones; API para introducir URL real autorizada si el tiempo lo permite.
