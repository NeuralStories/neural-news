# SECURITY.md — Controles de seguridad, riesgos pendientes y políticas

## 1. Controles implementados (verificados con pruebas)

- **SSRF (conector web/RSS)**: esquema restringido a http/https; resolución DNS y bloqueo de rangos privados/loopback/link-local/reservados; allowlist explícita opcional (`NEURAL_ALLOWED_HOSTS`) y lista de bloqueo (`NEURAL_BLOCKED_HOSTS`); máx. 3 redirecciones verificadas una a una; tope de 5 MB y timeout de 20 s. Probado: bloqueo de 127.0.0.1 y 169.254.169.254, y descarga correcta contra servidor local permitido.
- **Corte real de la descarga (NN-111.6)**: el cuerpo se lee **por trozos** y se detiene en el límite. Antes se leía entero (`response.content`) y se recortaba después: un servidor hostil podía agotar la memoria del proceso antes de que el corte surtiera efecto.
- **DNS-rebinding (NN-111.7)**: además de comprobar el dominio, se comprueba la **dirección real de la conexión**. Si no es pública, o si no era una de las direcciones que se habían validado (la resolución cambió entre la comprobación y la conexión), el contenido **se descarta**. Probado con ambos casos.
- **Entorno explícito (NN-111.1, ADR-017)**: `NEURAL_ENV=local|beta|prod`. Fuera de `local`, la aplicación **no arranca** si el modo demo está activo, si falta la contraseña del editor o si sigue siendo la de ejemplo. Es preferible no levantar a levantar exponiendo el modo demo.
- **Cookie de sesión (NN-111.2)**: `HttpOnly` y **`Secure` fuera del entorno local** (antes `secure=False` estaba fijo y el comentario prometía una variable que no existía). `SameSite` y `Domain` son configurables (`NEURAL_SESSION_COOKIE_SAMESITE`, `NEURAL_SESSION_COOKIE_DOMAIN`).
- **Acceso de demostración (NN-111.3)**: el endpoint `/auth/demo` **sólo existe en el entorno local**; fuera de él responde 403 aunque el modo demo estuviera activo.
- **Puertas de los servicios de pago (NN-111.3)**: las rutas que llaman a un proveedor real (`research`, `draft`, `analyze`) dicen en voz alta cuando en un despliegue los servicios de pago están desactivados, en lugar de encolar un trabajo que no podrá completarse. Configurar el presupuesto con el modo demo activo se **rechaza**: antes devolvía un «ok» que no surtía efecto.
- **Límite de intentos de entrada (NN-111.10)**: los intentos fallidos se cuentan por dirección; tras 5, la entrada se rechaza con `429` durante el enfriamiento. Es un límite en memoria, por proceso (suficiente para un único editor; con varias instancias habría que compartirlo).
- **Contenido como dato**: el HTML se sanea (se eliminan script/iframe/object/embed/template) y el texto extraído es texto plano. El contenido de fuentes se trata como dato no fiable: los prompts enmarcan el contenido entre delimitadores e ignoran instrucciones internas. Prueba con texto malicioso («ignora todas las reglas», XSS, metadata de nube) verifica que no altera el comportamiento.
- **Autenticación**: sesión por cookie HttpOnly, SameSite=Lax, token aleatorio de 32 bytes guardado sólo como hash SHA-256; contraseñas PBKDF2-SHA256 (200k iteraciones). Todas las rutas privadas exigen sesión.
- **Costes**: servicios de pago desactivados por defecto; presupuesto diario configurable; cuando se agota, las llamadas facturables fallan de forma definitiva (sin reintentos que dupliquen cargos) y se registran como `blocked` en `usage_events`.
- **Secretos**: se leen de variables `NEURAL_*` / `.env` (fuera del repositorio); el endpoint `provider-status` informa sólo de booleanos de configuración; los logs y la exportación no contienen claves.
- **Errores al cliente (NN-109.5)**: el texto crudo de una excepción nunca llega al navegador. `neuralnews/errors.py` lo resume (sin rutas del sistema, sin secretos, sin correos) y el detalle completo queda en el registro.
- **Integridad del paquete**: cada export registra SHA-256 y se sirve con cabecera `X-Package-Sha256`; un guion sin aprobación humana activa no puede figurar como aprobado ni en manifiesto ni en Markdown.
- **Concurrencia editorial**: edición con control optimista (HTTP 409); ambas revisiones se conservan; aprobar exige la versión más reciente con hash.

