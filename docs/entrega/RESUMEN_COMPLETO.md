# Resumen completo — neural.news v1.0.0-beta.1

**Estado:** BETA LOCAL verificada · **Ruta:** `C:\Users\haxth3\Documents\NeuralStories\proyecto final`
· **Raíz Git:** `C:/Users/haxth3/Documents/NeuralStories/proyecto final`

Este documento resume **qué es** el producto, **cómo está construido**, **cómo se ha
verificado** y **qué queda fuera**. No inventa nada: cada afirmación tiene su evidencia
en el código, en las pruebas o en los logs de `docs/entrega/evidencias/`.

---

## 1. Propósito

`neural.news` es un **motor editorial** sobre inteligencia artificial: recoge una fuente
(YouTube, Spotify/pódcast, web/RSS o texto propio), extrae noticias candidatas, las
investiga con evidencia trazable, escribe y **aprueba** guiones por versiones, los agrupa
en lotes y exporta el paquete editorial.

Encima está el **NeuralStories Studio**: el flujo de producción audiovisual en ocho etapas
(personaje, escenario, guion, voz, movimiento, referencias, producción y resultado), con
**persistencia real en la base de datos**: lo que se guarda se conserva al recargar.

La tesis del producto, en una frase: **la máquina propone y la persona aprueba**. Ninguna
afirmación se da por verificada sin evidencia, y ninguna versión de guion se da por
aprobada sin una acción humana explícita.

## 2. Alcance de esta beta

**Dentro:**

- Recorrido editorial completo con contenido ficticio en modo demo.
- Studio de 8 etapas con persistencia, control de versión y colisión explícita (409).
- Cola de trabajos con lease, reintentos y barrido de trabajos caducados.
- Observabilidad: salud real de dependencias, métricas y alertas.
- Presupuesto verificado **antes** de la llamada, con coste estimado real.
- Bóveda de secretos (Fernet) y Argon2id para contraseñas.
- Puertas de seguridad de despliegue (`NEURAL_ENV`), SSRF, rate limit y escaneo de secretos.

**Fuera (declarado en la interfaz, no solo aquí):** TTS/voz real, render final con
locución, publicación en plataformas, generación programática de imagen/vídeo, gráficos
distintos de BAR, multiusuario y material real de MaxDotAi.

## 3. Arquitectura y componentes

```
                    navegador
                        │  mismo origen /api/* (proxy de Next)
                        ▼
        ┌───────────────────────────────┐
        │  Web (Next.js 15 + React 19)   │  páginas + Studio de 8 etapas
        └───────────────┬───────────────┘
                        │  HTTP (FastAPI)
                        ▼
        ┌───────────────────────────────┐
        │  API (FastAPI + SQLAlchemy)    │  fuentes · noticias · lotes · operaciones
        │  · auth y sesión               │
        │  · cola de trabajos (jobs)     │
        │  · adaptadores de proveedor   │
        └───────────────┬───────────────┘
                        │  entrega de trabajos
                        ▼
        ┌───────────────────────────────┐
        │  Worker (bucle de trabajos)    │  transcripción · extracción · investigación
        │  · lease + reintentos          │  redacción · storyboard · montaje FFmpeg
        └───────────────┬───────────────┘
                        ▼
        ┌───────────────────────────────┐
        │  Base de datos (SQLite/PG)     │  fuentes · noticias · afirmaciones · guiones
        │  · Alembic (único esquema)     │  aprobaciones · lotes · trabajos · medios
        └───────────────────────────────┘
```

**Decisiones estructurales con efecto en el comportamiento:**

1. **Una sola base de datos y un solo esquema**: el esquema sale **solo** de Alembic
   (`create_all` se eliminó: nunca añade columnas, y por eso la base viva quedó desfasada).
2. **Ninguna petición HTTP hace trabajo pesado**: transcripción, extracción, investigación,
   redacción y montaje salen a la cola. El trabajo pesado va con **lease**, así que un
   worker caído no pierde el trabajo ni lo ejecuta dos veces.
3. **El log es JSON por evento** y el motivo del fallo va **normalizado**
   (`budget` · `material` · `connector` · `unknown`): el operador sabe por qué falló sin
   leer la traza.
4. **Los errores del servidor no se devuelven al cliente**: se registran. El cliente recibe
   un error tipado (`ApiError` con `status`/`code`/`detail`).
5. **El backend es la fuente de verdad de estados y etiquetas**: la web los recibe
   generados, así que no puede haber dos listas que diverjan.
6. **El presupuesto se verifica antes de la llamada**, no después: si el día ya está
   gastado, el trabajo se marca `FAILED` con `error_kind=budget` sin gastar.

## 4. Flujos principales

### 4.1 De la fuente a la noticia aprobada

1. **Alta** de una fuente (URL o texto). La deduplicación es por ID, URL canónica y
   similitud léxica: la misma fuente no se crea dos veces.
