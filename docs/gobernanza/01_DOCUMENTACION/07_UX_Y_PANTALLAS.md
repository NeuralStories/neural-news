# Producto y UX/UI — única aplicación española

## Principios
Un usuario no debe ver contratos, Idempotency-Key, HTTP 422, schemas, unions ni nombres de tablas. Tampoco diez menús derivados de prototipos. Interfaz en castellano de España, lenguaje natural, opciones visibles según estado, persistencia inmediata y evidencia de que se guardó. Navegación consistente desktop/tablet/móvil, focus visible, etiquetas de formularios, WCAG 2.2 AA objetivo. Panel oscuro/neutral con diseño broadcast solo en área de vídeo; el resto necesita máxima legibilidad, sin pantallas saturadas de brillos.

## Mapa de navegación propuesto
1. **Inicio**: pendientes editoriales, trabajos en curso, costos previstos, errores accionables y últimos resultados.
2. **Fuentes**: feeds, captaciones, dominio, frecuencia, fallos, derechos y filtros.
3. **Noticias**: bandeja de historias agrupadas; estado factual, fecha, origen, diversidad de fuentes; detalle con claims/evidencias y decisiones.
4. **Producción**: proyecto central con pestañas **Guion | Dirección | Recursos | Gráficos | Animática | Exportación** sin perder contexto. La noticia y versión permanecen visibles siempre.
5. **Programas**: episodios/bloques de 5 o 10 noticias, orden y tiempo de duración.
6. **Biblioteca**: personaje `maxDotAi` y vídeos autorizados, platós, voces, clips, derechos, aprobaciones, hashes.
7. **Configuración**: conexiones/modelos, fuentes de gastos, presupuestos, trabajos, usuarios, backups y diagnósticos.

## Pantalla esencial «Noticia → Producción»
Cabecera: titular, fecha y revision; izquierda evidencia/guion; centro timeline de beats y planos; derecha propiedades de elemento (tipo vídeo, referencia, prompt, cámara, costo). Arriba indicadores «Guion aprobado», «Fuentes pendientes», «MaxDotAi sin vincular», «Coste pendiente», «3 planos por generar». El usuario puede aceptar, corregir y reordenar; no se ocultan datos por fases.

## Edición del guion
Mostrar texto legible; clic frase -> evidencia y plano que la cubren; «Ver fuente», «Editar frase», «Proponer alternativa», «Aprobar esta versión», «Crear dirección visual». La UI avisa: «Esta cifra se usa en dos gráficos y tres rótulos; habrá que revisarlos». El botón de aprobar opera `expected_revision_hash` y al conflicto muestra «Hay una versión más reciente. Revísala antes de aprobar».

## Selector de plano
Opciones: «Usar un vídeo mío», «Generar con maxDotAi en Flow», «Gráfico animado», «Recurso de la noticia», «Vídeo ilustrativo», «Rótulo», «Pendiente». Si recurso ausente, «Falta seleccionar un vídeo aprobado». Si Flow no disponible «Preparar instrucciones para Flow» en vez de «Generar automáticamente». Si coste no está autorizado, «No se puede iniciar: falta permiso de gasto».

## Panel Configuración
Conexiones: nombre, tipo (OpenAI-compatible local/externo, proveedor oficial), endpoint, modelo, propósito, timeout, concurrencia, test de conexión, estado y fecha de última comprobación; API key campo de **sustitución** que nunca se vuelve a mostrar. Presupuestos 0 = cero llamadas pagadas, estados de work. `.env` de arranque no es editor web. Permitir guardar revisiones y volver a configuración anterior (sin exportar secretos).

## Flujo de primera apertura
1. Asistente «Configurar instalación» admin local + PostgreSQL + almacén.
2. Marcar `DEMO` si no hay APIs; cargar noticia sintética sin fuentes engañosas.
3. Abrir pieza demo y recorrer editor/guion/dirección/gráfica/Flow manual.
4. Importar vídeo real (opcional) para comprobar montaje y validación.
5. Pantalla «Sistema listo» solo cuando DB, worker, auth y prueba guardado estén OK.

## Errores obligatorios
403 «No tienes permiso para cambiar esta conexión». 409 «La noticia ha cambiado. Revisa la versión». Sin medios «Todavía no has subido un vídeo aprobado del presentador». Fuente bloqueada «No podemos recuperar esta página de manera autorizada; añade otra fuente o adjunta el documento». Fallo proveedor «La conexión falló. Revisa endpoint, clave o disponibilidad» con detalle técnico solo en logs de admin.

## QA de UX
390 px móvil sin scroll horizontal para flujos básicos, teclado completo, movimiento reducido, contraste, subtítulos visibles, timeline navegable por lista para lectores de pantalla, validación de ratio (9:16/16:9) en previas, estado persistente después de refresh, no save fantasma, por defecto se ve qué es `DEMO`.
