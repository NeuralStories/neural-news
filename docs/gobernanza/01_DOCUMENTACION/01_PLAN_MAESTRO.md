# Plan Maestro de Construcción Inicial — neural.news

## 0. Mandato, alcance y verdad operativa
Este documento define una **construcción nueva** con un solo repositorio y una sola aplicación. Las pantallas y funciones de Flow recuperadas sirven para recuperar reglas de producción, no para trasladar una aplicación. Ninguna decisión del Plan Maestro previo mantiene autoridad. Cualquier divergencia se registra en un ADR nuevo, nunca se resuelve improvisando.

### Propuesta de valor
De una noticia a **un paquete audiovisual reproducible y verificable**, reutilizable para Short, Reel, vídeo explicativo 16:9 y bloque informativo de 5/10 noticias. Editar un hecho debe señalar todos los rótulos, escenas y locuciones dependientes; regenerar solo lo necesario. El sistema no sustituye el juicio editorial ni finge conexiones no existentes.

### Actores y roles
- Administrador: configura proveedores y límites, aprueba identidad y medios, revisa seguridad.
- Editor: selecciona historias, comprueba fuentes, revisa afirmaciones, aprueba versión de guion.
- Realizador: bloquea perfil de plató/personaje, ajusta escenas, encuadres, recursos y gráficos, aprueba animática.
- Operador: controla trabajos y montaje; no ve secretos.
- Sistema: ingiere, propone, valida esquemas, ejecuta tareas programables; **no autoaprueba hechos ni publica por defecto**.
Primer corte: administrador único con control de acceso ya preparado para más roles, no crear permisos ficticios.

## 1. Objetivos funcionales y aceptación final
**P1 — Captación responsable.** Registro de RSS, URLs individuales, comunicados y documentos, con título, URL canónica, fecha de publicación y captura, autor, idioma, licencia, texto bruto guardado y hash, política robots/condiciones. Evitar paywalls y acceso no autorizado. El artículo original no se reescribe sin procedencia.

**P2 — Criterio periodístico.** Un `Story` agrupa varias fuentes; detecta duplicados reales; un `Claim` contiene afirmación, nivel de evidencia, citas precisas y contradicciones. Una fuente de la misma nota replicada no constituye verificación independiente. Distinguir comunicado, declaración, rumor, análisis y confirmación externa. Registrar `unknown`, `disputed`, `supported`, `rejected`. No transformar «se anuncia» en «ya funciona».

**P3 — IA asistida, no omnisciente.** Modelos por tarea: extracción estructurada, deduplicación semántica, resumen, reclamaciones, contrastación asistida, redacción, escaleta, prompts. Salidas JSON con validación de esquema más validación semántica; citas que remitan a fragmentos almacenados. Preservar citas y atribuciones. Permitir versión manual si no hay API.

**P4 — Un guion y múltiples formatos.** Texto principal aprobado con beats temporales; versiones y revisiones independientes para locución, copy de subtítulos, titular, descripción social, miniatura y 9:16/16:9. Cambios no sobrescriben aprobaciones anteriores. Ritmo ajustable, cálculo inicial por palabras, corrección con TTS o lectura real.

**P5 — Dirección visual con continuidad.** Cada beat puede cubrirse con A-roll del presentador, B-roll auténtico, B-roll generativo, captura real, gráfica de datos, rótulo o mezcla. Registrar *por qué* se selecciona, qué referencias tiene, qué datos soporta, qué archivos se requieren y qué costo puede implicar. MaxDotAi o vídeos del usuario exclusivamente para presentador.

**P6 — Biblioteca canónica.** Videos, audio, fotogramas, fondo CRT, hoja de personaje, preset de cámara, perfil de voz y prompts, con `owner`, checksum, versión, licencia, fecha, resolución, orientación, duración, estado `pending/approved/rejected`, quién aprobó y compatibilidad. No asumir que URLs genéricas del prototipo son aprobadas.

**P7 — Gráficos programáticos.** Series temporales, barras, comparativas, porcentajes, cronología, mapas conceptuales (sin cartografía engañosa), diagramas y tarjetas numéricas: datos tipados, unidades, fuentes, escala, easing, duración, zona segura, transición; no generar texto numérico dentro de imágenes de IA cuando la exactitud sea necesaria. Animática de bajo coste antes del render definitivo.

**P8 — Producción.** Un `ProductionPlan` versionado explica audio, tiempos, tomas, efectos, subtítulos, gráficos, prompts, dependencias y estado por activo. Exportar un paquete para Flow **manual** desde la primera etapa. Adaptadores API reales solo donde la documentación oficial y credenciales/autorización lo respalden. Nunca derivar la existencia de API de que `flow-sdk` aparezca en código incrustado de Flow.