2. **Transcripción** (worker): cadena de tres proveedores para YouTube (`yt-dlp` →
   `timedtext` → reproductor interno), feed RSS para pódcast y texto pegado a mano. Sin
   transcripción, la fuente se marca «Solo información básica» con aviso claro.
3. **Extracción** de candidatos: del contenido salen noticias, con su bloque de escaleta.
4. **Investigación**: cada afirmación queda `UNVERIFIED`, `SUPPORTED`, `CONTRADICTED` o
   `NOT_VERIFIABLE`, con su evidencia. En modo demo la evidencia ficticia usa el dominio
   reservado `.invalid` y va marcada `DEMO`. Una afirmación sin evidencia **no** se da por
   verificada.
5. **Puntuación** orientativa y configurable (impacto 35 · verificación 30 · novedad 20 ·
   visual 15).
6. **Guion por versiones**: generar borrador → editar → «Aprobar esta versión». Editar
   después **anula** la aprobación (y la interfaz avisa de ello).
7. **Lote** de 5/10 con pendientes marcados y **exportación** (ZIP con manifiesto JSON,
   guiones en Markdown y storyboard).

### 4.2 El Studio en ocho etapas

Noticias · Personaje · Fondo · Guion · Voz · Movimiento · Referencias · Resultado. Cada
etapa se guarda por separado (y solo se guarda si ha cambiado de verdad), con control de
concurrencia: si otra sesión guardó antes, la API responde **409** y la interfaz lo dice
en vez de pisar el trabajo ajeno.

### 4.3 Operación

`/ops` muestra la salud real (base de datos, FFmpeg, yt-dlp, proveedores con sus claves),
el consumo de hoy, los trabajos recientes **con su motivo de fallo**, las **métricas**
(p95 y media de duración, tasa de fallo, profundidad de cola, desglose por tipo y por
motivo) y las **alertas** (cola parada, lease vencido, presupuesto al 80 %, fallo repetido
del mismo tipo).

## 5. Integraciones

| Integración | Estado | Nota |
|---|---|---|
| YouTube (metadatos y transcripción) | FUNCIONA sin claves | La transcripción no necesita clave |
| Spotify (feed de episodio) | FUNCIONA con el feed aportado | El token de usuario es opcional |
| Web/RSS | FUNCIONA | Con protecciones SSRF y allowlist de hosts |
| Gemini (análisis de vídeo) | Preparado, **sin validar** | Requiere clave; el modo demo no lo llama |
| Modelo compatible OpenAI (guiones) | Preparado, **sin validar** | Requiere clave y `NEURAL_PAID_SERVICES_ENABLED` |
| Búsqueda (Brave) | Preparado, **sin validar** | Requiere clave |
| FFmpeg | FUNCIONA si está en el `PATH` | Genera la animática 9:16 |

Detalle: [`docs/PROVIDER_STATUS.md`](PROVIDER_STATUS.md).

## 6. Archivos clave

| Fichero | Para qué |
|---|---|
| `apps/api/src/neuralnews/config.py` | Toda la configuración y las reglas de despliegue |
| `apps/api/src/neuralnews/queue.py` | Cola: reserva, lease, reintentos, barrido |
| `apps/api/src/neuralnews/worker.py` | Bucle del worker (log JSON por evento) |
| `apps/api/src/neuralnews/states.py` | Estados y etiquetas (**fuente de verdad** para la web) |
| `apps/api/src/neuralnews/metrics.py` | Métricas y alertas del sistema |
| `apps/api/src/neuralnews/services/budget.py` | Presupuesto verificado antes de la llamada |
| `apps/api/src/neuralnews/services/model_routes.py` | Rutas de modelo con instantánea en el trabajo |
| `apps/api/src/neuralnews/vault.py` · `services/secrets.py` | Bóveda de secretos (Fernet) |
| `apps/web/lib/http.ts` | Cliente HTTP único con `ApiError` tipado |
| `apps/web/lib/estados.ts` · `estados.generado.ts` | Mapa de estados **único** (generado) |
| `apps/web/features/studio/lib/` | Los 7 hooks del Studio (reglas de negocio) |
| `tools/*.py` | Comprobadores ejecutables (secretos, a11y, clases, evidencia, build) |
| `docs/entrega/verificar.ps1` | Las 14 comprobaciones de la entrega |
| `docs/agente/PLAN_MAESTRO.md` · `ESTADO.md` | Plan ejecutado y checkpoint |

## 7. Configuración

- **Variables**: las 30 que lee el código están en [`.env.example`](.env.example); la prueba
  `tests/test_env_example_completo.py` falla si el backend añade una y la plantilla no la
  recoge.
