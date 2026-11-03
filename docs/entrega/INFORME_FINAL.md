# Informe final — entrega de la beta `1.0.0-beta.1`

**Proyecto:** neural.news (motor editorial + NeuralStories Studio)
**Ruta final:** `C:\Users\haxth3\Documents\NeuralStories\proyecto final`
**Salida de `git rev-parse --show-toplevel`:** `C:/Users/haxth3/Documents/NeuralStories/proyecto final`
**Fecha:** 2026-11-03 · **Modo de la entrega:** beta **local** (sin despliegue, sin publicación)

---

## 1. Estado final

**`[ESTADO: BETA_LISTA]`**

Motivo: las ocho fases (F1–F8) están **COMPLETADAS** con evidencia. Las cuatro condiciones
del encargo se cumplen:

| Condición | Estado | Evidencia |
|---|---|---|
| `proyecto final` es la raíz real del repositorio Git | **Sí** | `git rev-parse --show-toplevel` → `C:/Users/haxth3/Documents/NeuralStories/proyecto final`; `.git` es un directorio normal; commit e historia idénticos a los de F1 |
| La beta tiene versión, commit y tag **locales** | **Sí** | `1.0.0-beta.1` · rama `release/1.0.0-beta.1` · commit `release: v1.0.0-beta.1` · tag anotado `v1.0.0-beta.1` (**sin push**) |
| La aplicación se lanza en local en modo producción y responde | **Sí** | web **http://localhost:3000** → 200 · API **http://127.0.0.1:8000/api/v1/health** → 200 con `version: 1.0.0-beta.1`; prueba rápida de Playwright **7/7 PASA** |
| Resumen, documentación e informe final dentro de `proyecto final` | **Sí** | `README.md`, `CHANGELOG.md`, `docs/entrega/{RESUMEN_COMPLETO,NOTAS_BETA,GUIA_PRUEBAS_BETA,INFORME_FINAL}.md`, `docs/entrega/evidencias/` |

Lo **aplazado** (DEC-02, SUP-01, SUP-02) no impide este estado y aparece en §8.

## 2. Resumen del proyecto y de lo entregado

`neural.news` es un motor editorial sobre IA: recoge una fuente (YouTube, Spotify/pódcast,
web/RSS o texto propio), extrae noticias candidatas, las investiga con evidencia trazable,
escribe y **aprueba** guiones por versiones, los agrupa en lotes y exporta el paquete
editorial. Encima, el **NeuralStories Studio**: el flujo de producción audiovisual en ocho
etapas con persistencia real en la base de datos.

La tesis del producto: **la máquina propone y la persona aprueba**.

En esta entrega se ha añadido, además del producto ya verificado:

- La **reubicación** del repositorio a `proyecto final` (con `.git` y la historia intactos).
- La **versión `1.0.0-beta.1`** declarada y comprobada en cinco sitios.
- La **gobernanza dentro del repositorio** (`docs/governance/`), con su manifiesto SHA-256
  verificado.
- La **plantilla de entorno completa** (las 30 variables que lee el código).
- El **parche de seguridad** de Next.js (15.1.6 → 15.5.28).
- El **log del worker uniforme** (JSON por evento; se retiraron 4 `print()`).
- **Métricas y alertas** del sistema, ya operativa en `/ops`.
- **Rutas de modelo** con instantánea en el trabajo.
- **Scripts de arranque/parada multiplataforma** (`node`, sin Bash ni WSL) y el **script de
  verificación** de 14 comprobaciones con veredicto y log por comando.
- **Pruebas nuevas**: versión coherente, plantilla de entorno, integridad de la gobernanza,
  build de producción sin depuración ni datos personales, y auditoría del plan.

## 3. Ruta final

```
Entrada:  C:/Users/haxth3/Documents/NeuralStories/neural-news   (F1)
Salida:   C:/Users/haxth3/Documents/NeuralStories/proyecto final  (F2, verificado)
```

