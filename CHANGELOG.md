# Changelog

Todas las novedades de **neural.news** se anotan aquí.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el
versionado es [SemVer](https://semver.org/lang/es/).

## [1.0.0-beta.1] — 2026-11-03

Primera **beta local** del motor editorial `neural.news` con el NeuralStories
Studio integrado. Es una versión **local**: no se despliega, no se publica y no
requiere claves de proveedor ni Docker.

### Añadido

- **Recorrido editorial completo y verificable**: alta de fuente (YouTube,
  Spotify, web/RSS, texto propio) → candidatos → investigación con evidencia →
  guion → aprobación humana → lotes → paquete de producción exportable.
- **NeuralStories Studio en ocho etapas** (personaje, escenario, guion, voz,
  movimiento, referencias, producción), con **persistencia real en la base de
  datos**: lo que se guarda se conserva al recargar.
- **Cola de trabajos con lease y reintentos**, con motivo de fallo normalizado
  (`budget`, `material`, `connector`, `unknown`) y **log JSON por evento**.
- **Ninguna petición HTTP hace trabajo pesado**: transcripción, análisis,
  investigación, redacción y montaje salen de la petición a una cola.
- **Seguridad de despliegue**: `NEURAL_ENV=local|beta|prod` gobierna el modo
  demo, la cookie de sesión, la allowlist de red y el esquema; fuera de `local`
  la aplicación **no arranca** con el modo demo activo o con la contraseña de
  ejemplo.
- **Bóveda de secretos** (Fernet) en la base de datos y **Argon2id** para
  contraseñas, conservando la verificación de las contraseñas antiguas.
- **Observabilidad**: página `/ops` con salud real de base de datos, FFmpeg,
  yt-dlp y proveedores; **métricas** (p95, tasa de fallo, duración, profundidad
  de cola) y **alertas** (cola parada, lease vencido, presupuesto al 80 %,
  fallo repetido).
- **Presupuesto verificado antes de la llamada**, con coste estimado real por
  proveedor.
- **Rutas de modelo por tarea** con instantánea en el trabajo: cambiar la ruta
  después no altera un trabajo en marcha.
- **Subtítulos SRT/VTT** desde los segmentos de transcripción, con el texto
  íntegro, y **detección de contradicciones de cifras** que se *proponen* y
  nunca se aplican solas.
- **Centro de mantenimiento** en el Studio: auditoría SHA-256 de las fuentes y
  exportación del estado con manifiesto.
- **Verificación reproducible**: `scripts/bootstrap.ps1` (un comando),
  `scripts/start.ps1` / `scripts/stop.ps1`, `docs/entrega/verificar.ps1` (14
  comprobaciones con veredicto y log) y CI con la matriz real.
- **Auditorías ejecutables**: clases inexistentes o reimplementadas en línea,
  accesibilidad sin bloqueantes, secretos en el árbol y en el historial, mapa de
  estados generado desde el backend y evidencia del plan que tiene que existir.

### Corregido

- 21 defectos del recorrido crítico (NN-109) y 2 fallos de concurrencia
  (B23/B24), con prueba en rojo→verde para cada uno.
- La **aprobación raced**: aprobar una versión que ya no era la última.
- El **esquema vivo**: la base se crea solo con Alembic; `create_all` se
  eliminó porque nunca añade columnas.
- El **lease de la cola**: la reserva se confirma en la transacción y la
  renovación no bloquea al barrido.
- El **doble fallo silencioso** de `DossierPanel`, que hacía su propio `fetch`.
- La **etiqueta de la zona segura** del rótulo, que usaba márgenes ajenos.
- La **carrera del guion** al aprobar (B22) y el **número de versión** en
  borradores simultáneos (B24).
- La **clase `scrollbar-none`** y `studio-root`, que se usaban sin existir.
- La **ruta de instalación**: `start.ps1` no arrancaba la web en Windows, y
  `stop.ps1` no paraba el servidor del E2E.

### Changed

- El repositorio pasa a llamarse **`proyecto final`** y es la raíz real del
  repositorio Git.
- La versión del paquete (`package.json`, `pyproject.toml`, `__version__`) pasa
  a **1.0.0-beta.1** y se comprueba con un test de coherencia.
- **Next.js 15.1.6 → 15.5.28** (mismo *major*): parche de seguridad. `npm audit
  --omit=dev` baja de **3 vulnerabilidades (2 altas y 1 crítica)** a **2 (1 alta y 1
  moderada)**. Las que quedan son avisos de `postcss`/`sharp` **transitivos de
  Next** y solo se resuelven con **Next 16**, que es un cambio **ruptivo**: no
  se aplica en esta beta. Evidencia: `docs/entrega/evidencias/npm_audit.log`.

### Notas

- **Limitación conocida**: quedan 2 avisos de seguridad en dependencias
  transitivas de Next (`postcss`, `sharp`). Requieren Next 16 (ruptivo) o que
  Next los parchee; se documentan en vez de forzar una actualización mayor.
- `pip-audit` **no está instalado** en la máquina de la entrega, así que no se
  pudo auditar el lado de Python (`docs/entrega/evidencias/pip_audit.log`).
- El modo demo **no** llama a proveedores de pago: todo el contenido ficticio
  va marcado como tal.

[1.0.0-beta.1]: https://example.invalid/neural-news/releases/v1.0.0-beta.1
