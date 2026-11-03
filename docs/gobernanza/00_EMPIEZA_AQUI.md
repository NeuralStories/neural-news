# NEURAL.NEWS — ENTREGA ÚNICA PARA EL AGENTE

**Fecha de corte: 2026-10-30.** **Estado: especificación y evidencia auditada; desarrollo nuevo aún NO ejecutado.**

## ÚNICA FUENTE DE INSTRUCCIONES
Este directorio sustituye y **anula íntegramente** todos los Planes Maestros, backlogs y prompts anteriores. No debes importar ni combinar sus tareas, versiones o recomendaciones. Las fuentes del prototipo Flow adjuntas son **evidencia técnica de solo lectura**, no código del nuevo producto.

## Qué se pretende construir
Una **única plataforma** neural.news capaz de ejecutar: fuentes autorizadas/RSS/web -> recuperación y conservación de evidencias -> agrupación de hechos y contraste -> edición/selección -> guion y locución -> escaleta audiovisual por frase -> selección de MaxDotAi o vídeos aportados -> generación visual/B-roll/gráficos dinámicos -> animática -> paquete Flow / render cuando exista acceso real -> QA -> exportación/agrupación de 5 o 10 noticias. Todo persistente en PostgreSQL y configurable por panel (APIs, endpoints, modelos, presupuesto) sin exponer secretos.

## Lee en este orden
1. `01_DOCUMENTACION/01_PLAN_MAESTRO.md` — producto completo, límites, secuencia y definición de terminado.
2. `01_DOCUMENTACION/02_AUDITORIA_FLOW.md` y `03_EVIDENCIA_FLOW/reports/` — qué aporta realmente el RAR y qué no acredita.
3. `01_DOCUMENTACION/03_ARQUITECTURA_Y_TECNOLOGIA.md` — elecciones técnicas y alternativas.
4. `01_DOCUMENTACION/04_PIPELINE_EDITORIAL.md` y `05_PRODUCCION_Y_MAXDOTAI.md` — especificación funcional exhaustiva.
5. `01_DOCUMENTACION/06_DATOS_APIS_CONFIG.md`, `07_UX_Y_PANTALLAS.md`, `08_SEGURIDAD_Y_OPERACIONES.md`, `09_QUALITY_GATES.md`.
6. `01_DOCUMENTACION/10_EJECUCION_10_HORAS.md` + `06_TASKS/BACKLOG.csv`; cada tarea incluye evidencia de terminación.
7. `01_DOCUMENTACION/11_EVALUACION_MODELOS_Y_COSTES.md`, `12_REGISTRO_DECISIONES_Y_RIESGOS.md`, `13_FUENTES_EXTERNAS.md`.
8. `02_CONTRATOS/*.schema.json` + `05_EJEMPLOS/*`; después ejecuta `04_OPERACION/validar_paquete.py`.
9. `PROMPT_UNICO_PARA_AGENTE.md`: **copia solo este mensaje al agente**, con todo este directorio accesible.

## Contenido suministrado
- `03_EVIDENCIA_FLOW/flow-recovery.rar` original intacto; material `source/`, `reports/` y `README_RECUPERADO.md` extraído con procedencia comprobada contra manifiesto interno. No ejecutar extractor ni `flow-sdk` sin revisión y autorización.
- Plan Maestro nuevo, tecnologías, sistema de producción, contratos, evaluación, instrucciones de arquitectura.
- Backlog nuevo e independiente; NO utilizar IDs históricos N-xxx.
- Contratos JSON Schema y ejemplos de demostración, pruebas de integridad y manifiesto de archivos.

## Entrega esperada tras 10 horas
Un **primer recorrido vertical real y verificable**, no 100 módulos de escaparate. Debe permitir crear/ingestar fuente de prueba, almacenar evidencia, generar o editar una ficha con afirmaciones trazadas, pasar a guion y plano visual, seleccionar tipo de toma, construir al menos un gráfico con cifras DEMO exactas, emitir un paquete Flow MANUAL completo, guardar/reabrir, mostrar errores y recuperar un trabajo. Los conectores de pago o de Flow que no estén acreditados serán `BLOCKED`/`MANUAL`, nunca `DONE`.

## Prohibiciones
No reutilizar prototipo como base de código. No fabricar MaxDotAi ni sustituirlo por otro. No acceder a tu cuenta Flow ni a vídeos privados sin permisos. No gastar créditos, publicar, generar vídeos o usar servicios pagos sin autorización. No registrar un hecho como verificado porque un LLM lo diga. No introducir secretos reales en Git ni exponer `.env` al navegador. No afirmar que las diez horas permiten terminar el producto completo.
