# AUDITORÍA BETA — `1.0.0-beta.1` (auditoría independiente, 2026-11-03)

> Objetivo: **refutar** las afirmaciones del informe de entrega, no añadir
> funcionalidad. Solo se corrigió lo que la auditoría demostró que estaba roto o
> era inconsistente.
>
> - Rama auditada: `release/1.0.0-beta.1` (commits de corrección de la auditoría
>   sobre el tag `v1.0.0-beta.1`)
> - Tag auditado: `v1.0.0-beta.1` → `1c63a3a` (**no movido**)
> - Evidencias (un log por comprobación): `docs/entrega/evidencias/auditoria/`
> - Restricciones respetadas: **sin push**, sin remotos, sin despliegue, sin
>   mover el tag, sin reescribir el historial, sin desactivar pruebas, sin tocar
>   `.env` reales. Solo commits locales de corrección.

---

## 1. Veredicto

# `BETA_CON_DEFECTOS_CORREGIDOS`

La beta **funciona** (arranca, responde, el recorrido editorial completo se
puede hacer) y sus afirmaciones principales son ciertas. **Pero** la auditoría
encontró **16 defectos reales** (14 de código o repositorio y 2 de la guía de
pruebas), varios de ellos graves: **el repositorio no era autosuficiente** (en
una instalación limpia faltaban dos dependencias declaradas y la suite abortaba),
el **manifiesto SHA-256 de la gobernanza no cuadra con lo entregado** (72 de 223
entradas), los **artefactos generados** describían bytes distintos de los
versionados, la **web no arrancaba** en un clon limpio siguiendo la guía, y la
**parada dejaba procesos huérfanos**.

Todos están corregidos y verificados en la rama. Como el contenido del tag ya
no representa lo que se entrega, **no se ha movido el tag**: se propone
`1.0.0-beta.2` (ver §7).

---

## 2. Afirmaciones del informe anterior: cómo se comprobaron y qué se encontró

| Afirmación del informe de entrega | Cómo la comprobé | Resultado |
|---|---|---|
| «386 tests, 0 skip» | `python -m pytest tests -q` en el workspace **y en un clon limpio** | **FALLA en el clon**: 13 tests fallaban y la instalación abortaba por `Pillow` sin declarar. **PASA** tras corregir (A1) |
| «El repositorio se instala con `npm ci` y `pip install -e apps/api[dev]`» | Instalación real en un clon limpio | **FALLA**: `Pillow` y `cryptography` se usaban en el código y **no estaban declaradas** |
| «La gobernanza llega intacta (manifiesto SHA-256)` | `tools/auditoria/comprobar_gobernanza.py` (nuevo): 223 entradas contra el blob de git | **FALLA**: en el tag solo cuadraban **151/223**; el `core.autocrlf=true` convirtió la evidencia al confirmar |
| «Los artefactos generados están al día» | `generar_manifiesto_studio --check` y `exportar_openapi --check` **en el clon** | **FALLA**: los generadores escribían CRLF en Windows y los hashes describían bytes que no se versionan |
| «El contrato OpenAPI exportado coincide con el servido» | `tests/test_openapi_exportado.py` en el clon | **FALLA**: `fastapi` sin acotar → 0.115.8 (equipo) y 0.162.0 (clon) dan esquemas distintos |
| «`scripts\bootstrap.ps1` + `scripts\start.ps1` dejan la instalación lista» | Clon limpio → bootstrap → start → web | **FALLA**: `bootstrap.ps1` no construía la web y `next start` no arranca sin build |
| «`beta_stop.mjs` para la pila» | Parada/arranque/parada/arranque + búsqueda de procesos huérfanos | **FALLA**: una pila arrancada con `start.ps1` sobrevivía a `beta_stop.mjs` (PIDs no registrados) |
| «La beta se puede arrancar en otros puertos (clon en 3001/8001)` | `beta_start.mjs` con `NEURAL_BETA_*_PORT` | **FALLA**: los puertos estaban **fijos en el código** (8000/3000); las URLs de espera sí eran configurables (trampa) |
| «La documentación es coherente» | `tools/auditoria/comprobar_enlaces.py` (nuevo) sobre 17 documentos | **FALLA**: 9 destinos rotos, incluido el nombre del directorio de gobernanza |
| «`.env.example` documenta toda la configuración» | `tools/auditoria/comprobar_configuracion.py` (nuevo): 40 variables leídas por el código | **FALLA**: faltaban 8; sobraban 0 |
| «La versión es `1.0.0-beta.1` en todas partes» | 5 ficheros estáticos + `/health` en vivo | **PASA** (6/6) |
| «No hay secretos en el repositorio» | `tools/scan_secrets.py` + `tools/auditoria/comprobar_secretos_historial.py` (nuevo) | **PASA**: 0 hallazgos en árbol e historial |
| «El tag `v1.0.0-beta.1` está anotado y apunta a `1c63a3a`» | `git cat-file -t` / `git rev-list -n1` | **PASA** |
| «Los commits posteriores al tag solo tocan documentación» | `git show --name-only` de `7c18c29`, `87b07cc`, `c02e055` | **FALLA (parcial)**: `87b07cc` **creó `scripts/auditar_entrega.mjs`** (186 líneas): es **código de verificación**, no de producto. `apps/`, `infra/`, `packages/` y `tests/` siguen **idénticos al tag**, así que el tag sí representa el producto; pero la afirmación literal «solo documentación» es falsa |

