# NN-107 — Implementación realizada: la lógica de Flow vuelve a neural.news (operativa)

**Fecha:** 31/10/2026 · **Rama:** `nn-107-reintegracion-flow` · **Estado: OPERATIVA en local, 100 % sin Docker**

> **NO APROBADO — PENDIENTE DE REVISIÓN DEL PROPIETARIO.** Instantánea inmutable entregada para revisión; nada se fusiona a `main` ni se da por definitivo hasta aprobación explícita. **Todo el desarrollo y la operación son sin Docker**, con PostgreSQL local de binarios nativos.

Este documento resume qué se implementó, cómo arrancarlo y qué evidencia lo respalda. El detalle
fase a fase está en `TASK_NN-107_REINTEGRACION_FLOW.md` (docs/gobernanza) y el estado honesto módulo a
módulo en `ESTADO_REAL.md`.

---

## 1. El punto de partida y el resultado

La lógica creativa de Flow (NeuralStories Studio, 8 etapas: Noticias · Personaje · Fondo · Guion ·
Voz · Movimiento · Referencias · Resultado) había sido eliminada. Se recuperó de una fotografía del
29/10 (`REVISION_UNIFICACION_NEURAL_NEWS.zip`, 226 entradas, SHA-256 verificado) y de las 17
fuentes originales de Flow (4.774 líneas, 17/17 con hash contra manifiesto), se auditó
(diferencial: 12 idénticas + 5 modificadas) y se **reintegró completa y funcional** en la app
única `neural-news`, mejorándola:

- **Una sola aplicación y una sola fuente de datos**: el Studio vive dentro de la web Next.js
  (`/estudio`, sin iframe) y guarda todo en la base de datos vía la API. Nada solo en el
  navegador; sin redacciones paralelas.
- **Runtime de Flow sustituido por un adaptador**: fuera del editor de Google Flow toda
  generación queda honestamente **BLOCKED** con paquete manual; nada simulado.
- **Producción audiovisual de verdad**: director determinista (cap. 7), prompts versionados por
  toma, `FlowManualPackage.v1` exportable e importación del MP4 generado externamente con
  aprobación humana.

## 2. Qué funciona hoy (todo probado con tests automáticos y E2E en navegador real)

| Bloque | Estado |
|---|---|
| Proyectos con persistencia real (CAS 409, revisiones inmutables por paso) | FUNCIONA |
| Biblioteca de medios (subida idempotente por SHA-256, aprobación humana) | FUNCIONA |
| Studio de 8 etapas nativo en la web, guardado por API, sin iframe | FUNCIONA |
| Conexión editorial: dossier de la noticia vinculada (fuentes + afirmaciones y estados) | FUNCIONA |
| Director audiovisual determinista (beats continuos sin cortes de 8 s impuestos, tomas por capacidad del proveedor, tipo de recurso con justificación) | FUNCIONA |
| Prompts versionados por toma + FlowManualPackage exportable | FUNCIONA |
| Importación de MP4 externo asociado a toma/revisión + aprobación humana | FUNCIONA |
| Gráficos programáticos (SVG determinista con valores exactos y fuente) + invalidación dirigida al cambiar el guion | FUNCIONA (solo plantilla BAR en esta ventana) |
| Regresiones de auditoría F-01…F-10 (maxDotAi, nada aprobado por defecto, Algenib = hipótesis, importar ≠ verificado, dedup canónica antes que léxica, export ≠ backup BD…) | FUNCIONA |
| Prueba real contra PostgreSQL local (sin Docker) | FUNCIONA |

**Declarado NO_IMPLEMENTADO (Etapa B/C):** render/montaje real con B-roll y voz (el FFmpeg
portado del 29/10 es una simulación técnica y está etiquetado como tal), TTS, episodios de 5/10,
director LLM completo, gráficos line/timeline/percentage, publicación en plataformas.

## 3. Commits (rama `nn-107-reintegracion-flow`)

| Commit | Fase | Contenido |
|---|---|---|
| `b7ed981` | F1 | Modelos + migración `d4ce8c95781e` + API de proyectos/Studio con CAS + biblioteca de medios |
| `1fe68d3` | F2 | Studio unificado en `apps/web/features/studio/` (17 fuentes con hash verificado) + página nativa `/estudio` + adaptador `flow/` |
| `59e45d5` | F3 | Director determinista, prompts versionados, FlowManualPackage, importación MP4 |
| `96a5bfd` | F4+F5 | Dossier editorial, gráficos programáticos, invalidación dirigida, regresiones F-01…F-10, `ESTADO_REAL.md` |
| `48381bf` | — | Prueba real contra PostgreSQL local sin Docker |

