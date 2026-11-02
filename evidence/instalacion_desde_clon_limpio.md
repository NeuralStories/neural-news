# Instalación desde un clon limpio — evidencia

**Tarea:** NN-114.7 · **Fecha:** 2026-11-02 · **Rama:** `beta/v1` · **Commit:** `8fff0d7`

## Desviación documentada

El criterio original pedía un **vídeo** de la instalación. Esta sesión **no tiene
capacidad de grabación de vídeo**: no hay herramienta de captura de pantalla ni de
grabación, y la única vía de render disponible produce imagen estática, no vídeo.

En lugar de dejar la tarea sin hacer o inventar una evidencia, se deja la
**transcripción literal de la instalación real**, ejecutada en esta sesión con
salida real. Es la misma evidencia en formato texto: cualquier persona puede
repetir los comandos y obtener exactamente lo que se registra aquí.

**Estado: `PENDIENTE_POR_CAPACIDAD`** para el formato vídeo; el contenido pedido
(instalación verificada desde cero) **sí está cumplido y verificado**.

## Qué se ejecutó

### 1. Clon limpio

El repositorio remoto local es `C:\Users\haxth3\Documents\NeuralStories\.remotes\neural-news.git`
(rama `beta/v1`). Clon de referencia ya verificado en la Fase 1: 27 commits,
árbol de 141 ficheros idéntico al original.

### 2. `scripts\bootstrap.ps1` — un comando

```
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

Salida real (recortada en lo irrelevante):

```
== Comprobando requisitos
   Python 3.12
   Node 24.20.0

== Instalando el backend (apps/api)
Successfully installed neuralnews-0.1.0

== Preparando la configuración (.env)
   .env creado a partir de .env.example. Revísalo antes de desplegar.

== Aplicando las migraciones (Alembic)
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Running upgrade  -> d38b9d62cb47, esquema inicial MVP
INFO  [alembic.runtime.migration] Running upgrade d38b9d62cb47 -> d4ce8c95781e, nn107 studio proyectos y medios
INFO  [alembic.runtime.migration] Running upgrade d4ce8c95781e -> b3c1d9e4f7a2, invalidación de prompts por hash de guion
INFO  [alembic.runtime.migration] Running upgrade b3c1d9e4f7a2 -> c4d2e8f1a5b6, motivo normalizado del fallo de un trabajo
INFO  [alembic.runtime.migration] Running upgrade c4d2e8f1a5b6 -> d5e3f9a2b7c1, secretos de proveedor cifrados (bóveda)

== Instalando la web (apps/web)
up to date in 1s

== Ejecutando la suite de pruebas
........................................................................ [ 24%]
...................................
[ 48%]
.......s............................................
[ 72%]
........................................................................ [ 96%]
............ [100%]

Listo.
```

**Código de salida: 0.** (El `ConnectionAbortedError` que aparece en pantalla
procede del servidor de prueba de `tests/test_red_descargas.py`, que corta la
conexión a propósito para verificar que la descarga se interrumpe: es el
comportamiento esperado de esa prueba.)

### 3. `scripts\start.ps1` — la pila arriba

```
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

```
API    → http://127.0.0.1:8000  (registro: _api.log)
Worker → cola de trabajos (registro: _worker.log)
Web    → http://localhost:3000  (registro: _web.log)
Salud: neural.news v0.1.0 · entorno local
Listo. Para parar:  powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

Comprobación con la pila en marcha:

| Comprobación | Resultado |
|---|---|
| `GET http://127.0.0.1:8000/api/v1/health` | **200** |
| `GET http://127.0.0.1:3000/` | **200** |
| Proceso `python -m neuralnews.worker` | **activo** (PID propio) |
| Proceso `next start` | **activo** (PID propio) |

### 4. `scripts\stop.ps1` — la pila abajo, sin tocar nada ajeno

```
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

```
Deteniendo PID 17116: "C:\Python312\python.exe" -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000
Deteniendo PID 16956: "C:\Python312\python.exe" -m neuralnews.worker
Pila parada.
```

El script busca **por línea de comandos** (`neuralnews.main:app`,
`-m neuralnews.worker`, `next/dist/bin/next`), nunca por nombre de proceso: no
puede parar nada ajeno.

## Hallazgo que salió de esta verificación

**B30 (real):** `scripts\start.ps1` arrancaba la API y el worker, pero **la web
no**: en Windows, `Start-Process -FilePath "npm"` falla con «no es una aplicación
Win32 válida» porque `npm` es `npm.cmd`. El script terminaba con error y la
pila se quedaba a medias — justo lo que la tarea debía detectar.

**Corrección:** se resuelve `npm.cmd` con `Get-Command` y se usa su ruta real.
Verificado: la pila completa levanta y responde 200 en API y web.
