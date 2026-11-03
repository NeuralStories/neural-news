# Plan de ejecución inicial — 10 horas, 1 agente

**No significa producto terminado**: ventana de 600 minutos de trabajo autónomo. El agente no esperará instrucciones rutinarias, pero tampoco gastará créditos, accederá a Flow privado o desplegará sin permiso. Cada fase entrega código, test y registro, o falla honestamente. **No alterar fases o requisitos para simular progreso**.

| Hora | Minutos | Gate y resultado | Si bloquea |
|---|---:|---|---|
| 00:00–00:40 | 40 | G0: inspección de paquete/Flow, entorno, repo nuevo, Git, README, ADR y dependencias de versión comprobadas | Anotar faltantes; no instalar herramientas inseguras |
| 00:40–02:00 | 80 | G1: Compose PostgreSQL, API, Alembic, admin seguro, `.env.example`, base de tablas mínimas y configuración de costo 0 | Primero DB real y auth; diferir UI avanzada |
| 02:00–03:35 | 95 | G2: fuente DEMO autorizada, snapshots/claims/evidence, guion versión editable, persistencia y pruebas de concurrencia | Sin LLM usar pipeline manual/fixture DEMO |
| 03:35–05:15 | 100 | G3: beats, ProductionPlan, selector source_kind, MaxDotAi PENDING, GraphicSpec/primer gráfico, paquete manual Flow | Dejar generación real como MANUAL/BLOCKED |
| 05:15–06:45 | 90 | G4: pantalla única Inicio/Noticias/Producción/Configuración; guardar/cargar y controles explícitos | No crear 12 vistas vacías |
| 06:45–07:40 | 55 | G5: jobs persistentes, proveedor fake local, rutas modelo/config, test de presupuesto=0, worker y estados visibles | No añadir nueva cola infra |
| 07:40–09:05 | 85 | G6: tests de fuentes, auth/secretos, aprobaciones, gráfico, UI E2E, backup+restore en test | Interrumpir nuevas funciones y corregir P0 |
| 09:05–10:00 | 55 | G7: repetir suite, build, README de uso, bitácora, backlog estado, entrega honesta, próximos pasos | No desplegar/publicar |
| **Total** | **600** | **10h** | |

**Orden de ejecución predeterminado**: seleccionar `milestone=A` en `BACKLOG.csv`, orden topológico por deps y prioridad. No tratar duración asignada como excusa para cerrar tarea. Si cae la calidad, recortar extensiones P1/P2, **nunca** seguridad básica, persistencia, coherencia o veracidad.

## Primera demo de aceptación
En UI admin: abrir noticia `DEMO` -> ver fuente y claim de demostración -> escribir o obtener desde proveedor fake un guion -> guardar versión -> seleccionar plan con (a) video aportado PENDING para presentador, (b) gráfico de barras exacto, (c) title card -> export paquete Flow manual con prompt sin supuesta API -> cerrar navegador y reabrir sin pérdida. Ejecución pago 0. Confirmar que sin medio real no hay «vídeo final».

## Archivo obligatorio de reporte en repo nuevo
`docs/estado/00_INVENTARIO.md`; `01_DECISIONES.md`; `02_TAREAS_EJECUTADAS.csv`; `03_PRUEBAS_Y_COMANDOS.md`; `04_BLOQUEOS.md`; `05_MANUAL_INSTALACION.md`; `06_ENTREGA_10H.md`. Actualizar cada 45–60 min; registra timestamps, commits/archivos y pruebas. No afirmar ejecución si no hay entorno.

## Formato de cierre por tarea
`ID`, prerequisitos, archivos tocados, test específico, comando ejecutado, resultado literal, evidencia, riesgos, estado `DONE|PARTIAL|BLOCKED|NOT_STARTED`, cambio respecto plan. Revisión de cambios `git diff --check`, migración/check rollback, contratos de schema y escaneo de secretos. Antes de terminar, agent debe parar el worker si puede dejar cargos o efectos laterales fuera de sandbox.

## El agente no tiene que pedir
Ubicación de nuevo repo si el usuario le asigna carpeta; si no, crear carpeta `neural-news` bajo directorio de trabajo **autorizado**, sin tocar proyectos viejos. Elección de librería y tareas rutinarias dentro de stack fijado. Si falta cuenta Flow o vídeos, no bloquear la capa editorial; dejar integración manual preparada.