---

## 2 bis. A5 — Recorrido funcional (`GUIA_PRUEBAS_BETA.md`)

Recorrido real contra la pila en marcha, a nivel HTTP (el mismo contrato que
usa la web). Script: `tools/auditoria/recorrido_funcional.py`; resumen:
`docs/entrega/evidencias/auditoria/A5_recorrido_funcional.json`.

| Paso de la guía | Veredicto | Observación |
|---|---|---|
| 1.3 `/api/v1/health` → 200, `ok=true`, versión correcta | **PASA** | base, FFmpeg, yt-dlp y presupuesto OK |
| 1.2 «Entrar en modo demo» → sesión iniciada | **PASA** | cookie `nn_session`; `auth/me` → `actor_id=demo` |
| 1.4 `/ops` (métricas y alertas) | **PASA** | 200 con métricas de la ventana de 24 h |
| 1.5 proveedores sin clave declarados como no configurados | **PASA** | 9 proveedores, **7 sin clave** (`youtube`, `spotify`, `gemini_video`, `search`, `editorial_llm`, `asr`, `video_production`) |
| 2.1 «Añadir fuente» (YouTube) | **PASA** | fuente creada (id 132) |
| 2.1b la misma fuente **no** se duplica | **PASA** | segunda llamada → misma id (132) |
| 2.2 el worker la procesa | **PASA** | estado `READY` |
| 2.3 `/stories` con noticias | **PASA** | 3 noticias de demo |
| 2.4 «Investigar» | **PASA** | `job_id` creado |
| 2.5 afirmaciones con estado y sin confirmaciones sin evidencia | **PASA** | 0 confirmadas sin evidencia |
| 2.6 el Estudio (8 pasos) carga | **PASA** | HTTP 200 |
| 2.9 «Lotes → nuevo lote» y exportar | **PASA** | el contrato exige **exactamente 5 o 10** noticias; con 3 de demo la API responde «Selecciona exactamente 10 noticias». Se crean 7 con el proveedor «manual» (texto propio, sin red) → lote creado (`id=1`, 10 noticias), exportado (trabajo `DONE`), estado `READY_FOR_REVIEW` y **ZIP descargable** (8 127 bytes) con el manifiesto JSON, los guiones en Markdown y los guiones sueltos. El **storyboard y los prompts van dentro del manifiesto**, no en ficheros aparte |
| 3.2 sin evidencia, estado `UNVERIFIED` | **PASA** | comprobación informativa |
| 3.3 alerta «cola parada» en `/ops` | **PASA** (tras corregir la guía) | la alerta real es `cola_parada` y avisa de **trabajos sin recoger desde hace >5 min**, no «del worker parado en menos de un minuto» |

**Dos afirmaciones de la guía eran inexactas** (B55, B56) y se han corregido en
`docs/entrega/GUIA_PRUEBAS_BETA.md`:

1. El lote exige **exactamente 5 o 10 noticias**; la guía no lo decía (con los 3
   datos de demo, el paso 2.9 no se puede hacer).
2. La alerta «cola parada» **no detecta el worker parado**: avisa de trabajos en
   cola sin recoger hace más de 5 minutos (`MINUTOS_SIN_RECOGER` en
   `neuralnews/metrics.py`). La guía prometía «en menos de un minuto».

**Ambiguousidades y pasos que exigen conocimiento no documentado** (anotadas, sin
cambiar el producto):

- El salto del manual al API no es evidente: `POST /api/v1/sources` devuelve la
  fuente **anidada** (`{"source": {...}}`) y el estado del proveedor es `READY`,
  no «lista» como dice la guía.
