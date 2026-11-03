# Decisiones arquitectónicas, supuestos, riesgos y pendientes del propietario

## Registro ADR — decisiones iniciales aprobadas por especificación (sujetas a evidencia)
- ADR-001 Construcción nueva; archivos anteriores NO son arquitectura ni tareas ejecutables.
- ADR-002 Aplicación única con módulos verticales; API y worker reutilizan dominio.
- ADR-003 PostgreSQL primario, Alembic y media externo al web root.
- ADR-004 Modo documental/factual y audiovisual separados por contrato, misma UI y DB.
- ADR-005 MaxDotAi / vídeos del usuario como únicas fuentes del presentador; sin sustitutos.
- ADR-006 Flow MANUAL por defecto; API programática solo tras comprobación oficial.
- ADR-007 Información procedente de web como dato no confiable; aprobación por revisión.
- ADR-008 Gráficos exactos programáticos, no números escritos por vídeo IA.
- ADR-009 Rutas/modelos/secretos configurables desde panel; `.env` solo infraestructura.
- ADR-010 No gasto ni publicación por defecto.
- ADR-011 Video IA en worker con control de coste, capacidades, idempotencia y provenance.
- ADR-012 No usar sistema multiagente complejo antes de probar necesidad; fases especializadas con contratos.
- ADR-013 Versionado y hashes de artefactos + invalidación selectiva.
- ADR-014 Producto inicial por recorrido vertical; no pantallas vacías.
- ADR-FLOW-001 Reintegración de la lógica de Flow (Studio 8 pasos) en `apps/web`, condicionada a auditoría diferencial previa (ver detalle).
- ADR-015 Repositorio único de destino: `neural-news`; el repo hermano `neuralnews` es fuente de funcionalidades reutilizables (media library ffprobe, importación Flow, gráficos, CAS), no un segundo producto.

### ADR-FLOW-001 — Reintegración de la lógica de Flow en neural-news (31/10/2026)

- **Autor / fecha:** sesión ZCode con revisión del propietario del 31/10/2026. **Estado:** ACEPTADA — condición de entrada resuelta; **F0 superado** el 31/10/2026 (verificación del propietario + evidencias en `03_EVIDENCIA_FLOW/revision_unificacion/F0_MANIFIESTO_EVIDENCIAS.md`). F1–F5 autorizadas sin nueva aprobación por fase.
- **Decisión.** Reintegrar la lógica de Flow eliminada (NeuralStories Studio, 17 fuentes TS/TSX verificadas) en `neural-news/apps/web` como módulo `/estudio`, con persistencia en PostgreSQL vía API (una sola fuente de verdad), adaptador de runtime local para `flow-sdk` (hosted/manual), compilador de prompts determinista y `FlowManualPackage`. Especificación rectora: `NEURAL_NEWS_LOGICA_COMPLETA_PARA_AGENTE.md`. Tarea de seguimiento única: NN-107 (`16_PLAN_MAESTRO_REINTEGRACION_FLOW.md`, rev. 3).
- **Condición de entrada (RESUELTA).** La auditoría diferencial F0 comparó los tres árboles con evidencia material: (a) repo activo, (b) 17 fuentes de Flow, (c) `REVISION_UNIFICACION_NEURAL_NEWS.zip` — aportado por el propietario y **verificado por SHA-256** (`d710c9f8…1d70c`; 226 entradas con `apps/studio`, página iframe `/estudio`, los 6 componentes pendientes y `services/av_render.py`). Resultado: **12 idénticas + 5 modificadas + 0 ausentes** (confirmado por hash), 5 módulos de API exclusivos del ZIP, contrato `production_handoff.v1` con consumidor probado en ambos lados, 7 tests exclusivos y 11 hallazgos reproducibles documentados con causa localizada. Matriz definitiva: `17_MATRIZ_DIFERENCIAL_DEFINITIVA.md`.
- **Decisión de repo único (ADR-015).** Destino: `neural-news`. El repo hermano `neuralnews` queda como fuente de funcionalidades reutilizables, no como segundo producto.
- **Alternativas rechazadas.** (1) Puerto directo sin auditoría: riesgo de pérdida funcional y de repetir una integración ya existida (veredicto del propietario). (2) Construcción desde cero ignorando código previo: contradice el mandato y desperdicia trabajo verificado. (3) Mantener dos interfaces/estados: la ejecución del 29/10 lo demostró (dos aplicaciones, verificación inflada, handoff importado ≠ pieza activa).
- **Trade-off.** La auditoría diferencial añadió trabajo a F0 y pospuso F1; a cambio se conocen los costes reales de portabilidad (2 modelos + migración + router `av.py`), las causas localizadas de los fallos heredados y se evita duplicar Neural News.
- **Test de rollback.** Backup verificable del repo activo creado antes de cambios estructurales: `backups/neural-news-pre-NN107-F0-20261031.zip` (SHA-256 `c08d99b4…77d69d`, 189 ficheros, manifiesto adjunto) + rama de trabajo en F1; evidencia `03_EVIDENCIA_FLOW/` inmutable; la implementación anterior solo se elimina tras acreditar equivalencia con pruebas funcionales de las funcionalidades migradas.
- **Riesgos asociados:** R-15, R-16.