## 4. Cómo arrancarlo (todo en local, sin Docker)

### 4.1 PostgreSQL local (ya instalado en `Documents/NeuralStories/pglocal`)

```bash
# arrancar (si no está corriendo)
C:/Users/haxth3/Documents/NeuralStories/pglocal/pgsql/bin/pg_ctl.exe \
  -D C:/Users/haxth3/Documents/NeuralStories/pglocal/data \
  -l C:/Users/haxth3/Documents/NeuralStories/pglocal/logfile.log -o "-p 5433" start
# parar
... pg_ctl.exe -D .../pglocal/data stop
```

BD: `neuralnews` (usuario `neural`, auth trust solo-local, puerto 5433).
Migraciones ya aplicadas (`alembic upgrade head` verificado en PG).

### 4.2 API + worker (FastAPI) — contra PostgreSQL

```bash
cd Documents/NeuralStories/neural-news
export NEURAL_DATABASE_URL="postgresql+psycopg://neural@127.0.0.1:5433/neuralnews"
python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000      # API
python -c "from neuralnews.worker import run; run()"                    # worker (cola)
```

### 4.3 Web (Next.js) — http://localhost:3000

```bash
cd Documents/NeuralStories/neural-news/apps/web
npm run build   # solo la primera vez o tras cambios
npm run start
```

### 4.4 Entrar

Abrir **http://localhost:3000** → «Entrar en modo demo» → **Estudio** (o directo a
`/estudio?project=<id>`). La primera ejecución crea el proyecto desde el lanzador del Studio.

## 5. Verificación operativa (prueba de humo del 31/10, sobre la pila en marcha)

Ejecutada por HTTP contra `localhost:3000` con PostgreSQL local:

1. Demo login `200`
2. Fuente de texto → worker → historia editorial creada
3. Proyecto con la noticia vinculada (queda activa: R-BUG-1)
4. Guion del proyecto guardado con CAS
5. Director determinista: **3 beats, 2 tomas** `[DATA_GRAPHIC, FLOW_MAXDOTAI]`
6. Toma + prompt **v1** → `PROMPT_LISTO`
7. `FlowManualPackage.v1` (personaje maxDotAi, ratio 9:16, checklist de 5 puntos)
8. MP4 externo importado → `IMPORTADA` con SHA-256 (`44eeb5c5…`; probe `FAILED` honesto: sin
   ffprobe en PATH; instalar FFmpeg aporta duración/resolución)
9. Aprobación humana → `APROBADA`
10. Gráfico programático: SVG renderiza el valor exacto `12 %`
11. Estado final persistido en PostgreSQL: ratio intacto, noticia activa, toma APROBADA

## 6. Pruebas (evidencia)

- **API (01/11/2026, tras NN-109):** **154 passed, 1 skipped, 0 fallos** (antes de NN-109: 139 passed, 1 skipped).
  Las 15 pruebas nuevas de `tests/test_nn109_defectos.py` se han verificado **rojas sobre el código original**
  (8 de 15 fallaban) y **verdes** después del arreglo.
- **API (antes):** 107 passed, 0 fallos (+ `test_postgres_projects.py` PASSED contra PG 16.9 real:
  ciclo crear → editar → CAS → MP4 → reiniciar → recuperar).
- **Tipos y build (web):** `tsc --noEmit` sin errores; `next build` compila (9 páginas estáticas) con
  `NEURAL_ENV=local` y **falla a propósito** sin `NEURAL_API_URL` fuera de local (hallazgo B9).
- **E2E navegador real (Edge):** `studio-reintegration.spec.ts` (8 etapas + persistencia tras
  recargar) y `vertical-production.spec.ts` (director → prompt → paquete → importar → aprobar).
- **Migraciones:** ciclo `upgrade → downgrade → upgrade` verificado en SQLite y PostgreSQL.
- **Regresiones de auditoría:** F-01…F-10 consolidadas en `tests/test_regressions_f01_f10.py`.
  La comprobación de identidad F-01 se ha ampliado para recorrer **todo** el árbol del Studio:
  al hacerlo ha aparecido una regresión real (la identidad «NeuralDotAI» en 5 componentes, que la
  lista fija de ficheros no cubría). Ver `ESTADO_REAL.md` B17.