- El lote exige `target_size` ∈ {5, 10} **y** exactamente ese número de noticias,
  y la **exportación es asíncrona** (hay que esperar al trabajo para descargar el
  ZIP).
- `POST /api/v1/sources/{id}/analyze` **solo** aplica a fuentes de YouTube; para
  las demás hay que aportar texto o transcripción (el mensaje del propio API lo
  dice, pero la guía no lo menciona).
- Una fuente «manual» solo se convierte en noticia si el **texto es distinto** en
  cada una: la extracción deduplica por `topic_key`, así que dos textos
  idénticos producen **una** noticia (no es un defecto: es la deduplicación).
- La guía dice «pulsa «Actualizar»» en el paso 2.2, sin indicar **qué** se
  actualiza ni que el estado se ve en `/fuentes`.
- El paquete de un lote no lleva el storyboard como fichero aparte (va dentro de
  el manifiesto): la guía no lo precisa.

---

## 3. A1 — Clon limpio: resultado y archivos que faltaban

**Método**: `git clone --branch <ref>` en `%TEMP%\beta-audit*`, instalación
desde los ficheros de bloqueo (`npm ci`, `pip install -e "apps/api[dev]"` en una
venv propia), `.env` copiado de `.env.example`, y ejecución de pytest, tsc,
eslint, build, Playwright y arranque en **3001/8001**.
Batería reproducible: `tools/auditoria/verificar_clon_limpio.ps1`.

### 3.1 Clon del **tag** `v1.0.0-beta.1` (lo que se entregó)

| Comprobación | Código de salida | Veredicto |
|---|---|---|
| Instalación del backend | 2 | **FALLA** |
| `pytest` | 2 | **FALLA** (aborta en la recolección) |
| `tsc` / `eslint` / `build` | 0 / 0 | PASA |
| Playwright | — | **BLOQUEADA** (no hay build) |
| Arranque en 3001/8001 | — | **BLOQUEADA** (los puertos estaban fijos en el código) |

**Archivos que faltaban (con su ruta exacta):**

| Ruta | Qué faltaba | Por qué rompía |
|---|---|---|
| `apps/api/pyproject.toml` | la dependencia **`Pillow>=10.0`** | `services/graphics.py` la usa con import perezozo: la app arranca, pero **dos tests no se pueden recoger** y `pytest` aborta la suite entera (exit 2) |
| `apps/api/pyproject.toml` | la dependencia **`cryptography>=42.0`** | `apps/api/src/neuralnews/vault.py` la usa para la bóveda de secretos: **ocho tests de la bóveda fallan** en instalación limpia |
| `apps/api/pyproject.toml` | cota superior de **`fastapi`** | `fastapi>=0.115` sin acotar: el equipo tenía 0.115.8 y el clon 0.162.0; el contrato OpenAPI versionado solo cuadra con una de las dos |
| `apps/web/features/studio/data/manifiestoStudio.generado.json` | hashes de los ficheros del Studio | generado con **CRLF** en Windows: no cuadra con los bytes versionados (LF) → el test «manifiesto al día» falla en el clon |
| `apps/web/lib/estados.generado.ts` | igual que el anterior | idem |
| `docs/openapi.json`, `packages/contracts/openapi.json` | igual que el anterior | idem |
| `docs/gobernanza/**` (52 ficheros) | **bytes verbatim** | el tag entregó la evidencia en LF, pero su manifiesto declara los bytes en CRLF: **72 de 223 entradas no cuadraban** |
| `docs/gobernanza/03_EVIDENCIA_FLOW/flow-recovery.rar` | el binario sellado | el `.gitignore` lo excluye a propósito («0 binarios sueltos»): el test de integridad lo daba por alterado en cualquier clon |
| `apps/web/.next/` (build de producción) | el **build** | `bootstrap.ps1` no lo construía: `next start` falla con «Could not find a production build» |

### 3.2 Clon de la **rama corregida** (lo que se entregaría como `beta.2`)

| Comprobación | Código de salida | Veredicto |
|---|---|---|
| Instalación (venv + `npm ci`) | 0 | **PASA** |
| `pytest tests -q` | 0 | **PASA** |
| `npx tsc --noEmit` | 0 | **PASA** |
| `npx eslint .` | 0 | **PASA** |
| `npm run build` | 0 | **PASA** |
| `npx playwright test` | 0 | **PASA** |
| Arranque en 3001/8001 | 0 | **PASA** (`/health` → `1.0.0-beta.1`, web 200) |
| Parada | 0 | **PASA** (0 huérfanos, puertos libres) |

