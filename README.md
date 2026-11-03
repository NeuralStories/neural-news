# neural.news v1.0.0-beta.1 — motor editorial + NeuralStories Studio

Plataforma de investigación y producción editorial sobre inteligencia artificial: registrar
fuentes (YouTube, Spotify/pódcast, web/RSS, texto propio), extraer noticias candidatas,
investigarlas con evidencia, escribir y aprobar guiones, agruparlos en lotes y exportar el
paquete editorial. Encima, el **NeuralStories Studio**: el flujo de producción audiovisual en
ocho pasos, con persistencia real en la base de datos.

**Estado: BETA LOCAL verificada.** Versión `1.0.0-beta.1`. Se ejecuta **en local**, sin
desplegar ni publicar, sin claves de proveedor y sin Docker.

> Este README es la **única** guía de arranque. Si otro documento lo contradice, este manda.

---

## 1. Qué es y qué se ha verificado

Recorrido editorial completo, de principio a fin, con contenido ficticio en modo demo:

| Recorrido | Estado verificado |
|---|---|
| Alta de fuente con deduplicación (URL de YouTube/Spotify/artículo o texto propio) | FUNCIONA |
| Transcripción de vídeo de YouTube (cadena de 3 proveedores, sin Docker ni claves) | FUNCIONA |
| Transcripción de pódcast desde el feed RSS y transcripción pegada a mano | FUNCIONA |
| Extracción automática de candidatos (en el worker, no en la petición HTTP) | FUNCIONA |
| Investigación con evidencia marcada DEMO; sin evidencia, nada se marca como confirmado | FUNCIONA |
| Puntuación editorial orientativa y configurable (impacto/verificación/novedad/visual) | FUNCIONA |
| Guiones con **versiones** y aprobación humana; editar después **anula** la aprobación | FUNCIONA |
| **Studio de producción en 8 pasos** con persistencia real por paso | FUNCIONA |
| Invalidación dirigida: cambiar el guion marca solo los derivados afectados | FUNCIONA |
| Preparación visual (storyboard) con escenas, duración, rótulos y prompts | FUNCIONA |
| Lotes de 5/10 y exportación (ZIP con manifiesto JSON + guiones MD + storyboard) | FUNCIONA |
| Avisos de duplicados en la tabla de Noticias | FUNCIONA |
| Animática 9:16 con FFmpeg | **PARCIAL**: es animática **sin locución**, etiquetada como tal |

Lo que **no** es parte de esta beta está declarado en §7 (Límites) y en
[`docs/entrega/NOTAS_BETA.md`](docs/entrega/NOTAS_BETA.md).

**Cómo se verificó:** 14 comprobaciones automáticas con veredicto, código de salida y log
íntegro: [`docs/entrega/RESUMEN_VERIFICACIONES.md`](docs/entrega/RESUMEN_VERIFICACIONES.md).

---

## 2. Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 · SQLite (por defecto) o PostgreSQL 16 |
| Cola de trabajos | Tabla `jobs` con **lease**, reintentos y barrido de trabajos caducados |
| Frontend | Next.js 15 (App Router) · React 19 · TypeScript estricto · Tailwind CSS |
| Pruebas | pytest (backend) · Playwright (E2E en navegador real) · ESLint + `tsc --noEmit` |
| Criptografía | Argon2id (contraseñas) · Fernet (bóveda de secretos) · SHA-256 (integridad de fuentes) |

---

## 3. Requisitos

- **Python 3.12** (probado con 3.12.6)
- **Node.js 20 o superior** (probado con v24.20.0) y **npm** (probado con 11.19.0)
- **FFmpeg** en el `PATH` (para la animática; el resto funciona sin él)
- **yt-dlp** en el `PATH` (para transcripción de YouTube; sin él, la cadena cae al
  reproductor interno)
- Opcional: **PostgreSQL 16** (hay `infra/docker-compose.yml`; por defecto se usa SQLite)

No hace falta Docker para la beta.

---

## 4. Instalación (un comando)