- **Integridad de activos:** las 17/17 fuentes de Flow contrastan con `reports/manifest.json` (SHA-256).

## 7. Pendientes honestos

- **Pendiente_pOR_ACTIVO:** handle real de maxDotAi, hoja maestra aprobada y un MP4 real de Flow
  (la importación ya está probada con archivo de prueba; el flujo es idéntico).
- **Pendiente_por_API:** generación programática de imagen/vídeo (futuro adaptador autorizado).
- **Etapa B/C:** render real, animática, TTS, episodios 5/10, director LLM, gráficos
  line/timeline/percentage, publicación.
- Nota: `probe_status` de los MP4 será `OK` instalando FFmpeg y añadiéndolo al PATH.
- **Docker: eliminado del flujo por decisión del propietario.** La base de datos es PostgreSQL local de binarios nativos (§4.1); el `infra/docker-compose.yml` del repositorio queda sin uso.


---

# FASES 1–4 — Integración y primera producción real (01/11/2026)

## FASE 1 — Integración de NN-107 en `main` ✅
- Fusión controlada `--no-ff` sin conflictos (merge `0647489`); punto de reversión etiquetado `pre-merge-main` (dd7c414).
- Verificación tras fusionar en `main`: 117 tests + 1 skip, build limpio, app integrada contra PostgreSQL local (proyecto 2 recuperado tras reinicio).
- **Invalidación exclusiva** (nuevo): `prompt_packages.source_script_hash` + `generated_takes.needs_review` (migración `b3c1d9e4f7a2`). Cambiar el guion marca `⚠ Revisar: el guion cambió` SOLO en las tomas cuyo prompt dependía del texto; recompilar despeja la marca; el MP4 importado nunca se destruye.

## FASE 2 — PILOTO 001 ✅ (proyecto #12, http://localhost:3000/estudio?project=12)
- Noticia real: OPA de Anthropic (Reuters, nov 2026; valoración 61,5→380→965 G$). Fuente manual con snapshot y referencia reuters.com/technology/.
- Guion periodístico natural (~150 palabras ≈ 53 s a 2,85 pal/s) editable; afirmaciones UNVERIFIED hasta contraste humano.
- maxDotAi PENDIENTE_DE_VINCULAR (sin activos no se inventa nada); plató CRT PENDIENTE_DE_APROBACIÓN.
- Director: 7 tomas (2 FLOW_MAXDOTAI, 4 GENERATIVE_BROLL, 1 DOCUMENTARY en el primer plan; línea de tiempo revisada con TITLE_CARD + DATA_GRAPHIC para montaje).
- Gráfico programático con valores exactos 61,5/380/965 (SVG en la UI) + FlowManualPackage por toma.

## FASE 3 — Motor de montaje real ✅ (PARCIAL por diseño: animática sin locución)
- FFmpeg 9.0.2 binarios nativos en `ffmpeg-local/` (sin Docker).
- `services/montage.py`: timeline desde shots/takes persistidos; clips MP4 reales + tarjetas programáticas (Pillow, valores exactos); concat 1080x1920/30fps; salida etiquetada ANIMÁTICA (no render final).
- API: `GET/POST /v1/projects/{id}/montage(.mp4)` con lista exacta de materiales ausentes.
- Validación: 2 tests (MP4 reales vía testsrc; lista de faltantes honesta). Animática del piloto: h264 1080x1920, 10,5 s programáticos; 5 tomas pendientes listadas con motivo.

## FASE 4 — UX ✅
- Sección «Montaje» en Producción: Validar y montar lo disponible → previsualización del MP4 + lista de pendientes por ventana. Sin pantallas técnicas duplicadas.

## Pruebas al cierre de las FASES 1–4
- API: **119 passed, 0 fallos, 1 skip** (skip = test PG que con `NEURAL_TEST_POSTGRES` pasa: verificado 1 passed).
- E2E Edge: **2 passed** (studio-reintegration 18,7 s; vertical-production 12,7 s).
- Commit de referencia: `d701099` en `main`.


## FASE 3/4 — Lagunas cerradas tras la revisión del propietario (01/11/2026)

