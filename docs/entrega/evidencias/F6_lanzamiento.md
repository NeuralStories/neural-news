# F6 — Lanzamiento local en modo producción

**Fecha:** 2026-11-03 09:50:08 · **URL web:** http://localhost:3000 · **URL API:** http://127.0.0.1:8000

## Comprobación HTTP

- Web `GET http://localhost:3000/` → **200**
- API `GET http://127.0.0.1:8000/api/v1/health` → **200**

`json
{"ok":true,"app":"neural.news","version":"1.0.0-beta.1","demo_mode":true,"env":"local","checks":{"database":{"ok":true,"detalle":"responde"},"ffmpeg":{"ok":true,"detalle":"ffmpeg version 8.1.1-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers","necesario_para":"montaje con FFmpeg"},"yt_dlp":{"ok":true,"detalle":"C:\\Users\\haxth3\\Documents\\NeuralStories\\tools\\yt-dlp.exe","necesario_para":"transcripción automática de YouTube"},"providers":{"ok":true,"detalle":"0 de 5 con clave","items":[{"key":"llm_api_key","configurado":false},{"key":"search_api_key","configurado":false},{"key":"youtube_api_key","configurado":false},{"key":"gemini_api_key","configurado":false},{"key":"spotify_access_token","configurado":false}]},"presupuesto":{"ok":true,"detalle":"modo demo: los servicios de pago están bloqueados"}}}
`

## PIDs de la instancia en marcha

`json
{
  "api": 33000,
  "worker": 20568,
  "web": 10504
}
`

## Prueba rápida de Playwright contra esta instancia

- Script: `apps/web/scripts/prueba_rapida_beta.mjs` (7 comprobaciones)
- Resultado: **7/7 PASA** (web responde, pantalla de acceso con modo demo, el
  modo demo abre el producto, el pie declara `v1.0.0-beta.1`, sin errores de
  JavaScript, sin recursos rotos y la API con la misma versión).

## Comandos

`powershell
# Arranque (multiplataforma, sin Bash ni WSL)
node scripts\beta_start.mjs
# o, en Windows
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# Parada
node scripts\beta_stop.mjs
# o
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
`

## Nota sobre el entorno

La instancia queda **en marcha** (los procesos están desacoplados del lanzador y
sobreviven a su salida). Los PIDs est`an arriba. Para pararla: `node scripts/beta_stop.mjs`.
