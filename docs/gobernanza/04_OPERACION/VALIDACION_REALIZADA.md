# Validación de este paquete (30-10-2026)

**Hechos que SÍ se han comprobado en este entorno:**
- RAR original disponible y SHA-256 `29f15305cd1fb17b2bb00f99699808810aa74f529e12e86e04f590fbeb5cc6b7`.
- Los 17 archivos fuente recuperados coinciden con el manifiesto de extracción local de Flow por SHA-256 y longitud. Eso no prueba compilabilidad, compatibilidad SDK ni acceso a la cuenta actual.
- El backlog nuevo tiene **106 tareas**: 23 A, 38 B, 25 C y 20 D. IDs y dependencias existentes y sin referencias hacia tareas futuras.
- De las 23 tareas A, 18 son `CORE` estimadas en 590 minutos (9h50m) y 5 `STRETCH` en 175 minutos; CORE tiene dependencias internas cubiertas. Son estimaciones, no horas ejecutadas.
- Cinco JSON Schemas Draft 2020-12 y cinco ejemplos DEMO han pasado validación `jsonschema` y formatos, incluidos texto continuo reconstruido, identidad pendiente y modo Flow MANUAL `NOT_EXECUTED`.
- Matriz de 40 casos de pruebas redactada, estados iniciales `NOT_RUN`.

**NO se ha ejecutado en esta auditoría:** nueva app, migraciones, PostgreSQL, generadores externos, TTS, montaje, pruebas de UI y QA del producto nuevo. El paquete es plan+evidencias+contratos, no programa desarrollado. Tampoco se ha accedido en directo a la cuenta privada Flow ni se dispone de medios de MaxDotAi.

**Comando de reproducción:** `python 04_OPERACION/validar_paquete.py` desde la carpeta de entrega (paquete `jsonschema` necesario para todas las validaciones; el script indica `NOT_RUN` si falta).
