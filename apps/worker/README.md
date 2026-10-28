# apps/worker

Punto de entrada del trabajador de trabajos en segundo plano. Usa el mismo paquete
`neuralnews` que la API (la cola vive en la base de datos, no en un servicio externo).

## Arranque

```powershell
cd apps\api
python -m neuralnews.worker          # bucle continuo (encuesta cada segundo)
python -m neuralnews.worker --once   # drena la cola y sale (útil en pruebas)
```

Con el paquete instalado también funciona el entrypoint `neuralnews-worker`.

## Comportamiento

- Al arrancar recupera los trabajos RUNNING con lease vencido (recuperación tras reinicio).
- Reclama un trabajo cada vez con lease de 300 s; reintenta hasta 3 veces con backoff (30 s × intento).
- Manejadores idempotentes: `process_source`, `analyze_video`, `research_story`, `draft_script`, `export_batch`.
- Las llamadas de pago fallan de forma definitiva si el presupuesto las bloquea (sin reintentos que dupliquen cargos).