1. **Transiciones en el montaje (FASE 3 punto 5) — IMPLEMENTADO.** El director asigna ahora a cada
   toma un movimiento del catálogo (sin repetir el mismo en tomas consecutivas) y una transición de
   entrada (corte seco rotando con glitch RGB / whip pan / push zoom). El montador aplica
   transiciones reales: xfade (fade/wipeleft/zoomin) de 0,4 s entre segmentos y concat seco para
   los cortes directos; la duración del MP4 refleja el solape. La respuesta del montaje expone las
   transiciones aplicadas. Tests: `test_transiciones_movimiento.py` (3 passed: movimientos sin
   repetición consecutiva, xfade aplicado con acortamiento real, movimiento llegado al prompt).
2. **Movimiento del catálogo en las tomas (FASE 2) — IMPLEMENTADO.** Las 7 tomas del PILOTO 001
   fueron replanificadas con `movement_id` + `movement_instruction` (lateral_slide_in,
   chest_punch_zoom, subtle_dolly, horizontal_flip…) y sus prompts regenerados a v2 incluyendo el
   movimiento y la transición de entrada. La animática del piloto se reconstruyó con las
   transiciones (h264 1080x1920, 25,6 s según ffprobe; evidencia en
   `../REVISION_NN107_FLOW/evidencia/piloto001_animatica_916.mp4`).
- Corrección adicional: `run_director` desvincula tomas/beats antes de sustituir la línea de
  tiempo (FK violations en PostgreSQL al replanificar proyectos con tomas).
- Pruebas al cierre: **122 passed, 0 fallos, 1 skip** + 2 E2E en verde.


## Unificación visual completa (01/11/2026, tras revisión del propietario)

El propietario detectó que el Studio era visualmente otra aplicación. Corregido:

- **Paleta unificada**: slate→neutral y ámbar/naranja→sky en los 15 componentes del Studio
  (mismos neutros y mismo acento sky que Fuentes/Noticias/Lotes/Configuración).
- **Iconos Material retirados** (dependencia de Google Fonts eliminada del layout); los estados
  se comunican con texto y badges del sistema (.badge-* de globals.css).
- **Cabecera duplicada eliminada**: la identidad la aporta el shell de neural.news; el Studio
  conserva solo su navegación de 8 pasos por proceso, con el mismo estilo de píldoras.
- **Herramientas de herencia retiradas de la UI**: «Descargar código completo» y «Manual y
  Contrato» ( herramientas de desarrollo del prototipo recuperado); el gráfico y el rótulo del
  montaje y el SVG de la UI derivan ahora del MISMO modelo de diseño (paridad verificada por
  píxel en tests/test_graphic_design_parity.py).
- El diseño de los gráficos/tarjetas usa la paleta de la app: fondo neutral-950, barras sky-400.

Verificación: suite 126 passed + 1 skip; 2 E2E Edge en verde; build limpio; revisado en
navegador (/fuentes vs /estudio, mismas píldoras, acentos y tipografía).


## FASE 5 — Transcripción automática de cualquier fuente (01/11/2026)

Commits `4b9ec04` (buscar o crear la transcripción), `d9f89f6` (ASR de cualquier vídeo),
`ef01bd0` (transcripción COMPLETA vía yt-dlp).

- **Cadena de 3 proveedores, sin Docker ni claves de API:** `yt-dlp` (principal, binario local de
  23,6 MB en `tools/`) → `timedtext` (pistas manuales publicadas) → reproductor interno (pistas ASR).
- **Desempate de idioma por variante regional:** se prefiere `es-419` antes que `es`, porque YouTube
  puede no tener la pista genérica; se descartan las variantes encadenadas (`es-es-419`), que son
  traducciones automáticas de otra lengua.
- **Reintento con backoff ante el 429 de YouTube** (3 intentos, una sola pista por intento).
- **Verificación real ejecutada:** `../tools/sub5/x.en.json3` descargado con `yt-dlp`; la fuente #22
  transcrita vía HTTP (`POST /api/v1/sources/22/transcribe` → 200) con el contenido almacenado.
- **Pruebas:** `test_transcribe_sources.py` (5), `test_transcribe_auto.py` (3), `test_transcribe_ytdlp.py` (5).
- **Estado honesto: PARCIAL.** La cadena funciona, pero el recorrido de usuario tiene defectos
  abiertos: la transcripción pegada en el alta se descarta (B2), los errores se pintan en verde (B4)
  y la ruta de pódcast lanza `AttributeError` por `source.metadata` (B1). Ver `ESTADO_REAL.md` §5.