El cambio se hizo con `Move-Item` de la **carpeta completa** (incluidos `.git`, los ficheros
ocultos y los que estaban sin commitear). No hay carpeta `proyecto final/proyecto final`.
El paquete de Python instalado en modo editable guardaba la ruta absoluta: se reinstaló
(`pip install -e ".[dev]"`) y `neuralnews` resuelve ya a la ruta nueva.

## 4. Versión, rama, commit, tag y estado

| Dato | Valor |
|---|---|
| Versión | `1.0.0-beta.1` (en `package.json`, `pyproject.toml`, `__version__`, `apps/web/lib/version.ts`, OpenAPI y `/health`) |
| Rama de entrega | `release/1.0.0-beta.1` (creada desde `beta/v1` @ `4a6d5db`) |
| Commit de entrega | «release: v1.0.0-beta.1» |
| Tag | `v1.0.0-beta.1` (anotado: «Beta 1.0.0-beta.1») |
| Remoto | `origin` → `.remotes/neural-news.git` (local). **Sin push**, por decisión de la sección 0 |
| `git status` tras el cierre | limpio (salvo el commit `docs: cierre beta`) |

## 5. Lanzamiento

| Qué | Cómo |
|---|---|
| Arranque (multiplataforma) | `node scripts/beta_start.mjs` |
| Arranque (Windows, PowerShell) | `powershell -ExecutionPolicy Bypass -File scripts\start.ps1` |
| Parada | `node scripts/beta_stop.mjs` (o `scripts\stop.ps1`) |
| Web | http://localhost:3000 · build de producción (`next start`) |
| API | http://127.0.0.1:8000 · salud en `/api/v1/health`, documentación en `/docs` |
| Worker | cola de trabajos (sin URL propia) |
| Registros | `storage/logs/{api,worker,web}.log` · PIDs en `storage/logs/beta.pids.json` |

Comprobación performed: `GET /` → **200**; `GET /api/v1/health` → **200** con
`{"ok": true, "version": "1.0.0-beta.1"}`, base de datos **ok**, FFmpeg **ok**, yt-dlp **ok**,
presupuesto **bloqueado en modo demo**. La prueba rápida de Playwright contra esa misma
instancia dio **7/7 PASA** (acceso con modo demo, producto abierto, versión en el pie, sin
errores de JavaScript, sin recursos rotos y la API con la misma versión).

La instancia se dejó **en marcha** durante la entrega (PIDs registrados en
`storage/logs/beta.pids.json`); para pararla, `node scripts/beta_stop.mjs`.

## 6. Tabla de verificaciones

Comando | Veredicto | Código | Tests / detalle | Log
---|---|---|---|---|---|
| `python -m pytest tests -q` | **PASA** | 0 | 386 tests, **0 skip** (la prueba real de PostgreSQL se ejecuta: `scripts/preparar_base_pg_test.py` crea una base aislada) | `evidencias/pytest.log` |
| `npx tsc --noEmit` | **PASA** | 0 | 0 errores de tipos | `evidencias/tsc.log` |
| `npx eslint .` | **PASA** | 0 | 0 problemas | `evidencias/eslint.log` |
| `npm run build` | **PASA** | 0 | build de producción (con `NEURAL_ENV=local`) | `evidencias/build.log` |
| `npx playwright test` | **PASA** | 0 | 8 pruebas E2E en navegador real | `evidencias/playwright.log` |
| `tools/check_clases.py` | **PASA** | 0 | 0 clases inexistentes, 0 reimplementaciones en línea | `evidencias/check_clases.log` |
| `tools/check_a11y.py` | **PASA** | 0 | 0 bloqueantes, 0 avisos | `evidencias/check_a11y.log` |
| `tools/scan_secrets.py .` | **PASA** | 0 | 0 hallazgos (árbol e historial) | `evidencias/scan_secrets.log` |
| `tools/generate_estados.py --check` | **PASA** | 0 | generado al día | `evidencias/generate_estados.log` |
| `tools/generar_manifiesto_studio.py --check` | **PASA** | 0 | manifiesto al día | `evidencias/generar_manifiesto_studio.log` |
| `tools/generar_plan_casillas.py --check` | **PASA** | 0 | `PLAN.md` al día | `evidencias/generar_plan_casillas.log` |
| `tools/exportar_openapi.py --check` | **PASA** | 0 | contrato exportado = servido | `evidencias/exportar_openapi.log` |
| `tools/auditar_evidencias.py` | **PASA** | 0 | 0 referencias desfasadas | `evidencias/auditar_evidencias.log` |
| `git diff --check` | **PASA** | 0 | sin errores de espacios (excluidos, por diseño, la evidencia y la gobernanza verbatim) | `evidencias/git_diff_check.log` |