Evidencia: `docs/entrega/evidencias/auditoria/A1_clon_*.log` y
`A1_clon_resumen.json`.

### 3.3 Todas las comprobaciones de la auditoría, con veredicto y log

| Comprobación | Veredicto | exit | Log |
|---|---|---|---|
| A1.1–A1.10 clon limpio (instalación, pytest, tsc, eslint, build, Playwright, arranque 3001/8001, parada) | **PASA** | 0 en todos | `A1_clon_01..09.log`, `A1_clon_resumen.json` |
| A1 (tag original) instalación y suite | **FALLA** | 2 | `A1_clon_04_pytest.log` (primera ejecución, superada) |
| A2.1 el directorio de gobernanza es `docs/gobernanza` | **PASA** | 0 | `A2_A3_A4.log` |
| A2.2 enlaces y rutas de 17 documentos | **PASA** | 0 | `A2_A3_A4.log` |
| A2.3 `.env.example` = variables del código (42/42) | **PASA** | 0 | `A2_A3_A4.log` |
| A2.4 versión en los 6 sitios (5 ficheros + `/health`) | **PASA** | 0 | `A2_A3_A4.log`, `comprobar_configuracion.py` |
| A3.1 parada en frío | **PASA** | 0 | `A2_A3_A4.log` |
| A3.2 arranque: 200 en web y `/health` | **PASA** | 0 | `A2_A3_A4.log` |
| A3.3 segunda parada: puertos libres, 0 huérfanos | **PASA** | 0 | `A2_A3_A4.log` |
| A3.4 segundo arranque (idempotencia) | **PASA** | 0 | `A2_A3_A4.log` |
| A4.1 tag anotado → `1c63a3a` | **PASA** | 0 | `A2_A3_A4.log` |
| A4.2 commits post-tag: 0 cambios en código de producto | **PASA** | 0 | `A2_A3_A4.log` (con el matiz de B57) |
| A4.3 `git diff --check` sin errores | **PASA** | 0 | `A2_A3_A4.log` |
| A4.4a secretos en árbol e historial (`scan_secrets.py`) | **PASA** | 0 | `A2_A3_A4.log` |
| A4.4b secretos en `git log -p` (patrones de clave) | **PASA** | 0 | `A2_A3_A4.log` |
| A4.5 `.gitignore` y nada prohibido en el índice | **PASA** | 0 | `A2_A3_A4.log` |
| A4.6 gobernanza = manifiesto SHA-256 (223/223) | **PASA** | 0 | `A2_A3_A4.log` |
| A5 recorrido funcional (17 pasos de la guía) | **PASA** | 0 | `A5_recorrido_funcional.json` |
| 14 comprobaciones del repo (`docs/entrega/verificar.ps1`) | **14/14 PASA** | 0 | `docs/entrega/evidencias/*.log` |
| 17 comprobaciones de `scripts/auditar_entrega.mjs` | **17/17 PASA** | 0 | salida de consola |

**Bloqueadas / no comprobables en esta máquina** (se escriben como
*desconocido*, sin inventar):

| Cosa | Estado | Por qué |
|---|---|---|
| `supervisor.sh` (raiz del repositorio) y el crontab | **BLOQUEADA** | WSL no arranca (virtualización desactivada); nada depende de bash/cron |
| **Cuota** de la plataforma | **desconocido** | no hay herramienta de consulta de cuota ni de saldo |

---

### 3.4 A3.4 — `scripts\start.ps1` frente a `beta_start.mjs`

Ambos levantan **la misma pila** (API `uvicorn neuralnews.main:app`, worker
`python -m neuralnews.worker` y web `npm run start`) y ambos dejan los
procesos desacoplados (no se paran al cerrar la terminal). La auditoría
comprobó el código de los dos y su comportamiento real.

| | `scripts\start.ps1` | `scripts\beta_start.mjs` |
|---|---|---|
| Dependencia | PowerShell (Windows) | **Node 20+**: funciona en Windows, macOS y Linux |
| Puertos | parámetros `-PuertoApi` / `-PuertoWeb` | variables `NEURAL_BETA_API_PORT` / `NEURAL_BETA_WEB_PORT` (o el puerto de `NEURAL_BETA_*_URL`) |
| Registro | `_api.log`, `_worker.log`, `_web.log` en la raíz | `storage/logs/{api,worker,web}.log` |
| Comprobación | una línea «Salud: …» tras 6 s | espera por HTTP y reporta API y web por separado |
| Opción | `-SinWeb` (levanta solo API y worker) | no tiene equivalente |
| **PIDs** | **registra `storage/logs/beta.pids.json`** (corregido en esta auditoría) | **registra `storage/logs/beta.pids.json`** |
| **Parada** | `beta_stop.mjs` (mismo fichero) o `stop.ps1` (barrido por línea de comandos) | `beta_stop.mjs` o `stop.ps1` |