## FASE 6 — Preparación de la beta (01/11/2026) — NN-108 / NN-119

- **Consolidación del repositorio.** El hermano `neuralnews` queda **archivado y sellado** en
  `archive/neuralnews-20261101/` (20 024 ficheros, repo git válido con su remoto), con manifiesto
  SHA-256 de sus 121 ficheros versionados. Se detiene **solo** su pila (API `:8800`, web `:3100`);
  la pila principal sigue en marcha.
- **Remoto local + backups verificados.** `.remotes/neural-news.git` (3 ramas + tag) y
  `.remotes/neuralnews.git`; dos bundles git verificados; dump de PostgreSQL **restaurado en base
  limpia con recuento idéntico en 20 tablas**; backup previo a NN-107 con SHA-256 coincidente.
- **Artefactos sueltos fuera del árbol** (13 MB de ZIP/RAR + 2 directorios) → `storage/`, con
  manifiesto de sellado. Las **17/17 fuentes de Flow** contrastan con `reports/manifest.json`.
- **Rama `beta/v1`** creada desde `main` (`ef01bd0`). Un clon limpio desde el remoto reproduce
  27 commits y un árbol de 141 ficheros **idéntico**.
- **Base de pruebas verificada:** **139 passed, 1 skipped, 0 fallos** (E) desde la raíz del
  repositorio. Se detecta una fragilidad: desde `apps/api` fallan 3 tests por el `sys.path`.
- **Documentación actualizada:** `ESTADO_REAL.md` reescrito con la FASE 4, los 15 defectos y los
  8 riesgos de plataforma verificados, y `BACKLOG.csv` reconstruido con el estado real.
- **Siguiente:** NN-109 (corrección de los 9 defectos bloqueantes) sobre `beta/v1`.

## FASE 7 — NN-109: corrección de los defectos verificados (01/11/2026)

Rama `beta/v1`. **15 pruebas de regresión nuevas** en `tests/test_nn109_defectos.py`, verificadas
**rojas sobre el código original** (8 de 15 fallaban) y **verdes** tras el arreglo.

### Cerrados

| # | Qué se corrigió | Dónde |
|---|---|---|
| B1 | `source.metadata` → `source.metadata_json`: la ruta de pódcast lanzaba `AttributeError` y lo enmascaraba un `except Exception` | `api/sources.py` |
| B16 | `podcast:transcript` se leía del atributo `href`; feedparser lo expone como `url`. **La transcripción de pódcast nunca funcionó, por dos motivos independientes** (B1 y B16) | `providers/transcript.py` |
| B2 | La transcripción pegada se perdía en **dos** puntos: la interfaz no la enviaba y `create_source` la ignoraba en la rama de texto. Ahora se guarda como `TRANSCRIPT` | `app/fuentes/page.tsx`, `services/sources.py` |
| B3 | El paso **«Resultado»** era el único de los ocho que no se persistía. Ahora se guarda, se hidrata y sobrevive a la recarga | `features/studio/App.tsx`, `components/ResultTab.tsx` |
| B4 | Los mensajes de la interfaz llevan **severidad explícita** (`ok`/`warn`/`error`): «el vídeo no tiene subtítulos» ya no se pinta en verde | `app/fuentes/page.tsx` |
| B7 | Nuevo módulo `neuralnews/errors.py` con `safe_error()`: rutas, secretos y correos se ocultan; el detalle completo va al log. Afecta a la transcripción, el montaje, el trabajo en cola y los metadatos de la fuente | `errors.py`, `api/sources.py`, `api/projects.py`, `services/sources.py`, `worker_tasks.py` |
| B8 | La caché de transcripciones automáticas pasa a tener TTL (3600 s; 300 s para resultados negativos) y tope de 64 entradas. Los negativos también se cachean: un vídeo sin subtítulos no se vuelve a preguntar en cada intento | `api/sources.py` |
| B9 | `NEURAL_API_URL` es **obligatoria** fuera de local: **el build de la web falla con un mensaje explícito** en vez de compilar una aplicación que se quedaría sin datos al desplegar | `apps/web/next.config.ts` |
| B10, B11, B12 | Código muerto (`tracks`), URL sin codificar (`quote`) y docstring del director alineado con su comportamiento real | `providers/transcript.py`, `services/director.py` |
| B13, B14 | `HelpModal.tsx` **eliminado** (es el «Manual y Contrato», retirado de la UI por decisión del propietario; queda en el historial) y `setError_clear` eliminado | `features/studio/components/`, `lib/hooks.ts` |
| B15 | `logout` cierra **solo la sesión actual** (antes borraba todas las del actor y expulsaba de otras pestañas) | `api/auth.py` |
| B17 | La identidad «NeuralDotAI» aparecía en **5 componentes visibles**, violando la regla F-01 del propio proyecto. El test original solo miraba 4 ficheros y no lo detectaba: la comprobación ahora recorre todo el árbol | `BackupModal.tsx`, `ReferencesTab.tsx`, `ResultTab.tsx`, `VoiceTab.tsx`, `test_regressions_f01_f10.py` |

