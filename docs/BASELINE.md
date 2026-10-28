# BASELINE.md — Estado encontrado y decisiones (Etapa 0)

Fecha: 27–28 de octubre de 2026. Entorno: Windows 11 (win32 10.0.26100), Git Bash, Python 3.12.6, Node 24.20.0, npm 11.19.0, Docker 29.6.2 + Compose v5.5.0, git 2.47.0, uv 0.6.3.

## 1. Auditoría del entorno

- Carpeta de trabajo entregada: `C:\Users\haxth3\Documents\NeuralStories` — **vacía**.
- No se encontró código de NeuraldotAI, del pipeline audiovisual ni de Control Hub, ni hojas de personaje, plantillas ni documentación visual previa. No había nada que conservar ni riesgo de sobrescribir.
- Acceso a red verificado: registro npm y PyPI alcanzables (HTTP 200).
- Docker Desktop instalado pero con el daemon parado al inicio; se lanzó durante la Etapa 0. La verificación completa de `docker compose up --build` se documenta en OPERATIONS.md y en el informe final.

## 2. Decisión de estructura

Se crea un **monorepositorio nuevo** `neural-news/` dentro de la carpeta de trabajo, siguiendo la estructura de referencia del encargo (apps/api, apps/worker, apps/web, packages/contracts, infra, fixtures, docs). Motivos: no había repositorio que integrar; el monorepositorio mantiene API, worker e interfaz versionadas juntos; los adaptadores de proveedores quedan aislados para cambiarlos sin tocar el motor editorial.

## 3. Reutilización de activos

- **Nada previo reutilizable** (carpeta vacía).
- De las decisiones editoriales y audiovisuales del encargo se han incorporado como *especificación* (no como código): lotes de 5/10, estados diferenciados transcripción/análisis/metadatos, separación contenido editorial ↔ representación audiovisual, y personaje visual @neuraldotai referenciado **solo** en los prompts de imagen generados (no se ha reinventado hoja de personaje ni logo; el documento original no estaba disponible en el entorno).

## 4. Decisiones técnicas adoptadas (resumen)

| Decisión | Elección | Justificación breve |
|---|---|---|
| Base de datos por defecto en Windows | SQLite (storage/neural-news.db) + PostgreSQL vía docker compose | Permite arrancar sin Docker y sin claves; compose cubre el despliegue equivalente |
| Cola de trabajos | Tabla `jobs` con `dedupe_key` única, lease y reintentos acotados | Idempotencia y recuperación tras reinicio sin dependencias externas |
| Autenticación | Sesión con cookie HttpOnly + PBKDF2; modo demo marcado | MVP de un editor; Supabase Auth queda como evolución |
| Conector web/RSS | Implementación real (httpx + feedparser + BeautifulSoup) | Verificable sin claves, con protecciones SSRF y allowlist |
| YouTube / Spotify / Gemini / búsqueda / LLM | Adaptadores reales preparados **sin validar** + modo demo determinista | Nunca se declara validado lo no probado con credenciales |
| Producción de vídeo | Fuera del MVP; storyboard + prompts exportables | Según alcance §2.2 del encargo |
