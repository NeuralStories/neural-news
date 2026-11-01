# neural.news — motor editorial + NeuralStories Studio

Plataforma de investigación y producción editorial sobre inteligencia artificial: registrar fuentes (YouTube, Spotify/pódcast, web/RSS, texto propio), extraer noticias candidatas, investigarlas con evidencia, escribir y aprobar guiones, agruparlos en lotes y exportar el paquete editorial. Encima, el **NeuralStories Studio**: la reintegración del flujo de producción audiovisual de Flow en ocho pasos, con persistencia real en la base de datos.

**Estado: en preparación de BETA. NO APROBADO todavía.** La lógica de Flow está reintegrada y verificada; la capa de entrega se está cerrando (ver [`ESTADO_REAL.md`](ESTADO_REAL.md), que es la fuente de verdad, y el [plan rector](../newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md)).

> Este README es la **única** guía de arranque. Si otro documento contradice a este, este manda.

---

## 1. Arranque rápido (Windows, sin claves, sin Docker)

```powershell
cd neural-news

# 1) Backend (una sola vez)
cd apps\api
python -m pip install -e ".[dev]"

# 2) Base de datos (si ya tienes PostgreSQL local, úsalo; si no, SQLite por defecto)
#    PostgreSQL 16.9 nativo en ../pglocal:
#    ..\..\pglocal\pgsql\bin\pg_ctl.exe -D ..\..\pglocal\data -l ..\..\pglocal\logfile.log -o "-p 5433" start
#    $env:NEURAL_DATABASE_URL="postgresql+psycopg://neural@127.0.0.1:5433/neuralnews"

# 3) API           → http://127.0.0.1:8000   (documentación en /docs)
python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000

# 4) Worker (otra terminal)
python -c "from neuralnews.worker import run; run()"

# 5) Web (otra terminal) → http://localhost:3000
cd ..\web
npm install
$env:NEURAL_ENV="local"     # ver §2
npm run dev
```

Entra en http://localhost:3000 y pulsa **«Entrar en modo demo»**. El flujo completo funciona con contenidos ficticios claramente marcados: alta de fuente → candidatos → investigación → guion → aprobación → lote → exportación.

---

## 2. Variables de entorno que importan

Copia `.env.example` a `.env` y ajústala. Las que **cambian el comportamiento** de la instalación:

| Variable | Por defecto | Efecto |
|---|---|---|
| `NEURAL_ENV` | `local` | `local` permite que el proxy de la web apunte a `127.0.0.1:8000`. **Cualquier otro valor exige `NEURAL_API_URL`.** |
| `NEURAL_API_URL` | *(vacío)* | Destino del proxy same-origin `/api/*` de la web. **Obligatoria fuera de `local`: sin ella, `next build` falla con un mensaje explícito** (antes el build pasaba y la aplicación se quedaba sin datos al desplegar). |
| `NEURAL_DEMO_MODE` | `true` | Modo demo reproducible; los servicios de pago quedan bloqueados. |
| `NEURAL_DATABASE_URL` | SQLite en `storage/` | Conexión a la base de datos. |
| `NEURAL_ALLOWED_HOSTS` | `[]` | Hosts de confianza del conector web/RSS. |
| `NEURAL_LOG_LEVEL` | `INFO` | Los errores del servidor se registran aquí **en vez de devolverse al cliente**. |
| `NEURAL_PAID_SERVICES_ENABLED` / `NEURAL_BUDGET_DAILY_EUR` | `false` / `0` | Puerta de gasto. |

Claves de proveedores (YouTube, Gemini, Spotify, LLM, Brave): **opcionales y vacías**. Los adaptadores están escritos pero **no se declaran validados** sin credenciales ([docs/PROVIDER_STATUS.md](docs/PROVIDER_STATUS.md)).

---

## 3. Qué se puede probar hoy

| Flujo | Cómo | Estado |
|---|---|---|
| Alta de fuente con deduplicación | Pega una URL de YouTube/Spotify/artículo o texto; repetirla no crea duplicados | FUNCIONA |
| **Transcripción de cualquier vídeo de YouTube** | Fuentes → «Buscar transcripción»: cadena de 3 proveedores (`yt-dlp` → `timedtext` → reproductor interno), **sin Docker ni claves** | FUNCIONA |
| **Transcripción de pódcast** | El operador aporta el feed RSS en los metadatos de la fuente; se lee `podcast:transcript` | FUNCIONA (corregido el 01/11, ver `ESTADO_REAL.md` B1/B16) |
| **Transcripción pegada a mano** | En el alta o en la ficha de la fuente: se guarda como `TRANSCRIPT` y no se pierde | FUNCIONA (corregido el 01/11, B2) |
| Episodio de Spotify sin transcripción | Aparece como «Solo información básica» con aviso claro | FUNCIONA |
| Extracción de candidatos | Automática al procesar la fuente (worker) | FUNCIONA |
| Investigación con evidencia marcada DEMO | Botón «Investigar»; sin evidencia nada se marca como confirmado | FUNCIONA |
| Puntuación editorial orientativa | impacto 35 · verificación 30 · novedad 20 · visual 15 (configurable) | FUNCIONA |
| Guiones con versiones y aprobación | Generar borrador → editar → «Aprobar esta versión»; editar después la anula | FUNCIONA |
| **Studio de producción en 8 pasos** | `/estudio`: Noticias · Personaje · Fondo · Guion · Voz · Movimiento · Referencias · Resultado. Persistencia real por paso, con control de versión (CAS 409) | FUNCIONA |
| Invalidación dirigida | Cambiar el guion marca **solo** los derivados afectados (gráficos, tomas) y deja el MP4 importado intacto | FUNCIONA |
| **Animática 9:16** | Montaje FFmpeg real con transiciones. **Etiquetada como animática sin locución: NO es el render final** | PARCIAL |
| Preparación visual (storyboard) | En la noticia: «Preparar escenas» genera escenas, duración, rótulos y prompts de imagen copiables | FUNCIONA |
| Lotes de 5/10 y exportación | Pendientes claramente marcados; ZIP con manifiesto JSON + guiones MD + storyboard | FUNCIONA |
| Avisos de duplicados | La tabla de Noticias marca los posibles duplicados | FUNCIONA |