**Diferencias que siguen existiendo:** el lenguaje y la dependencia (PowerShell
frente a Node), dónde caen los registros, cómo se eligen los puertos y el
`-SinWeb`. **Unificado en esta auditoría:** los dos lanzadores registran sus
PIDs en el mismo fichero y ambos dejan la pila en el mismo estado, así que
cualquiera de los dos se para con `beta_stop.mjs` (y `stop.ps1` para cualquiera
de los dos). Antes, una pila arrancada con `start.ps1` **no se paraba** con
`beta_stop.mjs` (B50).

---

Gravedad: **ALTA** = impide instalar/arancar o hace que la entrega mienta ·
**MEDIA** = incoherencia verificable · **BAJA** = limpieza.

## 4. Hallazgos

| # | Hallazgo | Gravedad | Estado | Corrección |
|---|---|---|---|---|
| B41 | `Pillow` usada pero no declarada | ALTA | Corregido | `apps/api/pyproject.toml`: `"Pillow>=10.0"` |
| B42 | `cryptography` usada pero no declarada (el código decía «dependencia declarada») | ALTA | Corregido | `apps/api/pyproject.toml`: `"cryptography>=42.0"` |
| B43 | `fastapi` sin acotar → el OpenAPI versionado no cuadra con una instalación nueva | ALTA | Corregido | `fastapi>=0.115,<0.116` |
| B44 | Los generadores escribían CRLF en Windows: los artefactos no describen lo versionado | ALTA | Corregido | `newline="\n"` en los 4 generadores + regeneración |
| B45 | 76 ficheros del árbol con CRLF obsoleto (git los daba por limpios) | MEDIA | Corregido | alineados byte a byte con los blobs |
| B46 | La gobernanza entregada **no cuadra con su propio manifiesto** (72/223) | ALTA | Corregido | bytes verbatim restaurados + `.gitattributes` (`-text whitespace=cr-at-eol`) |
| B47 | El manifiesto de la gobernanza lista un RAR que el repo no puede contener | MEDIA | Corregido | excepción documentada `FUERA_DEL_REPOSITORIO` en el test |
| B48 | `bootstrap.ps1` no construía la web → en un clon limpio la web no arranca | ALTA | Corregido | `bootstrap.ps1` construye con `NEURAL_ENV=local`; `start.ps1` avisa si falta el build |
| B49 | `beta_start.mjs` con puertos fijos: las URLs de espera eran configurables, los puertos no | MEDIA | Corregido | `NEURAL_BETA_API_PORT` / `NEURAL_BETA_WEB_PORT` (y puerto derivado de la URL) |
| B50 | `beta_stop.mjs` solo paraba los PIDs registrados: una pila de `start.ps1` quedaba huérfana | ALTA | Corregido | `start.ps1` registra PIDs + barrido de huérfanos en `beta_stop.mjs` |
| B51 | 9 destinos rotos en la documentación (nombre del directorio de gobernanza, rutas del workspace, la variante bootstrap.sh que el plan cita pero no se entrega, y un fichero de prueba hipotético) | MEDIA | Corregido | `tools/auditoria/correcciones_documentales.py` + reescritura de los enlaces |
| B52 | `.env.example` no recogía 8 variables que el código lee | BAJA | Corregido | documentadas (comentadas) en `.env.example` |
| B53 | `.gitignore` tenía reglas muertas (`docs/governance/…`): un `.env` o un `.sqlite` dentro de `docs/gobernanza/` no se ignoraba | BAJA | Corregido | reglas apuntando a `docs/gobernanza/**` |
| B54 | Un test (`test_transiciones_movimiento.py`) usaba `ff_dir` sin comprobar: `UnboundLocalError` en clon limpio | MEDIA | Corregido | se salta con motivo si no hay FFmpeg |
| B55 | La guía no decía que un lote exige **exactamente 5 o 10 noticias** (con los 3 datos de demo, el paso 2.9 no se puede hacer) | BAJA | Corregido | `GUIA_PRUEBAS_BETA.md` |
| B56 | La guía prometía la alerta «cola parada» «en menos de un minuto» al parar el worker: la alerta real avisa de trabajos sin recoger desde hace >5 min | BAJA | Corregido | `GUIA_PRUEBAS_BETA.md` |
| B57 | El commit post-tag `87b07cc` creó `scripts/auditar_entrega.mjs` (código de verificación, no de producto): la afirmación «los commits post-tag solo tocan documentación» era **literalmente falsa** | MEDIA | Documentado | No se toca el historial (prohibido reescribirlo): se documenta en el informe y el check A4.2 distingue producto de herramienta |