## Matriz de riesgos
| ID | Riesgo | Prob./impacto cualitativo | Mitigación / trigger |
|---|---|---|---|
| R-01 | Flow interno no automatizable externamente | Alta / alta | `FlowManualPackage`; verificar documentación/permiso antes API |
| R-02 | Material MaxDotAi no disponible | Alta / alta | estado PENDING_ASSET, bibliotecas de vídeo sin simulación |
| R-03 | Editorial inventa hechos | Alta / crítica | claims por evidencia, 30 casos, aprobación humana |
| R-04 | Cifra de gráfico falsa | Media / alta | GraphicSpec de claim; test numérico |
| R-05 | Exfiltración API keys por SSRF/prompt | Media / crítica | segmentación redes, allowlist, políticas, logs sanitizados |
| R-06 | Gastos IA inesperados | Alta / alta | presupuesto default 0, capacidad y coste confirmado, operación idempotente |
| R-07 | Cambios en versiones proveedor | Alta / media | modelo configurable, prueba de conexión, adaptador por API |
| R-08 | Doble cobro por reintento | Media / alta | operación externa con reconciliation, no repetir UNKNOWN |
| R-09 | RAR extraído no compila | Alta / baja | solo referencia; código nuevo |
| R-10 | Feeds restringidos por condiciones | Media / media | RSS oficial y políticas, alternativa manual |
| R-11 | Pretender completar las 106 tareas nuevas en 10h | Alta / crítica | backlog nuevo, primera etapa solo recorrido completo |
| R-12 | Despliegue prematuro | Media / crítica | G6 y autorización humana obligatoria |
| R-13 | Derechos de clips del usuario ambiguos | Media / alta | ficha derechos + aprobación asset |
| R-14 | Git usado para almacenar secreto o media personal | Media / alta | gitignore, escaneo y almacenamiento privado |
| R-15 | Dos builds paralelos del mismo spec (`neuralnews` y `neural-news`) e integración anterior (ZIP 29/10) no localizada | Alta / alta | **Mitigado 31/10:** ZIP recibido y verificado (SHA-256), ADR-015 fija repo único; auditoría diferencial F0 superada con matriz definitiva |
| R-16 | Pérdida de funcionalidad útil al sustituir la integración anterior | Media / alta | Matriz diferencial con decisiones REUTILIZAR/ADAPTAR/FUSIONAR/SUSTITUIR/PENDIENTE; pruebas de equivalencia antes de eliminar nada |
| R-17 | Congelar el repo hermano sin portar sus capacidades ⇒ pérdida de cámara, backup verificable, vault, subtítulos, rutas de modelo y Argon2id | **Alta / alta** | **Mitigado 01/11:** hermano archivado y sellado (`archive/neuralnews-20261101/` + `backups/MANIFIESTO_ARCHIVE_neuralnews_2026-11-01.txt` + bundle verificado); tabla de decisión de 9 capacidades en el plan rector §6-Fase 7, cada port con test de equivalencia (NN-117) |
| R-18 | Migrar el trabajo pesado a la cola rompe el flujo actual de la UI (los handlers devolvían JSON directo) | Media / alta | El polling de trabajos **ya existe** en el frontend (`lib/hooks.ts`); el handler pasa a `202 + job_id` con el mismo esquema de respuesta; E2E del recorrido en la Fase 3 |
| R-19 | Arreglar sin cerrar antes el backlog ⇒ los fixes quedan sin trazabilidad | Media / media | Gate 0 **bloqueante**: backlog y `ESTADO_REAL.md` se actualizan antes del primer cambio de código |
| R-20 | Endurecer `demo_mode` / cookie / allowlist rompe el flujo local del propietario | Media / media | `NEURAL_ENV=local\|beta\|prod` con tres comportamientos; el local conserva el actual; el cambio se documenta en el README |
| R-21 | Sin remoto, un fallo de disco pierde los 36 commits y las dos bases de datos | Baja / **crítica** | **Mitigado 01/11:** remoto local `.remotes/*.git` + 2 bundles verificados + backup de BD restaurado y comparado (20 tablas con recuento idéntico) + manifiesto SHA-256 de todo lo sellado |
| R-22 | La cola hace la UI más lenta de lo que espera el usuario | Media / baja | La UI ya muestra progreso de trabajo; el gate de 2 s y el progreso visible lo compensan |
| R-23 | YouTube cambia su HTML/API y rompe la transcripción (R-07 aplicado a la cadena nueva) | **Alta / media** | Cadena de 3 proveedores ya existente (`yt-dlp` → `timedtext` → reproductor interno) + test con fixture local + aviso honesto en la UI |
| R-24 | Un port del hermano arrastra su arquitectura (`domain/` + vault) y choca con la del activo | Media / alta | Port **por módulo y por fichero**, con contrato propio y test; nunca «copiar la carpeta» |
| R-25 | La beta se cumple en la máquina del propietario y no en otra | Media / alta | Gate 6 con clon limpio en directorio nuevo, sin artefactos de la máquina |
| R-26 | **La gobernanza (plan, backlog, ADRs, tasks) vive en `newsV2/`, fuera de todo repositorio**: sin historial, sin remoto, sin copia de seguridad | Media / **alta** | El backlog y el registro de decisiones son la memoria del proyecto y lo único que explica *por qué* el código es como es. **Pendiente de decisión del propietario:** (a) mover `newsV2/` dentro de `neural-news/docs/governance/` y redirigir las referencias, o (b) versionarlo como repositorio propio con su remoto. **No ejecutar ninguna sin aprobación**: cambia rutas ya documentadas en el repo activo |

## Información que el agente NO puede deducir
1. Handle real de MaxDotAi en Flow y acceso a la cuenta.
2. Archivos MP4/fotografías o renders canónicos del personaje y permisos de uso.
3. Fondo CRT aprobado y si las pantallas deben mostrar marca NeuralStories News u otra definitiva.
4. Voz definitiva; material autorizado y consentimiento para TTS/clonación si la hubiera.
5. Catálogo de fuentes RSS preferidas, jurisdicciones, idiomas secundarios, frecuencia de noticias.
6. Endpoints/credenciales/modelos pagados, límites y condiciones contractuales.
7. Dominio de despliegue y política de publicación.
8. Licencia comercial de motor gráfico seleccionado para volumen y organización.
Estos asuntos son dependencias declaradas, **no razones para frenar el diseño del esquema/contratos y la demo sin gasto**. El sistema debe permitir cargarlos después sin reescritura.

## Change control
Cambios que afecten BD, identidad, derechos, costes, publicación o stack requieren ADR: decisión, alternativa, trade-off, test de rollback, autor y fecha. Ningún agente modifica las prioridades por su cuenta para declarar el proyecto acabado; puede replantear secuencia con evidencia y comunicarlo.