---

## 4. Pruebas

```powershell
# Suite Python (unitarias + integración + E2E de API) — DESDE LA RAÍZ del repositorio
cd neural-news
python -m pytest tests -q
```

Última ejecución en este entorno (01/11/2026): **154 passed, 1 skipped, 0 fallos** en 65 s. Incluye duplicidad e idempotencia, SSRF, contenido malicioso como dato, conflictos de edición, invalidación de aprobaciones, lotes con pendientes, presupuesto agotado, storyboard, duplicados, contrato OpenAPI, las 10 regresiones F-01…F-10 y **15 regresiones NN-109** nuevas (`tests/test_nn109_defectos.py`), verificadas rojas sobre el código original y verdes tras el arreglo.

> ⚠ **Ojo:** la suite debe ejecutarse **desde la raíz del repositorio**. Desde `apps/api` fallan 3 tests por el `sys.path` (pendiente de corregir: NN-114).

```powershell
# Tipos y build de la web
cd apps\web
npx tsc --noEmit
$env:NEURAL_ENV="local"; npm run build

# E2E en navegador real (Playwright con el Edge/Chrome del sistema)
# Requiere API (:8000), worker y web (:3000) en marcha
npm run e2e
```

---

## 5. Estructura

```
neural-news/
  apps/api/       FastAPI + SQLAlchemy (paquete neuralnews) y handlers del worker
  apps/web/       Next.js 15 + TypeScript + Tailwind
                    app/       Fuentes · Noticias · Lotes · Estudio · Configuración
                    features/studio/  el Studio de 8 pasos (22 ficheros)
  packages/contracts/  esquemas JSON de los contratos editoriales + openapi.json
  infra/          docker-compose, Dockerfiles, migraciones Alembic
  fixtures/       contenidos ficticios reproducibles (demo y pruebas)
  tests/          pytest: unitarias + integración + E2E de API (24 ficheros)
  docs/           BASELINE · ARCHITECTURE · PROVIDER_STATUS · EDITORIAL_STYLE · OPERATIONS · SECURITY
  storage/        base de datos SQLite local, medios, montajes y entregas selladas (no versionado)
```

---

## 6. Documentación

**Fuente de verdad del estado:** [`ESTADO_REAL.md`](ESTADO_REAL.md) — módulo a módulo, con etiquetas FUNCIONA / PARCIAL / PENDIENTE_POR_ACTIVO / PENDIENTE_POR_API / NO_IMPLEMENTADO y la evidencia de cada afirmación.

- [IMPLEMENTACION_REALIZADA.md](IMPLEMENTACION_REALIZADA.md) — qué se ha construido, fase a fase, con sus commits.
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — arranque, comandos, migraciones, errores y copias de seguridad.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — módulos, modelo de datos, estados, cola de trabajos y adaptadores.
- [docs/SECURITY.md](docs/SECURITY.md) — SSRF, contenido como dato, secretos, presupuesto y riesgos pendientes.
- [docs/EDITORIAL_STYLE.md](docs/EDITORIAL_STYLE.md) — contratos de extracción, investigación, redacción y revisión.
- [docs/PROVIDER_STATUS.md](docs/PROVIDER_STATUS.md) — estado honesto de cada integración externa.
- Plan rector de la beta: [../newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md](../newsV2/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md).

---

## 7. Límites declarados (beta)

- **TTS / voz real**: fuera. El paso «Voz» persiste la velocidad; no hay locución.
- **Render final con locución**: fuera. Hoy hay animática sin audio, etiquetada como tal.
- **Publicación en plataformas**: fuera. Requiere credenciales y política del propietario.
- **Generación programática de imagen/vídeo**: pendiente de integración externa autorizada.
- **Gráficos**: solo la plantilla **BAR** (verificado: el resto se rechaza con `422`).
- **Multiusuario**: fuera. El modelo es de un único editor.

Todo lo anterior está declarado **en la interfaz y en `ESTADO_REAL.md`**, no solo aquí.
