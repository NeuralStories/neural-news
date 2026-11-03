# PROVIDER_STATUS.md — Estado real de cada proveedor

Fecha de verificación: 28 de octubre de 2026. Entorno: Windows 11, Python 3.12.6, sin claves externas configuradas durante el desarrollo.

Convención de estados:
- **mock**: sólo implementación simulada (demo).
- **implementado**: código real escrito; NO ejecutado con credenciales reales.
- **probado**: ejecutado y verificado con credenciales reales durante este MVP.
- **error conocido**: fallo conocido documentado.

| Proveedor | Clave necesaria | Estado | Detalle y fecha |
|---|---|---|---|
| Texto/archivos aportados (manual) | ninguna | **probado** (28-10-2026) | Implementación completa y pruebas automáticas; funciona sin claves |
| Artículos web y RSS | ninguna | **probado** (28-10-2026, servidor de prueba local) | httpx+feedparser+BeautifulSoup; SSRF bloqueado (rangos privados), allowlist explícita, límites de bytes/tiempo/redirecciones. **No probado contra sitios públicos reales** (no se ejecutaron descargas externas en el desarrollo) |
| YouTube (metadatos, Data API v3) | `NEURAL_YOUTUBE_API_KEY` | **implementado, sin validar** | Adaptador `videos.list` escrito según documentación vigente en el momento de construirlo; sin clave no se ha ejecutado ninguna llamada real |
| YouTube (análisis por Gemini) | `NEURAL_GEMINI_API_KEY` | **implementado, sin validar** | Llamada REST `generateContent` con `fileData` (URL pública de YouTube) según docs del momento; salida SIEMPRE marcada `VIDEO_ANALYSIS`, nunca transcripción literal |
| YouTube (demo) | ninguna | **probado** | Vídeo ficticio: transcripción simulada + análisis simulado, con marcas temporales |
| Spotify (metadatos, Web API get-an-episode) | `NEURAL_SPOTIFY_ACCESS_TOKEN` (autorización de usuario) | **implementado, sin validar** | El endpoint exige token de usuario; no se ha ejecutado con token real. Sin transcripción: estado «Solo información básica» |
| Spotify (demo) | ninguna | **probado** | Episodio ficticio METADATA_ONLY con aviso comprensible |
| Transcripción de audio (ASR) | (proveedor por decidir) | **mock** (sólo interfaz) | El MVP acepta transcripciones aportadas por el usuario; ASR real queda pendiente |
| Búsqueda para investigación (Brave compatible) | `NEURAL_SEARCH_API_KEY` | **implementado, sin validar** | Adaptador REST escrito; en demo, evidencia ficticia con dominio `.invalid` marcada DEMO |
| Modelo editorial (extracción/guiones, REST compatible OpenAI) | `NEURAL_LLM_API_KEY` | **implementado, sin validar** | Adaptador escrito con validación de esquema y corrección acotada de JSON; en demo, generador determinista probado |
| Prompts de imagen / storyboard | ninguna | **probado** | Generador local determinista; no llama a APIs ni gasta créditos |
| Google Flow / APIMart (vídeo) | — | **fuera del MVP** | Se entregan prompts y storyboard para uso manual. Nada de APIMart/MCP ha sido descubierto, autenticado ni validado en este proyecto |

## Claves que harían falta para validar los adaptadores reales

1. `NEURAL_YOUTUBE_API_KEY` — proyecto de Google Cloud con YouTube Data API v3 habilitada.
2. `NEURAL_GEMINI_API_KEY` — clave de Google AI Studio con facturación si el volumen lo requiere.
3. `NEURAL_SPOTIFY_ACCESS_TOKEN` — app en Spotify Developer con OAuth de usuario (scope episode-read).
4. `NEURAL_SEARCH_API_KEY` — suscripción Brave Search API (o adaptar base URL a otro buscador).
5. `NEURAL_LLM_API_KEY` — clave de un proveedor compatible OpenAI.

Las claves se cargan por `.env` (ver `.env.example`); nunca por chat ni dentro del código. Hasta entonces, el modo demo cubre todo el flujo.