Comprobaciones adicionales de la entrega:

| Comprobación | Veredicto | Detalle |
|---|---|---|
| `npm audit --omit=dev` | informe | 3 vulnerabilidades (2 altas, 1 crítica) → **2** (1 alta, 1 moderada) tras el parche a `next@15.5.28`; las restantes exigen **Next 16** (ruptivo) → no se aplican. Log: `evidencias/npm_audit.log` |
| `pip-audit` | **no ejecutado** | No está instalado en la máquina (la sección 0 pide ejecutarlo solo si ya está). Log: `evidencias/pip_audit.log` |
| `tools/check_build_produccion.py` | **PASA** | 0 hallazgos de depuración, credenciales ni datos personales en el build |
| `apps/web/scripts/prueba_rapida_beta.mjs` | **PASA** | 7/7 contra la instancia en marcha. Log: `evidencias/F6_lanzamiento.md` |

## 7. Documentación creada o actualizada

| Fichero | Qué es |
|---|---|
| `README.md` | Guía única de la beta: qué es, funcionalidades verificadas, tecnologías, requisitos, instalación, variables, lanzamiento, pruebas, estructura, límites y enlaces |
| `CHANGELOG.md` | Keep a Changelog con la entrada `1.0.0-beta.1` |
| `.env.example` | Las **30** variables que lee el código, sin valores reales, comentadas las opcionales |
| `docs/entrega/RESUMEN_COMPLETO.md` | Propósito, alcance, arquitectura, flujos, integraciones, archivos clave, configuración, verificación, seguridad, limitaciones y hoja de ruta |
| `docs/entrega/NOTAS_BETA.md` | Novedades, 7 problemas conocidos, requisitos y expectativas de quien prueba |
| `docs/entrega/GUIA_PRUEBAS_BETA.md` | Pruebas paso a paso, pruebas negativas y plantilla de incidencia |
| `docs/entrega/INFORME_FINAL.md` | Este informe |
| `docs/entrega/verificar.ps1` | Las 14 comprobaciones con veredicto, código de salida y log |
| `docs/entrega/evidencias/` | Todos los logs (uno por comando) + `F1_linea_base.md` + `F6_lanzamiento.md` |
| `docs/agente/{PLAN_MAESTRO,PLAN,TAREAS,REGISTRO,ESTADO}.md` | Plan ejecutado (89 tareas + bloque «ENTREGA BETA»), checkpoint y registro |
| `docs/gobernanza/` | La gobernanza heredada, con su manifiesto SHA-256 verificado |

## 8. Bloqueos y tareas aplazadas

**Bloqueos: ninguno.** No hay ninguna fase BLOQUEADA.

| id | Estado | Qué necesita |
|---|---|---|
| `DEC-02` | **APLAZADA** (post-beta) | Autorización para crear un remoto remoto (GitHub/GitLab) con credenciales. Es una acción externa |
| `SUP-01` | **APLAZADA** (post-beta) | El comando real que lanza el agente, para `AGENTE_CMD` en `supervisor.sh:5` (sigue siendo un marcador) |
| `SUP-02` | **APLAZADA** (post-beta) | Un entorno con WSL o Git Bash y `crontab`: en esta máquina WSL no arranca (virtualización desactivada) |

