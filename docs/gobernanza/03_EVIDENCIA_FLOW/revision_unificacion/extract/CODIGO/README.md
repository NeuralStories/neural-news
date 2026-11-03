# neural.news — MVP y código de NeuralStories Studio

Plataforma de investigación y producción editorial sobre inteligencia artificial: registrar fuentes (YouTube, Spotify/pódcast, web/RSS, texto propio), extraer noticias candidatas, investigarlas con evidencia, escribir y aprobar guiones, agruparlos en lotes de 5 o 10 y exportar un paquete editorial completo.

Este repositorio está unificado en `C:\Users\haxth3\Documents\news_Neural`. El motor editorial vive en `apps/`; el código original recuperado del editor de Google Flow, el extractor, el ZIP y las pruebas de integridad están en [`flow-recovery/`](flow-recovery/README.md). La copia de Flow conserva sus rutas originales y todavía no es una aplicación independiente compilada. Véase [`UNIFICATION_MANIFEST.md`](UNIFICATION_MANIFEST.md) para procedencia, verificación y pendientes.

**Estado: MVP funcional en modo demo, verificado con 53 pruebas automatizadas y un recorrido completo en vivo.** Los adaptadores de proveedores de pago están preparados pero NO validados con credenciales (ver [docs/PROVIDER_STATUS.md](docs/PROVIDER_STATUS.md)).

## Arranque rápido en Windows (sin claves, sin Docker)

```powershell
cd news_Neural

# 1) Instalar el backend (una sola vez)
cd apps\api
python -m pip install -e ".[dev]"

# 2) Arrancar la API          → http://127.0.0.1:8000  (docs en /docs)
python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000

# 3) Arrancar el worker (otra terminal)
python -m neuralnews.worker

# 4) Arrancar la web (otra terminal) → http://localhost:3000
cd ..\web
npm install
npm run dev
```

Entra en http://localhost:3000 y pulsa **«Entrar en modo demo»**. Todo el flujo funciona con contenidos ficticios claramente marcados: alta de fuente → candidatos → investigación → guion → aprobación → lote → exportación ZIP.

Con Docker Desktop (PostgreSQL + API + worker + web):

```powershell
cd infra
docker compose up --build
```

## Qué puede probar sin claves

| Flujo | Cómo |
|---|---|
| Alta de fuente con deduplicación | Pega una URL de YouTube/Spotify/artículo o texto; repetirla no crea duplicados |
| Vídeo demo con transcripción simulada + análisis | `https://youtu.be/demoVideo01` |
| Episodio de Spotify sin transcripción | Aparece como «Solo información básica» con aviso claro |
| Texto propio | Pégalo o sube un `.txt`/`.md` (máx. 2 MB) |
| Extracción de candidatos | Automática al procesar la fuente (worker) |
| Investigación con evidencia marcada DEMO | Botón «Investigar»; sin evidencia nada se marca como confirmado |
| Puntuación editorial orientativa | impacto 35 · verificación 30 · novedad 20 · visual 15 (configurable) |
| Guiones con versiones y aprobación | Generar borrador → editar → «Aprobar esta versión»; editar después la anula |
| Preparación visual (storyboard) | En la noticia: «Preparar escenas» genera escenas, duración, rótulos y prompts de imagen copiables |
| Lotes de 5/10 y exportación | Pendientes claramente marcados; ZIP con manifiesto JSON + guiones MD + storyboard y prompts de imagen |
| Avisos de duplicados | La tabla de Noticias marca los posibles duplicados (mismo tema o títulos parecidos) |

## Estructura

```
news_Neural/
  apps/api/       FastAPI + SQLAlchemy (paquete neuralnews) y handlers del worker
  apps/worker/    punto de entrada del worker de trabajos
  apps/web/       Next.js 15 + TypeScript + Tailwind (Fuentes · Noticias · Lotes · Configuración)
  packages/contracts/  esquemas JSON de los contratos editoriales
  infra/          docker-compose, Dockerfiles, migraciones Alembic
  fixtures/       contenidos ficticios reproducibles (demo y pruebas)
  tests/          pytest: unitarias + integración + E2E del recorrido crítico
  docs/           BASELINE · ARCHITECTURE · PROVIDER_STATUS · EDITORIAL_STYLE · OPERATIONS · SECURITY
  storage/        base de datos SQLite local y paquetes exportados (no versionado)
  flow-recovery/ fuente original de NeuralStories Studio, extractor, ZIP e informes
```

## Pruebas

```powershell
# Suite Python (unitarias + integración + E2E de API)
cd apps\api
python -m pytest ../../tests -q
```

Última ejecución en este entorno: **64 passed**. Incluye duplicidad e idempotencia, SSRF, contenido malicioso como dato, JSON defectuoso del modelo, conflictos de edición, invalidación de aprobaciones, lotes con pendientes, presupuesto agotado, storyboard, duplicados posibles, contrato OpenAPI y el recorrido crítico completo de API.

```powershell
# Suite E2E en navegador real (Playwright con el Edge/Chrome del sistema)
# Requiere API (:8000), worker y web (:3000) en marcha
cd apps\web
npm run e2e
```

Última ejecución en este entorno: **5 passed** — recorrido crítico completo (fuente → noticias → investigación → guion → edición → aprobación → storyboard → lote), columnas de la tabla de noticias, reintento seguro y análisis de vídeo, diseño móvil a 390 px y redirección sin sesión.

## Claves de proveedores (opcionales)

Todas empiezan vacías y los servicios de pago **desactivados**. Copia `.env.example` a `.env` y rellena sólo lo que uses: YouTube Data API, Gemini (análisis de vídeo), Spotify (token de usuario), modelo editorial compatible OpenAI y buscador (adaptador Brave). Estado honesto de cada integración: [docs/PROVIDER_STATUS.md](docs/PROVIDER_STATUS.md).

## Documentación

- [docs/OPERATIONS.md](docs/OPERATIONS.md) — arranque, comandos PowerShell, migraciones, errores y copias de seguridad.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — módulos, modelo de datos, estados, cola de trabajos y adaptadores.
- [docs/SECURITY.md](docs/SECURITY.md) — SSRF, contenido como dato, secretos, presupuesto y riesgos pendientes.
- [docs/EDITORIAL_STYLE.md](docs/EDITORIAL_STYLE.md) — contratos de extracción, investigación, redacción y revisión (v1).
- [docs/BASELINE.md](docs/BASELINE.md) — auditoría inicial del entorno y decisiones.

## Límites del MVP

- Producción de vídeo (Google Flow, APIMart), ASR de audio y suscripciones automáticas: **fuera del MVP**; se entregan storyboard y prompts para uso manual.
- Los adaptadores YouTube/Spotify/Gemini/búsqueda/LLM reales están escritos pero sin ejecutar con credenciales: no se declaran validados.
- Un solo editor con sesión local; sin RLS/multiusuario (evolución con Supabase Auth).
