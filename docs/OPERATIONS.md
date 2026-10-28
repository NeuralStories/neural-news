# OPERATIONS.md — Arranque, operación y mantenimiento (Windows)

## 1. Requisitos

- Windows 10/11 con Python 3.12+, Node 20+ (probado con 24), git.
- Opcional: Docker Desktop (para PostgreSQL y despliegue en contenedores).

## 2. Arranque rápido en modo demo (sin claves, sin Docker)

```powershell
cd C:\Users\haxth3\Documents\NeuralStories\neural-news

# 1) Backend
python -m pip install -e ".[dev]" --src .\apps\api
# (desde apps/api: python -m pip install -e ".[dev]")

# 2) Arrancar API (terminal 1)
cd apps\api
python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000

# 3) Arrancar worker (terminal 2)
cd apps\api
python -m neuralnews.worker

# 4) Arrancar web (terminal 3)
cd apps\web
npm install
npm run dev   # http://localhost:3000
```

Entrar en http://localhost:3000 y pulsar **Entrar en modo demo**. La API expone documentación OpenAPI en http://127.0.0.1:8000/docs.

Alternativa de un solo paso (recomendada, ya verificada en este entorno):

```powershell
cd apps\api
python -m pip install -e ".[dev]"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd apps\api; python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd apps\api; python -m neuralnews.worker"
```

## 3. Arranque con Docker Desktop

```powershell
cd infra
docker compose up --build
# API: http://localhost:8000 · Web: http://localhost:3000 · PostgreSQL en 5432
```

Las migraciones Alembic se aplican automáticamente al arrancar el contenedor `api`.

> **Nota de verificación (28-10-2026):** en la máquina de desarrollo, Docker Desktop no llegó a arrancar
> («Docker Desktop is unable to start», problema local de instalación/WSL). El `docker-compose.yml` y los
> Dockerfiles están preparados pero **la construcción en contenedor NO ha podido verificarse**. El camino
> principal verificado es el arranque local sin Docker (sección 2), que cubre el mismo flujo con SQLite.
> Si Docker funciona en tu máquina, el compose debería levantar los cuatro servicios; revísalo antes de
> depender de él.

## 4. Migraciones

```powershell
cd infra\migrations
$env:NEURAL_DATABASE_URL="sqlite:///C:/Users/haxth3/Documents/NeuralStories/neural-news/storage/neural-news.db"
python -m alembic upgrade head                      # aplicar
python -m alembic revision --autogenerate -m "cambio"   # generar nueva revisión
```

En desarrollo SQLite la API también crea el esquema automáticamente si falta (`create_all`); en producción usar siempre Alembic.

## 5. Pruebas

**Suite Python (unitarias + integración + E2E de API):**

```powershell
cd apps\api
python -m pytest ../../tests -q
```

Resultado de referencia en este entorno: **64 passed**.

**Suite E2E en navegador real (Playwright + Edge/Chrome del sistema):**

```powershell
# Requiere la API (:8000), el worker y la web (:3000) en marcha.
cd apps\web
npm run e2e            # o: npx playwright test
npm run e2e:ui         # con interfaz visual
```

Resultado de referencia en este entorno: **5 passed** (recorrido crítico completo, columnas de la tabla
de noticias, reintento seguro y análisis de vídeo, diseño móvil a 390 px y redirección sin sesión).

El E2E usa el navegador ya instalado (`channel: msedge`; configurable con `NEURAL_E2E_CHANNEL=chrome`),
así que **no hace falta descargar navegadores de Playwright**. La web debe estar recién compilada
(`npm run build`) antes de `npm start`: un servidor `next start` con el build anterior sirve chunks
obsoletos y la aplicación se queda en «Cargando…».

**Regenerar el contrato OpenAPI:**

```powershell
python apps/api/scripts/export_openapi.py   # → packages/contracts/openapi.json
```

## 6. Operación diaria

1. **Alta de fuente**: pega URL de YouTube/Spotify/artículo/feed, o texto. La creación encola el proceso automáticamente (idempotente con `Idempotency-Key`).
2. **Candidatos**: el worker extrae noticias candidatas; revísalas en Noticias.
3. **Investigar**: lanza la búsqueda (demo o real según claves); revisa afirmaciones y evidencia.
4. **Guion**: genera borrador, edita (guarda versiones), aprueba la versión exacta.
5. **Lotes**: crea lotes de 5 o 10, ordena, exporta el paquete ZIP (manifiesto JSON + guiones Markdown + storyboard/prompts) y descárgalo.
6. **Configuración**: presupuesto diario, servicios de pago (desactivados por defecto), pesos de puntuación, estado de proveedores.

## 7. Errores frecuentes y recuperación

| Síntoma | Causa probable | Acción |
|---|---|---|
| «Esta fuente solo tiene información básica…» | Episodo de Spotify sin transcripción | Aporta transcripción (POST /sources/{id}/transcript) o usa el vídeo demo |
| «No hay clave de YouTube configurada…» | Adaptador real sin credenciales | Añade clave a `.env` o usa modo demo |
| «Presupuesto diario agotado…» | Límite alcanzado | Sube el límite en Configuración o sigue en demo |
| Trabajo en «Reintentando» | Fallo transitorio del conector | El worker reintenta (máx. 3). El error queda en el detalle del trabajo |
| Worker reiniciado con trabajos a medias | Corte/reinicio | Al arrancar recupera los lease vencidos y los reencola (idempotente) |
| Sesión caducada | 12 h por defecto | Vuelve a entrar |

## 8. Copias de seguridad

- SQLite: copia `storage/neural-news.db` (y `-wal`/`-shm` con la API parada).
- Paquetes exportados: `storage/packages/*.zip` (ya contienen manifiesto con hash).
- PostgreSQL: `pg_dump -U neural neuralnews > backup.sql`.

## 9. Logs y observabilidad

- El worker imprime por consola: id de trabajo, tipo, intento, resultado o error normalizado.
- `GET /api/v1/jobs` lista el historial; `GET /api/v1/usage` muestra consumos y presupuesto.
- Nunca se registran secretos ni tokens (ver SECURITY.md).