### Pendientes

- **P1 (decisión del propietario)**: `v1.0.0-beta.1` ya **no representa** lo que
  se entrega (el tag no incluye ninguna de estas correcciones). El tag **no se
  ha movido**. Propuesta: publicar **`1.0.0-beta.2`**.
- **P2**: `supervisor.sh` (raiz del repositorio) y el crontab no se pueden ejecutar aquí
  (WSL no arranca: virtualización desactivada). **Sin verificar.**
- **P3**: la **cuota** no es consultable con las herramientas disponibles →
  **desconocido** (no se inventa ningún valor).
- **P4**: `packages/contracts/openapi.json` y `docs/openapi.json` deben seguir
  regenerándose cuando cambie FastAPI: la cota superior lo hace estable, pero
  un salto de versión futuro vuelve a exigir regenerarlos.

---

## 5. Por qué `scripts/auditar_entrega.mjs` dio 17/17 y no detectó nada de esto

Porque **mide lo contrario de lo que se le pedía**: comprueba que *las pruebas
del propio repositorio* pasan y que *sus artefactos* son coherentes **en el
árbol de trabajo donde se ejecuta**, no que el repositorio sea reproducible
desde cero.

1. **No hay clon limpio.** `auditar_entrega.mjs` se ejecuta en el workspace,
   donde la instalación está hecha «a mano» y con `Pillow`/`cryptography`
   instaladas de más en el Python del sistema. En el workspace la suite pasaba;
   en un clon limpio abortaba. **La diferencia entre «aquí funciona» y «se puede
   instalar» es justo lo que la auditoría tenía que buscar.**
2. **El CRLF se cuela en la comparación.** Con `core.autocrlf=true`, git da por
   «limpios» ficheros cuyo contenido en disco difiere de los bytes versionados,
   y las herramientas que hashean el disco (el manifiesto del Studio, el
   OpenAPI) calculan hashes de esos bytes distintos. En el workspace, todo
   cuadra; en el clon, no.
3. **Mide la coherencia interna, no la fidelidad de la entrega.** Por eso la
   gobernanza (72 entradas rotas contra su manifiesto) pasaba: el test compara
   el manifiesto con los ficheros **del disco**, y en el disco estaban en CRLF,
   que es justo lo que el manifiesto declara. El defecto solo se ve al comparar
   con **los bytes que git entrega**.
4. **17/17 era una afirmación sobre 17 comprobaciones internas**, no sobre las
   afirmaciones del informe. Por eso el informe «17/17» y el informe
   «386 tests» podían ser ciertos y, a la vez, el repositorio no ser
   instalable en limpio.

Los nuevos comprobadores (`tools/auditoria/`) atacan justo ese ángulo:
clon limpio, bytes versionados en vez de bytes en disco, y rutas citadas por
los documentos.

---

## 6. Estado de git y del lanzamiento al cerrar

- Rama `release/1.0.0-beta.1` · **sin push**, remoto local
  `.remotes/neural-news.git` intacto.
- Tag `v1.0.0-beta.1` → `1c63a3a`, **anotado**, **sin mover**.
- `git status` limpio · `git diff --check` sin errores · 0 secretos.
- Commits de corrección (locales, en la rama):
  `a480387` (Pillow + test de transiciones) · `3eabf21` (bytes verbatim de la
  gobernanza) · `f656d5b` (enlaces, rutas y `.env.example`) · `f0eb767`
  (ciclo en frío) · `104489e` (autosuficiencia: clon limpio) · y el commit de
  cierre con este informe y el checkpoint.
- Al cerrar: **beta parada**, puertos 3000/8000 libres, 0 procesos huérfanos.

---

## 7. PRÓXIMA ACCIÓN EXACTA

**Crear el tag anotado `v1.0.0-beta.2` sobre el HEAD de
`release/1.0.0-beta.1`**, una vez que el propietario lo autorice. Sin push y
sin mover `v1.0.0-beta.1`.