### Decisión de alcance

`BackupModal.tsx` (Centro de mantenimiento: SHA-256 + descarga JSON) **se conserva**: no es código
muerto sino una capacidad real que la auditoría F-10 guarda. Cablearlo en la interfaz es NN-113.

### Verificación

- `python -m pytest tests -q` → **159 passed, 1 skipped, 0 fallos** (E).
- `npx tsc --noEmit` → 0 errores (E).
- `next build` → compila con `NEURAL_ENV=local`; **falla a propósito** sin `NEURAL_API_URL` (E).
- **E2E Edge: 7 passed, 0 fallos** (E) — frente a **4 de 5 fallando** en el mismo fichero sobre el
  código original (`ef01bd0`), con la base de datos desfasada (B20) y el sondeo sin esperar (B21).
- Prueba de rojo→verde: con el código original restaurado, 8 de las 15 pruebas nuevas fallan (E).

### Hallazgos aparecidos al verificar (fuera del plan original)

| # | Qué pasó | Gravedad | Estado |
|---|---|---|---|
| **B19** | El worker **no completaba ningún trabajo** con la salida redirigida en Windows: el `print` con «→» estaba **dentro de la transacción**, el `UnicodeEncodeError` (cp1252) la revertía entera y el trabajo volvía a la cola **para siempre** | **Crítica** | CERRADO — flujos a UTF-8 y estado escrito fuera de la transacción |
| **B20** | La **base de datos viva estaba desfasada** respecto a los modelos (`alembic_version` vacía, faltaba `generated_takes.needs_review`): `create_all()` solo crea tablas y **nunca añade columnas**. El Studio devolvía **500** y el E2E fallaba sin causa aparente | **Crítica** | CERRADO — el arranque aplica `alembic upgrade head`; base reparada y verificada (31/31 tablas, `alembic check` sin diferencias); red de seguridad en `tests/test_schema_migrations.py` (3 pruebas) |
| **B21** | `useJobPolling` tenía **un solo temporizador compartido** y `poll()` **no esperaba**: el sondeo antiguo terminaba tarde y **machacaba el guion recién escrito**; la edición se perdía en silencio | **Alta** (pérdida de datos) | CERRADO — `poll()` espera al trabajo y cada trabajo lleva su temporizador |

**Lección de método (aplicable a las fases siguientes):** tres de los cuatro hallazgos críticos
aparecieron **al ejecutar**, no al leer el código, y en los tres casos la causa era la misma: **el
mecanismo de prueba era más estrecho que la regla que debía comprobar**. La regla de identidad F-01
miraba 4 ficheros (no vio 5 componentes con «NeuralDotAI»); la del esquema no existía. Antes de
dar por cerrado un requisito hay que demostrar que la prueba que lo vigila **cubre el requisito
entero**.

### Arranque (sin Docker, todo local)
```bash
# PostgreSQL 16.9 nativo (si no está en marcha)
../pglocal/pgsql/bin/pg_ctl.exe -D ../pglocal/data -l ../pglocal/logfile.log -o "-p 5433" start

# API + worker (FastAPI) contra PostgreSQL
export NEURAL_DATABASE_URL="postgresql+psycopg://neural@127.0.0.1:5433/neuralnews"
python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000
python -c "from neuralnews.worker import run; run()"

# Web (Next.js) — http://localhost:3000
cd apps/web && npm run build && npm run start

# Pruebas (desde la raíz del repositorio)
python -m pytest tests -q
```