```powershell
cd "C:\Users\haxth3\Documents\NeuralStories\proyecto final"

powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

`bootstrap.ps1` comprueba los requisitos, instala el backend (modo editable), crea el `.env` a
partir de `.env.example`, aplica las migraciones, instala la web y lanza la suite de pruebas.
Debe terminar con **«Listo.»**.

> Si mueves la carpeta, reinstala el backend: la instalación editable guarda **rutas
> absolutas** (`python -m pip install -e ".[dev]"` desde `apps\api`).

---

## 5. Lanzar la beta en local (modo producción)

```powershell
# Arrancar API + worker + web (la web usa el build de producción)
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# Parar
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

| Servicio | URL | Registro |
|---|---|---|
| Web | http://localhost:3000 | `apps\web\_web.log` |
| API | http://127.0.0.1:8000 (documentación en `/docs`) | `apps\api\_api.log` |
| Worker | cola de trabajos | `apps\api\_worker.log` |

Entra en http://localhost:3000 y pulsa **«Entrar en modo demo»**.

> `NEURAL_ENV=local` es **obligatorio** para una instalación de escritorio: fuera de `local`
> la web exige `NEURAL_API_URL` y **el build falla con un mensaje explícito** (gate G5:
> es preferible no compilar a compilar sin destino).

---

## 6. Variables de entorno

Copia `.env.example` a `.env` (lo hace `bootstrap.ps1`). Las que **cambian el comportamiento**:

| Variable | Por defecto | Efecto |
|---|---|---|
| `NEURAL_ENV` | `local` | `local` permite el proxy a `127.0.0.1:8000`. **Cualquier otro valor exige `NEURAL_API_URL`.** |
| `NEURAL_API_URL` | *(vacío)* | Destino del proxy same-origin `/api/*`. Obligatoria fuera de `local`. |
| `NEURAL_DEMO_MODE` | `true` | Modo demo reproducible; los servicios de pago quedan bloqueados. |
| `NEURAL_DATABASE_URL` | SQLite en `storage/` | Conexión a la base de datos. |
| `NEURAL_ALLOWED_HOSTS` | `[]` | Hosts de confianza del conector web/RSS. |
| `NEURAL_LOG_LEVEL` | `INFO` | Los errores del servidor se registran **en vez de devolverse al cliente**. |
| `NEURAL_PAID_SERVICES_ENABLED` / `NEURAL_BUDGET_DAILY_EUR` | `false` / `0` | Puerta de gasto. |
| `NEURAL_MASTER_KEY` | *(vacío)* | Clave maestra de la bóveda de secretos (Fernet). Sin ella, las claves de proveedor se pueden guardar en `.env` pero no cifradas en la base. |

La lista **completa** (las 30 variables que lee el código) está en
[`.env.example`](.env.example) y la verifica
[`tests/test_env_example_completo.py`](tests/test_env_example_completo.py).

Las claves de proveedores (YouTube, Gemini, Spotify, LLM, Brave) son **opcionales y vacías**:
los adaptadores están escritos pero **no se declaran validados** sin credenciales
([`docs/PROVIDER_STATUS.md`](docs/PROVIDER_STATUS.md)).

---

## 7. Cómo pasar las pruebas

```powershell
# Las 14 comprobaciones de la entrega, con veredicto y log por comando
pwsh -NoProfile -File docs\entrega\verificar.ps1

# O a mano
python -m pytest tests -q          # suite del backend
cd apps\web
npx tsc --noEmit                  # tipos
npx eslint .                      # lint
npx playwright test                # E2E en navegador real (levanta su propia pila)
```

La guía paso a paso para probar la beta a mano está en
[`docs/entrega/GUIA_PRUEBAS_BETA.md`](docs/entrega/GUIA_PRUEBAS_BETA.md).

---

## 8. Estructura