**P9 — Ensamblaje.** Generación de audio autorizada o importación, montaje temporal determinista, export MP4 1080x1920 y 1920x1080 cuando medios y licencias lo permitan. Metadatos, miniaturas y subtítulos. Identificar explícitamente «animática», «vídeo DEMO» y «vídeo final».

**P10 — Lotes/episodios.** Selección y orden de 5 o 10 noticias; intro, sumario, separadores, cierre, duración y proporción coherente; regeneración parcial sin rehacer el lote entero; controles editoriales por noticia.

**P11 — Administración.** Panel en castellano para configurar endpoints, API keys, rutas por tarea, prioridad, presupuesto máximo, conexiones locales/remotas, comprobaciones, logs sanitizados y versionado; `.env` solo arranque/infraestructura.

**P12 — Operabilidad.** PostgreSQL + migraciones, trabajos y estados durables, reintentos idempotentes, limitación de consumo, backup restaurable, tests y auditoría; UI única y usable con teclado/móvil; separar endpoints públicos de privados.

## 2. No objetivos de las primeras diez horas
Ni publicación autónoma en YouTube/Spotify/TikTok, ni acceso automático a cuentas Flow privadas, ni generación de cientos de clips, ni entrenamiento de un avatar ni clonación de voz, ni sistema multiempresa completo, ni ingestión masiva de sitios que prohíban extracción, ni garantizar vídeo IA coherente sin medios reales. Preparar contratos y límites, dejar `BLOCKED` cuando proceda.

## 3. Arquitectura lógica
```
[Panel web único] ---> [API dominio]
                         |-> fuentes -> documentos -> historias -> afirmaciones/evidencias
                         |-> guiones/versiones -> beats -> planes de plano -> prompts
                         |-> librería medios/identidades -> proyectos/lotes
                         |-> proveedores/modelos/config/secretos/auditoría
                         |-> trabajos idempotentes -> trabajadores
                         V
                   [PostgreSQL]   [almacén privado de ficheros]
                                       |
                        [animática/FFmpeg/gráficas/paquetes manuales]
                                       |
                             [exportación y QA final]
```
Separar dos flujos que se enlazan por datos: editorial (exactitud) y audiovisual (realización); **no dos aplicaciones**. El contrato `ProductionPlan` conecta ambos.

## 4. Etapas del producto
- **Etapa A (10 horas):** estructura limpia + DB + configuración mínima + ruta vertical con fixtures verificados como DEMO + selector MaxDotAi/pending + empaquetado manual Flow + gráfico simple + UI integrada + tests esenciales.
- **Etapa B:** captación RSS real, políticas por dominio, deduplicación robusta, evaluaciones de LLM, escaleta editable, biblioteca multimedia y animática.
- **Etapa C:** render y audio real autorizados, reintentos, gráficos avanzados, distribución 9:16/16:9 y 5/10 noticias, observabilidad y calibración de costes.
- **Etapa D:** conectores externos comprobados, generación de vídeo a escala, selección inteligente de recursos y publicación con aprobación humana.
El alcance total del backlog **no** equivale al alcance de las 10 horas.

## 5. Definiciones no negociables
- `DONE`: código implementado, prueba ejecutada, evidencia registrada, persistencia tras reinicio, UI real o endpoint real, no secreto expuesto.
- `MANUAL`: paquete para uso humano, no llamada automática.
- `MOCK/DEMO`: solo datos de demostración, identificados visualmente y en DB.
- `BLOCKED`: falta permiso, medios, cuota o credencial.
- `QA-APPROVED`: estado editorial para una versión inmutable y sus claims; no certifica la realidad absoluta.
- `final`: media existente, reproducible y validado con ffprobe/archivo, medios autorizados, sin claims contradictorios.

## 6. Métricas de producto (objetivos de aceptación propuestos, no resultados)
- 100% de afirmaciones factuales publicables con al menos una cita comprobable; las disputadas visibles.
- 0 aprobaciones arrastradas a versión nueva de guion o gráfico dependiente modificado.
- 100% de cifras de gráficos derivadas de datos tipados revisables, no dibujadas por IA.
- 0 servicios de pago ejecutados si presupuesto de trabajo = 0.
- 0 presentadores inventados si falta material de MaxDotAi.
- 100% de tareas aprobadas con pruebas registradas (no exigir 100% de tareas implementadas).
- 0 secretos en frontend/exportación/logs.
- Recuperación demostrada de trabajo interrumpido y DB de prueba.

## 7. Criterio de producto completo, posterior a 10h
Una noticia externa autorizada desde URL y una segunda fuente contrastan -> editor revisa -> se guarda guion -> escaleta con gráfica + material autorizado/pendiente -> animática -> export Flow -> import vídeo real autorizado -> montaje/verificación -> descarga. El mismo contenido produce 9:16 y 16:9; un cambio factual invalida exactamente sus dependencias. Un lote de 5 o 10 reutiliza las piezas individuales.
