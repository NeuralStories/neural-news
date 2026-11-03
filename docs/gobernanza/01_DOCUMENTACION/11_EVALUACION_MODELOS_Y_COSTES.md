# Evaluación de modelos, dimensionamiento, costes y eficiencia

## Selección objetiva
Cada tarea LLM tiene: `role` (extractor, analyst, verifier_assistant, writer, director, prompt_compiler), versión de prompt, schema, `max_input_tokens`, `max_output_tokens`, timeout, modelo y ruta. Ejecutar los mismos **30 casos** (ver QA) para cada modelo y guardar resultados sin secretos. La evaluación combina validación de JSON, citas, precisión factual revisada, completitud de guion, tiempo y coste; no comparar dos modelos con prompts/datasets diferentes y afirmar ganador sin evidencia.

## Valores derivables, no precios inventados
- **Duración de locución:** `T = words * 60 / actual_wpm + sum(pauses_seconds)`; `actual_wpm` se calibra con audio aprobado. Ejemplos: 75 palabras / 150 ppm = 30 s; 125 palabras / 150 ppm = 50 s; + 3 s pausas -> 53 s.
- **Cobertura de tomas:** `sum(shot_duration_seconds) >= video_duration_seconds`; permitir superposición/transiciones pero no huecos sin salida audiovisual. Ej. pieza 53 s y clips disponibles de 8 s => 7 tomas cubrirían 56 s antes de recorte; ello **no significa 7 generaciones** si varios tramos se cubren con gráficos o vídeos reutilizados.
- **Planificación 5 noticias:** si cada una dura 53 s, son 265 s (4 min 25 s) antes de intro, separadores y cierre. **10 noticias:** 530 s (8 min 50 s) antes de elementos adicionales. Son cálculos DEMO, no objetivo obligatorio de duración.
- **Tokens:** `cost_llm = input_tokens/1_000_000 * input_price_per_million + output_tokens/1_000_000 * output_price_per_million` (moneda y modalidad del proveedor). Si precio desconocido => `UNKNOWN`, nunca suponer cero.
- **Generación vídeo:** `cost_video = sum(actual_billable_units_i * verified_unit_price_i)`; las unidades pueden ser segundos, vídeo o créditos. No usar constante global por 8s: los modelos y planes cambian.
- **Rendimiento real:** `total_critical_path = ingestion + analysis + approval_wait + script + assets + generation + render + QA`, aplicando paralelismo solo si no rompe dependencias/seguridad. Latencia de proveedor real se mide, no se presume.
- **Ahorro por caché:** `avoided_spend = sum(cost_would_have_been_repeated for valid reused artifacts)`, contabilizado como estimación contrafactual, separado de gastos reales.

## Tres escenarios de planificación por noticia (números ilustrativos, no mediciones)
A. **100% programático sin vídeo IA:** animática y gráfico SVG, coste monetario de API de vídeo = 0 (no incluye CPU, almacenamiento, trabajo, TTS/LLM).
B. **1 clip IA:** coste video = una operación facturable según tarifa real + edición local.
C. **3 clips IA:** coste de 3 operaciones + posibles iteraciones fallidas. Un clip fallido también puede facturar, verificar antes de solicitar 3 variaciones.

No fijar presupuesto en euros como dato universal: la cuenta/plan/mercado no están proporcionados. El panel mostrará euros estimados solo si existe tarifa/cambio comprobado. Presupuesto inicial **0** hasta autorización. Los reintentos no garantizan gratuidad.

## Métricas de calidad y eficiencia
- `% claims apoyados`, `% discrepancias revisadas`, `% escenas con recurso aprobado`, `% tiempo cubierto con media reutilizable`, `% errores de subtítulo/cifra`, `coste real por noticia`, `tokens por etapa`, `latencia P50/P95`, `tasa de regeneraciones`, `% prompts con referencias reales`, `ratio de aprobaciones rechazadas`.
- Umbrales de aceptación obligatorios: 0 costes no autorizados, 0 secretos en salida, 0 cifras «verificadas» sin evidencia, 0 ficticios representados como reales. Para velocidad/calidad visual no establecer porcentajes falsamente basados en prototipo.

## Evaluaciones A/B
Prompt A vs B bajo misma entrada, modelo y límite. Guardar `prompt_version`, `model_version`, `config_hash`, resultado, anotación de editor, si fue aprobado y motivos. Aprendizaje de preferencias **solo si el administrador lo aprueba**; no convertir cada rechazo en regla universal.

## Licencias y disponibilidad
Remotion tiene licenciamiento específico para empresas y automatización; revisar elegibilidad al introducirlo. Flow y Gemini no son sinónimos de API: la UI de Flow permite `@` e ingredientes; automatización externa dependerá del proveedor oficial actual y de permisos. La documentación oficial de Gemini al 30/10/2026 informa retirada de Veo 3.1 Preview el 22/10/2026 y dirige a Gemini Omni Flash u opciones GA. Next.js tiene avisos graves en octubre 2026; instalar una versión mantenida/parcheada y verificar advisories al fijar lockfile.