Limitaciones técnicas declaradas (no bloquean la beta): 2 avisos de seguridad en
dependencias transitivas de Next (exigen Next 16); `pip-audit` no instalado; animática sin
locución; la instalación editable de Python guarda rutas absolutas (hay que reinstalar si se
mueve la carpeta).

## 9. Decisiones tomadas

**De la sección 0 (autorizadas por el propietario):** ruta final `proyecto final`; versión
`1.0.0-beta.1`; rama `release/<versión>` con commit y tag **locales** y **sin push**; DEC-01
aplicada solo a la parte de la gobernanza que cumplía las cuatro condiciones; DEC-02, SUP-01 y
SUP-02 aplazadas; sin despliegue ni publicación.

**Decisiones propias, con motivo:**

1. **La gobernanza entra como `docs/gobernanza/`, no como `newsV2/`.** `newsV2/` estaba
   **fuera** del repositorio (era hermana de la carpeta del producto): no se puede versionar
   lo que no está dentro. Se movió el contenido real y se redirigieron las referencias
   documentadas.
2. **Lo que no cumplía DEC-01 se queda fuera, y se anota**: `newsV2/neural-news/` es una
   **copia duplicada del repositorio con su propio `.git`** (un `.git` anidado no se puede
   versionar: git lo trataría como submódulo) y `newsV2/flow-recovery/node_modules` contiene
   un binario de 105 MB. No se ha tocado nada de ahí.
3. **El manifiesto SHA-256 de la gobernanza se conserva tal cual**, aunque 3 de sus ficheros
   ya no cuadren: se selló el 2026-10-30 y después se actualizaron legítimamente (el backlog
   en la Fase 0 y el registro de decisiones con el riesgo R-26). Re-sellarlo escondería el
   cambio; el test documenta la excepción explícitamente.
4. **La verificación se ejecuta con la configuración local del proyecto** (el `.env` de la
   raíz): sin `NEURAL_ENV=local`, el build falla **por diseño** (gate G5) y la comprobación
   no distinguiría «producto roto» de «entorno sin configurar».
5. **`git diff --check` excluye la evidencia y la gobernanza**: son salidas capturadas y
   evidencia verbatim; su contenido no se toca. El motivo está escrito en el propio script.
6. **La prueba de PostgreSQL deja de estar en skip**: hay un PostgreSQL local, así que
   `scripts/preparar_base_pg_test.py` crea una base **aislada** y la prueba corre de verdad
   (386 tests, 0 skip).
7. **`outputFileTracingRoot` fijado en la configuración de Next**: Next infería la raíz
   buscando un `package-lock.json` hacia arriba y, en esta máquina, cogía uno suelto del
   directorio personal. Con la raíz fijada, el build es determinista.
8. **La beta declara su icono**: sin `app/icon.svg`, el navegador pedía `/favicon.ico` y
   recibía un 404 en cada carga.
9. **Scripts de arranque multiplataforma en Node** (`beta_start.mjs` / `beta_stop.mjs`): el
   guion no puede depender de Bash, WSL ni cron. Se mantienen también los de PowerShell.
10. **Los `print()` del worker, eliminados**: rompían el log JSON por evento. Ahora todo el
    registro del worker son eventos JSON.

## 10. Cómo reanudar

- **Checkpoint:** `C:\Users\haxth3\Documents\NeuralStories\proyecto final\docs\agente\ESTADO.md`
  (con los dos juegos de campos: títulos en español y alias en `snake_case`).
- **PRÓXIMA ACCIÓN EXACTA:** decidir `DEC-02` (remoto remoto) y `SUP-01`/`SUP-02` (activar el
  supervisor externo). Si se autoriza `DEC-02`, ejecutarla **empezando por** crear el remoto
  y configuringlo como `origin` — **sin** publicar la rama de la beta hasta que se pida
  expresamente, porque la sección 0 la prohíbe.
- **Para volver a verificar:** `pwsh -NoProfile -File docs\entrega\verificar.ps1` (14
  comprobaciones con veredicto y log).
- **Para probar la beta a mano:** `docs/entrega/GUIA_PRUEBAS_BETA.md`.
