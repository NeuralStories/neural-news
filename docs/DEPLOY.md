# DEPLOY.md — Lista de comprobación para desplegar la beta

Cada punto se marca ** sólo con evidencia ejecutada**: el comando y su salida, o la prueba
supérada. «Debería funcionar» no vale.

**Antes de empezar:** la aplicación **no arranca** con una configuración incoherente
(`NEURAL_ENV=beta|prod` con el modo demo activo, sin contraseña, o con la contraseña de
ejemplo). Si la API levanta, el punto 3 ya está comprobado.

---

## 1. Repositorio y código

- [ ] `git -C neural-news status` → **árbol limpio**, sin cambios sin commitear.
- [ ] `git -C neural-news log --oneline -1` → el commit esperado, y `git push` al remoto hecho.
- [ ] `git -C neural-news branch` → la rama de despliegue (`beta/v1` o `main`).
- [ ] Clonar en limpio y comprobar que el árbol trae **todo**:
      `git clone <remoto> && cd neural-news && git log --oneline | wc -l`.

## 2. Dependencias

- [ ] Python ≥ 3.12: `python --version`.
- [ ] `pip install -e ".[dev]"` en `apps/api` (incluye `alembic` y `pytest`).
- [ ] Node ≥ 20 y `npm ci` en `apps/web`.
- [ ] FFmpeg disponible en el `PATH` del servidor **y** del worker: `ffmpeg -version`.
- [ ] `yt-dlp` disponible (opcional, sólo para transcripción automática):
      `yt-dlp --version`.

## 3. Configuración

- [ ] `.env` creado a partir de `.env.example` y **fuera** del repositorio.
- [ ] `NEURAL_ENV=beta` (o `prod`).
- [ ] `NEURAL_DEMO_MODE=false` — **obligatorio** fuera de local (la app no arranca si no).
- [ ] `NEURAL_ADMIN_PASSWORD` con una contraseña **distinta** de `neural-demo`.
- [ ] `NEURAL_DATABASE_URL` apuntando a PostgreSQL.
- [ ] `NEURAL_ALLOWED_HOSTS` revisada: lista **corta y explícita** (ver `SECURITY.md` §1.1).
- [ ] `NEURAL_SESSION_COOKIE_DOMAIN` fijado si el dominio es propio.
- [ ] `NEURAL_SESSION_COOKIE_SAMESITE` según el despliegue (`lax` o `strict`).
- [ ] Claves de proveedores sólo si se usan; `GET /api/v1/provider-status` informa de
      booleanos, nunca de valores.

## 4. Esquema de la base de datos

- [ ] `alembic current` → la revisión **head**.
- [ ] `alembic upgrade head` sobre la base de datos **de despliegue** → sin errores.
- [ ] Ciclo completo verificado en una base limpia:
      `upgrade head` → `downgrade -1` → `upgrade head` (**hecho el 02/11/2026**:
      `d38b9d62cb47 → d4ce8c95781e → b3c1d9e4f7a2 → c4d2e8f1a5b6`).
- [ ] `python tools/compare_schema.py <url>` → «El esquema coincide EXACTAMENTE con los
      modelos» (**hecho el 02/11/2026** en PostgreSQL **y** en SQLite).
- [ ] Copia de seguridad **anterior** a la migración, verificada:
      `pg_dump` + SHA-256 + restauración en una base limpia.

## 5. Secretos

- [ ] `python tools/scan_secrets.py .` → **0 hallazgos** (los avisos de la contraseña de
      ejemplo se revisan a ojo).
- [ ] `.env` no está versionado: `git check-ignore -v .env`.
- [ ] Si el escaneo finds algo real: **rotar la clave** (limpiar el fichero no la saca del
      historial).

## 6. Pruebas

- [ ] `python -m pytest tests -q` → **0 fallos** (referencia 02/11/2026: 217 passed,
      1 skipped).
- [ ] `npx tsc --noEmit` → 0 errores.
- [ ] `npm run build` → compila (con `NEURAL_ENV=local` o `NEURAL_API_URL` puesta).
- [ ] `npm run build` **sin** `NEURAL_API_URL` y con `NEURAL_ENV=beta` → **falla** con
      mensaje explícito (es lo correcto: la web no debe compilar sin destino).
- [ ] `npx playwright test` → todo en verde (requiere API, worker y web en marcha).
- [ ] `python tools/compare_schema.py` sobre la base de despliegue.

## 7. Puesta en marcha

- [ ] API: `python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000`.
- [ ] Worker: `python -m neuralnews.worker` (proceso **separado**).
- [ ] Web: `NEURAL_API_URL=… npm run build && npm run start`.
- [ ] `GET /api/v1/health` → `{"ok": true, …}`.
- [ ] El log del worker escribe **JSON por evento** (una línea por trabajo, con `job_id`,
      `status`, `duration_s`, `error_kind`).
- [ ] La cola se vacía: los trabajos pasan a `DONE` y ninguno se queda en `QUEUED`.

## 8. Verificación funcional (recorrido de la beta)

- [ ] Entrar con la contraseña real (el acceso demo **no existe** fuera de local).
- [ ] Crear una fuente de texto → aparece en la tabla con un estado legible.
- [ ] «Buscar transcripción» → la interfaz **responde al instante** y avisa de que está en
      cola; el resultado llega después.
- [ ] Noticia candidata → investigar → generar guion → editar → **guardar** → aprobar.
- [ ] Studio: las ocho etapas persisten; recargar y comprobar que todo sigue ahí.
- [ ] Importar un MP4 en una toma → el sondeo se hace en segundo plano y la duración y la
      orientación aparecen reales.
- [ ] «Validar y montar lo disponible» → la interfaz responde al instante y el motivo
      (falta material) queda a la vista.

## 9. Red y proxy

- [ ] La web se sirve por **HTTPS**.
- [ ] La cookie de sesión llega con `Secure` (comprobar en las herramientas del navegador).
- [ ] `SameSite` y `Domain` correctos para el dominio real.
- [ ] CORS: `NEURAL_CORS_ORIGINS` con **sólo** los orígenes reales.
- [ ] El proxy tiene límites de peticiones (la API sólo limita la entrada).

## 10. Operación

- [ ] Copia de seguridad de la base de datos **verificada** (restauración probada).
- [ ] Copia del almacenamiento (`storage/media`, `storage/montage`).
- [ ] `GET /api/v1/usage` → el consumo y el presupuesto son legibles.
- [ ] `GET /api/v1/jobs` → los trabajos fallidos muestran su motivo **normalizado**
      (`budget`, `material`, `connector`, `unknown`) y su etiqueta.
- [ ] Alguien sabe qué hacer cuando el worker se cae: al arrancar recupera los trabajos
      con el lease caducado, y además los va barriendo.

## 11. Antes de abrir la beta a otra persona

- [ ] `ESTADO_REAL.md` al día (lo que funciona y lo que no).
- [ ] `docs/PROVIDER_STATUS.md` honesto: qué proveedor está **validado con credenciales**
      y cuál no.
- [ ] Los límites de la beta escritos en la interfaz, no sólo en la documentación.

---

**Registro de la comprobación del 02/11/2026** (instalación local de desarrollo):
puntos 4, 5, 6 (suite, tipos, build, esquema en SQLite y PostgreSQL) y 8 verificados en
ejecución. Los puntos 1–3, 7 y 9–11 dependen del entorno real de despliegue y **no** se
dieron por buenos sin ejecutarlos allí.
