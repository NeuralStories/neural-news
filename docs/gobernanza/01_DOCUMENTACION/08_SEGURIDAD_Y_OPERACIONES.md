# Seguridad, recuperación, privacidad, derechos y despliegue

## Modelo de amenazas
- RSS/HTML/PDF/transcripciones maliciosos: prompt injection, XSS, malware y exfiltración de claves. Tratarlos como texto no confiable; no otorgarles herramientas ni instrucciones. Limpiar HTML/renderizar texto seguro, deshabilitar enlaces externos de editores hasta saneamiento.
- SSRF al recuperar noticias o probar endpoints: DNS/IP pública, validar redirecciones y rango de cada salto, bloquear link-local y metadata (`169.254.169.254`), localhost y red privada excepto endpoints locales ADMIN preaprobados y segregados.
- Secrets: `.env` sin repo, clave maestra fuera DB, API keys cifradas autenticadamente, nunca retornar en GET, sustituir no mostrar, políticas de rotación, escaneo del repositorio/logs.
- Usuarios: sesiones hash, CSRF/orígenes, cookie Secure HttpOnly SameSite, Argon2id, rate limit login, RBAC real en API (no solo botón oculto), deshabilitar valores por defecto de producción.
- Modelo remoto: fuga de datos editoriales y costes; opt-in por proveedor, registrar qué se envía sin almacenar material sensible en texto plano de logs. Tasas, cuotas y moneda configurables.
- Vídeo/medios: tamaño/codec/Tipo MIME/ffprobe, rutas seguras, evitar zip-slip y path traversal, nombres aleatorios, límite de decodificación, accesibilidad privada hasta aprobación, licencias y fuente en DB.
- Publicación: aprobación explícita, revisión legal de derechos, atribución de material, distinción animación generativa de evidencia, verificación previa de subtítulos/cifras.
- Dependencias: versiones soportadas, lockfiles, npm/pip audit, escaneo de imágenes, actualizaciones controladas. No usar paquetes comprometidos ni `flow-sdk` no evaluado.

## Política de gastos
- Por defecto `paid_allowed=false`, `limit=0` para todas las rutas.
- Reservar coste estimado antes de lanzar tarea; si precio desconocido y tarea pagada, bloquear. Al éxito conciliar uso real; fallos de conexión con resultado remoto incierto requieren revisión humana.
- Presupuesto por lote, noticia, tarea, proveedor y día; el límite efectivo es el más restrictivo.
- Reintento con backoff exponencial+ jitter únicamente ante fallos seguros idempotentes. Timeout remoto no significa tarea no ejecutada.

## Backup / restauración
- PostgreSQL `pg_dump --format=custom` con checksum e inventario + medios por hash y catálogo, copia en destino protegido. Clave maestra fuera de backup de DB y con procedimiento de recuperación independiente.
- Prueba periódica de restauración a DB **aislada**, migraciones y verificación de cuenta de tablas, historias, guiones, assets y clips.
- Antes de cambios de esquema producción: backup, preflight, migración transaccional si procede, prueba, rollback compatible; nunca borrar datos productivos automáticamente.
- Recuperar workers: jobs en `RUNNING` con lease expirado se reevalúan; gastos remotos inciertos no se repiten a ciegas.

## Observabilidad
request_id, job_id, story_id, plan_revision, provider_id, estado, duración, uso/coste si disponible, tipo de error. Métricas de ratio error por etapa, latencia, reintentos, costes, tasa de claims sin evidencia, escenas bloqueadas, créditos gastados, contenidos aprobados. No almacenar prompts completos con secretos ni textos privados en logs generales.

## Instalación objetivo
Desarrollo Windows con Docker Desktop/WSL2 si está disponible; Docker Compose: postgres, api, worker, web, volúmenes privados (sin publicar PostgreSQL). `./scripts/bootstrap` comprueba Node/Python/Docker/ffmpeg y muestra bloqueos con alternativas. En producción TLS reverse proxy, dominios y CORS cerrados, secretos externos, backups monitorizados. No abrir a Internet la API de LM Studio/Ollama.

## Plan para pérdida de suministro
- Sin API IA: fixtures locales deterministas para demostrar orquestación, etiquetados DEMO; editor humano sigue funcionando.
- Sin Flow: export manual de prompts y checklist; no afirmar generación exitosa.
- Sin PostgreSQL: solucionar infra primero; no cambiar a SQLite sin ADR y prueba de futura migración.
- Sin vídeos/voz: escena `PENDING_ASSET`, animática con placeholder visible; ningún falso render final.