- **Puertas**: `NEURAL_ENV=local|beta|prod` gobierna el modo demo, la cookie de sesión, la
  allowlist de red y el esquema. Fuera de `local` la aplicación **no arranca** con demo
  activo o con la contraseña de ejemplo, y el build de la web **falla** sin `NEURAL_API_URL`.
- **Esquema**: solo Alembic (`infra/migrations`). La base se crea y se actualiza con
  migraciones; nunca con `create_all`.

## 8. Resultados de la verificación

14 comprobaciones, todas con veredicto, código de salida y log íntegro en
`docs/entrega/evidencias/`. Resumen en
[`RESUMEN_VERIFICACIONES.md`](RESUMEN_VERIFICACIONES.md).

| Comprobación | Resultado |
|---|---|
| `python -m pytest tests -q` | **386 tests**, 1 skip justificado, 0 fallos |
| `npx tsc --noEmit` | 0 errores |
| `npx eslint .` | 0 problemas |
| `npm run build` | compila (modo producción, con `NEURAL_ENV=local`) |
| `npx playwright test` | **8 pruebas E2E** en navegador real, 0 fallos |
| `tools/check_clases.py` | 0 reimplementaciones en línea, 0 clases inexistentes |
| `tools/check_a11y.py` | 0 bloqueantes, 0 avisos |
| `tools/scan_secrets.py .` | 0 hallazgos (árbol **e** historial de git) |
| `generate_estados` / `generar_manifiesto_studio` / `generar_plan_casillas` `--check` | al día |
| `exportar_openapi.py --check` | el contrato exportado coincide con el servido |
| `tools/auditar_evidencias.py` | 0 referencias desfasadas en el plan |
| `git diff --check` | sin errores de espacios (excluidos evidencia y gobernanza, por diseño) |

El **skip** justificado es el test que comprueba la descarga por trozos con corte real de
bytes: requiere cortar la conexión a mitad, algo que el entorno de pruebas no deja hacer de
forma determinista.

## 9. Seguridad y datos

- **SSRF**: solo `http`/`https`, redirecciones limitadas, hosts bloqueados, allowlist
  opcional, tiempo de espera y tamaño máximo de descarga.
- **El contenido ajeno es dato, no instrucción**: el texto de una fuente nunca se interpeta
  como orden del sistema.
- **Secretos**: bóveda Fernet en la base de datos; las claves de proveedor se cifran y solo
  se descifran en el servidor. Escaneo automático del árbol **y del historial de git**.
- **Contraseñas**: Argon2id, conservando la verificación de las contraseñas antiguas en
  PBKDF2 (migración sin reinicio de cuentas).
- **Sesión**: cookie `Secure` fuera de `local`, `SameSite`, duración limitada, 5 intentos
  fallidos → 429.
- **Presupuesto**: el gasto se verifica **antes** de la llamada y se registra con coste
  estimado real por proveedor.
- **La aprobación es humana**: ninguna versión de guion queda aprobada sin acción
  explícita, y editarla la anula.

## 10. Limitaciones conocidas

1. **Dependencias**: 2 avisos de seguridad en dependencias transitivas de Next (`postcss`,
   `sharp`). El parche compatible (Next 15.5.28) ya está aplicado; los avisos restantes
   exigen **Next 16**, un cambio ruptivo que no se aplica en la beta.
2. **`pip-audit` no está instalado** en la máquina de la entrega: la auditoría del lado
   Python no se pudo ejecutar (queda registrado, no se inventa).
3. **Sin locución**: el paso «Voz» persiste parámetros; no hay síntesis de voz.
4. **Animática, no render final**: el montaje de FFmpeg no lleva audio ni locución.
5. **Una sola base de datos en el despliegue**: la instalación editable de Python guarda
   rutas absolutas (hay que reinstalar si se mueve la carpeta).
6. **Sin entorno virtual por proyecto**: el backend usa el Python del sistema.
7. **Multiusuario**: el modelo es de un único editor (el control de concurrencia existe
   para dos sesiones del mismo editor, no para un equipo con roles).

## 11. Hoja de ruta posterior a la beta

1. **Remoto remoto** (GitHub/GitLab) y firma de los tags: la entrega es local y sin firma.
2. **Entorno virtual por proyecto** y scripts de arranque multiplataforma.
3. **Next 16** para cerrar los avisos de seguridad, con E2E completa antes.
4. **Auditoría de dependencias del lado Python** (`pip-audit`) en la CI.
5. **Métricas persistentes** (histórico, no solo ventana de 24 h).
6. **Papel de trabajo**: quién aprueba qué, con registro de auditoría.
7. **Validar los adaptadores** con credenciales reales (YouTube, Gemini, LLM, Búsqueda) y
   documentar el resultado en `PROVIDER_STATUS.md`.
8. **Prueba de humo del paquete exportado**: reimportar el `.zip` de producción en una
   instalación limpia.

Detalle en el plan maestro (`docs/agente/PLAN_MAESTRO.md`, «Ideas post-beta»).
