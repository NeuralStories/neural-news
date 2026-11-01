# NN-107 — Implementación realizada: la lógica de Flow vuelve a neural.news (operativa)

**Fecha:** 31/10/2026 · **Rama:** `nn-107-reintegracion-flow` · **Estado: OPERATIVA en local, 100 % sin Docker**

> **NO APROBADO — PENDIENTE DE REVISIÓN DEL PROPIETARIO.** Instantánea inmutable entregada para revisión; nada se fusiona a `main` ni se da por definitivo hasta aprobación explícita. **Todo el desarrollo y la operación son sin Docker**, con PostgreSQL local de binarios nativos.

Este documento resume qué se implementó, cómo arrancarlo y qué evidencia lo respalda. El detalle
fase a fase está en `TASK_NN-107_REINTEGRACION_FLOW.md` (newsV2) y el estado honesto módulo a
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

- **API:** 107 passed, 0 fallos (+ `test_postgres_projects.py` PASSED contra PG 16.9 real:
  ciclo crear → editar → CAS → MP4 → reiniciar → recuperar).
- **E2E navegador real (Edge):** `studio-reintegration.spec.ts` (8 etapas + persistencia tras
  recargar) y `vertical-production.spec.ts` (director → prompt → paquete → importar → aprobar).
- **Migraciones:** ciclo `upgrade → downgrade → upgrade` verificado en SQLite y PostgreSQL.
- **Regresiones de auditoría:** F-01…F-10 consolidadas en `tests/test_regressions_f01_f10.py`.

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
   `REVISION_NN107_FLOW/evidencia/piloto001_animatica_916.mp4`).
- Corrección adicional: `run_director` desvincula tomas/beats antes de sustituir la línea de
  tiempo (FK violations en PostgreSQL al replanificar proyectos con tomas).
- Pruebas al cierre: **122 passed, 0 fallos, 1 skip** + 2 E2E en verde.