## 1.1 Allowlist de red (`NEURAL_ALLOWED_HOSTS`)

**Decisión explícita, no un descuido.** Los hosts de la allowlist **se saltan el bloqueo de redes privadas**, y lo hacen **sólo** porque el operador los nombra uno a uno.

- **Motivo**: el conector web/RSS necesita descargar de fuentes internas o de redes locales (un feed de intranet, un servidor de pruebas). Sin la allowlist no habría forma de hacerlo sin abrir el SSRF entero.
- **Alcance**: el salto es **solo al bloqueo de direcciones privadas**. La allowlist **no** salta el esquema (sigue siendo http/https), ni el tope de bytes, ni el timeout, ni el límite de redirecciones.
- **Riesgo asumido**: quien añada un host a la allowlist abre ese host a la descarga desde el servidor. Por eso la lista debe ser **explícita y corta**, revisada, y nunca «*» ni un rango amplio.
- **Lista actual**: `[]` (vacía) — el producto no usa hoy ningún host de confianza.
- **Uso en pruebas**: el servidor de pruebas local (`127.0.0.1`) se declara en la allowlist **dentro de la prueba**, nunca en la configuración del producto.

## 2. Riesgos pendientes (aceptados para el MVP)

1. ~~**HTTPS/cookies seguras**~~ → **cerrado** (NN-111.2): la cookie va `Secure` fuera del entorno local. Queda pendiente **servir la web por HTTPS** y fijar `NEURAL_SESSION_COOKIE_DOMAIN`.
2. **Un solo editor**: la autorización es por sesión, no por recurso multiusuario. RLS/multiempresa queda para cuando exista Supabase Auth.
3. **CORS**: en desarrollo se permiten los orígenes localhost:3000; revisar antes de exponer.
4. **Descarga de archivos**: sólo texto (se rechaza PDF con mensaje claro); los límites de MIME/antivirus llegarán con el conector de audio.
5. **Rate limiting** de la propia API: implementado **para la entrada** (NN-111.10) y en memoria; el resto de la API sigue sin límite. Antes de exponer a Internet, añadir un proxy con límites.
6. **Validación de proveedores reales**: los adaptadores YouTube/Gemini/Spotify/búsqueda/LLM no se han ejecutado con credenciales; su comportamiento ante cuota, errores 4xx/5xx reales está probado sólo por diseño (manejadores de error tipados).
7. **Retención/borrado**: no hay política automática; el borrado de una fuente arrastra contenidos por cascade, pero no hay purga programada.
8. **Límite de entrada en memoria**: con varias instancias del proceso, el contador de intentos **no se comparte**. Para una instalación de un solo editor no importa; con varias, hay que moverlo a la base de datos o al proxy.
9. **DNS-rebinding**: la defence comprueba la dirección real de la conexión cuando el transporte la expone; si no la expone, no se puede comprobar y se acepta la conexión. En la práctica `httpx`/`httpcore` sí la dan.

## 3. Políticas de contenido y derechos

- No se salta DRM ni se descarga audio de Spotify; no se instalan extractores que violen condiciones de plataforma.
- No se redistribuyen transcripciones ajenas completas: las transcripciones aportadas se almacenan de forma privada y sólo fragmentos/citas aparecen como referencia trazable.
- Los subtítulos de YouTube no se descargan en bloque: `captions.download` exige permiso de edición sobre el vídeo; el MVP no lo invoca.
- El paquete exportado etiqueta el storyboard como **prompts preliminares**: no presenta imágenes sintéticas como capturas documentales.

## 4. Comprobación de secretos antes de entregar (NN-111.11)

El escaneo vive en `tools/scan_secrets.py` y comprueba, en el árbol **y en el historial** del repositorio:

- variables con forma de clave real (`sk-…`, `AIza…`, `ghp_…`, cadenas de 32+ caracteres tras `key`/`token`/`secret`/`password`);
- ficheros de entorno con valores no vacíos fuera de `.env.example`;
- las claves de ejemplo conocidas (`neural-demo`, `neural-local`).

Debe dar **0 hallazgos** antes de una entrega. Si aparece algo, **se rota la clave**, no se limpia el fichero: un secreto en el historial sigue en el historial.