```
proyecto final/
  apps/api/            FastAPI + SQLAlchemy (paquete neuralnews) y handlers del worker
    src/neuralnews/    config · db · models · queue · worker · api/ · services/ · providers/
  apps/web/            Next.js 15 + TypeScript + Tailwind
    app/               fuentes · noticias · lotes · estudio · operacion · configuracion
    features/studio/   el Studio de 8 pasos (hooks, componentes y módulos de datos)
    lib/               cliente HTTP, mapa de estados, versión
  packages/contracts/  esquemas JSON de los contratos editoriales
  infra/               docker-compose, Dockerfiles, migraciones Alembic
  fixtures/            contenidos ficticios reproducibles (demo y pruebas)
  tests/               pytest: unitarias + integración + E2E de API
  tools/               comprobadores ejecutables (secretos, a11y, clases, evidencia, build)
  scripts/             bootstrap · start · stop (PowerShell)
  docs/
    entrega/           RESUMEN_COMPLETO · NOTAS_BETA · GUIA_PRUEBAS_BETA · INFORME_FINAL
    agente/            PLAN_MAESTRO · PLAN · TAREAS · REGISTRO · ESTADO (checkpoint)
    gobernanza/        gobernanza heredada (plan rector, decisiones, evidencia del port)
    DEPLOY.md · SECURITY.md · ARCHITECTURE.md · OPERATIONS.md · PROVIDER_STATUS.md
  storage/             base SQLite local, medios, montajes y entregas selladas (no versionado)
```

---

## 9. Límites declarados de esta beta

- **TTS / voz real**: fuera. El paso «Voz» persiste la velocidad; no hay locución.
- **Render final con locución**: fuera. Hoy hay animática sin audio, etiquetada como tal.
- **Publicación en plataformas**: fuera. Requiere credenciales y política del propietario.
- **Generación programática de imagen/vídeo**: fuera; el Studio prepara los prompts y el
  paquete, la generación es de un proveedor externo.
- **Gráficos**: solo la plantilla **BAR** (el resto se rechaza con `422`).
- **Multiusuario**: fuera. El modelo es de un único editor.
- **Seguridad**: quedan 2 avisos en dependencias transitivas de Next (exigen Next 16, un cambio
  ruptivo); ver [`docs/entrega/NOTAS_BETA.md`](docs/entrega/NOTAS_BETA.md).

Todo lo anterior está declarado **en la interfaz y en `ESTADO_REAL.md`**, no solo aquí.

---

## 10. Documentación

- **Resumen de la entrega**: [`docs/entrega/RESUMEN_COMPLETO.md`](docs/entrega/RESUMEN_COMPLETO.md)
- **Notas de la beta** (novedades, problemas conocidos): [`docs/entrega/NOTAS_BETA.md`](docs/entrega/NOTAS_BETA.md)
- **Guía de pruebas**: [`docs/entrega/GUIA_PRUEBAS_BETA.md`](docs/entrega/GUIA_PRUEBAS_BETA.md)
- **Informe final**: [`docs/entrega/INFORME_FINAL.md`](docs/entrega/INFORME_FINAL.md)
- **Verificaciones**: [`docs/entrega/RESUMEN_VERIFICACIONES.md`](docs/entrega/RESUMEN_VERIFICACIONES.md)
- **Estado real del producto** (fuente de verdad): [`ESTADO_REAL.md`](ESTADO_REAL.md)
- **Qué se ha construido, fase a fase**: [`IMPLEMENTACION_REALIZADA.md`](IMPLEMENTACION_REALIZADA.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
  [docs/SECURITY.md](docs/SECURITY.md) · [docs/EDITORIAL_STYLE.md](docs/EDITORIAL_STYLE.md) ·
  [docs/PROVIDER_STATUS.md](docs/PROVIDER_STATUS.md) · [docs/DEPLOY.md](docs/DEPLOY.md)
- **Gobernanza** (plan rector, registro de decisiones y riesgos):
  [docs/gobernance/](docs/gobernanza/) ·
  [plan rector de la beta](docs/gobernance/01_DOCUMENTACION/18_PLAN_MAESTRO_BETA.md)
- **Plan maestro ejecutado** (89 tareas, todas completadas) y su checkpoint:
  [docs/agente/PLAN_MAESTRO.md](docs/agente/PLAN_MAESTRO.md) ·
  [docs/agente/ESTADO.md](docs/agente/ESTADO.md)
