# SECURITY.md — Controles de seguridad, riesgos pendientes y políticas

## 1. Controles implementados (verificados con pruebas)

- **SSRF (conector web/RSS)**: esquema restringido a http/https; resolución DNS y bloqueo de rangos privados/loopback/link-local/reservados; allowlist explícita opcional (`NEURAL_ALLOWED_HOSTS`) y lista de bloqueo (`NEURAL_BLOCKED_HOSTS`); máx. 3 redirecciones verificadas una a una; tope de 5 MB y timeout de 20 s. Probado: bloqueo de 127.0.0.1 y 169.254.169.254, y descarga correcta contra servidor local permitido.
- **Contenido como dato**: el HTML se sanea (se eliminan script/iframe/object/embed/template) y el texto extraído es texto plano. El contenido de fuentes se trata como dato no fiable: los prompts enmarcan el contenido entre delimitadores e ignoran instrucciones internas. Prueba con texto malicioso («ignora todas las reglas», XSS, metadata de nube) verifica que no altera el comportamiento.
- **Autenticación**: sesión por cookie HttpOnly, SameSite=Lax, token aleatorio de 32 bytes guardado sólo como hash SHA-256; contraseñas PBKDF2-SHA256 (200k iteraciones). Todas las rutas privadas exigen sesión. Modo demo: crea sesiones marcadas `is_demo`; bloquea servicios reales; sólo para uso local (`NEURAL_DEMO_MODE=true`).
- **Costes**: servicios de pago desactivados por defecto; presupuesto diario configurable; cuando se agota, las llamadas facturables fallan de forma definitiva (sin reintentos que dupliquen cargos) y se registran como `blocked` en `usage_events`.
- **Secretos**: se leen de variables `NEURAL_*` / `.env` (fuera del repositorio); el endpoint `provider-status` informa sólo de booleanos de configuración; los logs y la exportación no contienen claves.
- **Integridad del paquete**: cada export registra SHA-256 y se sirve con cabecera `X-Package-Sha256`; un guion sin aprobación humana activa no puede figurar como aprobado ni en manifiesto ni en Markdown.
- **Concurrencia editorial**: edición con control optimista (HTTP 409); ambas revisiones se conservan; aprobar exige la versión más reciente con hash.

## 2. Riesgos pendientes (aceptados para el MVP)

1. **HTTPS/cookies seguras**: en producción detrás de TLS hay que activar `secure=True` en la cookie (parámetro preparado en `security.py`) y servir la web por HTTPS.
2. **Un solo editor**: la autorización es por sesión, no por recurso multiusuario. RLS/multiempresa queda para cuando exista Supabase Auth.
3. **CORS**: en desarrollo se permiten los orígenes localhost:3000; revisar antes de exponer.
4. **Descarga de archivos**: sólo texto (se rechaza PDF con mensaje claro); los límites de MIME/antivirus llegarán con el conector de audio.
5. **Rate limiting** de la propia API: no implementado (despliegue local); añadir proxy con límites antes de exponer a Internet.
6. **Validación de proveedores reales**: los adaptadores YouTube/Gemini/Spotify/búsqueda/LLM no se han ejecutado con credenciales; su comportamiento ante cuota, errores 4xx/5xx reales está probado sólo por diseño (manejadores de error tipados).
7. **Retención/borrado**: no hay política automática; el borrado de una fuente arrastra contenidos por cascade, pero no hay purga programada.

## 3. Políticas de contenido y derechos

- No se salta DRM ni se descarga audio de Spotify; no se instalan extractores que violen condiciones de plataforma.
- No se redistribuyen transcripciones ajenas completas: las transcripciones aportadas se almacenan de forma privada y sólo fragmentos/citas aparecen como referencia trazable.
- Los subtítulos de YouTube no se descargan en bloque: `captions.download` exige permiso de edición sobre el vídeo; el MVP no lo invoca.
- El paquete exportado etiqueta el storyboard como **prompts preliminares**: no presenta imágenes sintéticas como capturas documentales.
