# F1 — Línea base (diagnóstico sin modificar nada)

**Fecha:** 2026-11-03 00:15 (Europe/Madrid) · **Objetivo de esta fase:** registrar el estado
real del repositorio **antes** de tocar nada, para que todo lo que se haga después sea
comparable con este punto de partida.

**Este fichero es la evidencia de F1.** Se ha escrito *después* de recoger los datos (es lo
único que F1 modifica): la captura de datos no altera el repositorio.

---

## 1. Repositorio Git

| Dato | Valor comprobado |
|---|---|
| `git rev-parse --show-toplevel` | `C:/Users/haxth3/Documents/NeuralStories/neural-news` |
| Rama actual | `beta/v1` |
| Commit | `4a6d5db32eb395dd534cea3e149e4c8ab5aa8218` (`4a6d5db Checkpoint: estructura de campos de ambos contratos y verificacion final rehecha`) |
| `git status --porcelain` | **vacío** (0 líneas): no hay cambios sin commit, ni del usuario ni previos |
| Tipo de repositorio | `.git` es un **directorio** → repositorio normal (no worktree, no submódulo) |
| `.gitmodules` | no existe |
| `git worktree list` | una sola entrada: `C:/Users/haxth3/Documents/NeuralStories/neural-news  4a6d5db [beta/v1]` |
| Remoto `origin` | `C:\Users\haxth3\Documents\NeuralStories\.remotes\neural-news.git` (**local**, no GitHub/GitLab) |
| Ramas | `beta/v1` (actual), `main`, `nn-107-reintegracion-flow` (+ sus remotas) |
| Tags | 1: `pre-merge-main` |
| HEAD del remoto | `origin/beta/v1` = `4a6d5db` (coincide con el local) |

## 2. Entorno

| Dato | Valor comprobado |
|---|---|
| Node | `v24.20.0` |
| npm | `11.19.0` |
| Python | `3.12.6` |
| Entorno virtual | **no existe** `.venv` ni carpeta tipo venv en el repo → el backend se ejecuta con el Python del sistema (el paquete `neuralnews` está instalado en modo editable: `pip install -e ".[dev]"`) |
| `pip show neuralnews` | instalado como editable apuntando a `apps/api/src` (ruta absoluta → **se rompería si se mueve la carpeta**) |

## 3. Rutas

| Dato | Valor comprobado |
|---|---|
| Ruta actual del repo | `C:\Users\haxth3\Documents\NeuralStories\neural-news` |
| Ruta final decidida | `C:\Users\haxth3\Documents\NeuralStories\proyecto final` |
| ¿Existe el destino? | **NO** (no existe la carpeta). Se puede mover sin sobrescribir nada. |
| Hermanas en el workspace | `.pytest_cache`, `.remotes`, `.tmp-clone-check`, `.tmp-e2e`, `archive`, `backups`, `ffmpeg-local`, `neural-news`, `newsV2`, `newsV3`, `pglocal`, `REVISION_NN107_FLOW`, `tools` |
| `archive/` | hermano congelado (`neuralnews-20261101`), ignorado por git |
| `.remotes/` | remoto local (bare) |

## 4. Capidades reales (comprobadas, no supuestas)

| Capacidad | Estado | Cómo se comprobó |
|---|---|---|
| Fichero persistente | **Sí** | se escriben y se releen ficheros del repo |
| Internet | **Sí** | `GET https://registry.npmjs.org/-/ping` → **200** |
| Procesos en segundo plano | **Sí** | `Start-Process` levanta API/worker/web y se comprueba con HTTP |
| Consulta de cuota | **No** | no hay herramienta de cuota ni de saldo: se escribirá «desconocido» |
| Programador de tareas | **Parcial** | existe `cron_create`/`cron_read` (0 tareas) y `supervisor.sh`; **pero** el guion es Bash y **WSL no arranca aquí** (virtualización desactivada). Nada de la beta puede depender de él. |

## 5. Cambios sin commit previos del usuario

**Ninguno.** `git status --porcelain` sale vacío: el árbol está limpio y todo lo anterior está
commiteado en `beta/v1` (`4a6d5db`). No hay nada que preservar de forma especial ni que
excluir del commit de la beta.

## 6. Estado declarado del plan (a comprobar, no a creer)

- `docs/agente/PLAN_MAESTRO.md`: **89 filas de tarea**, todas marcadas COMPLETADAS.
- `docs/agente/PLAN.md`: espejo con casillas, 89/89 `[x]`.
- `docs/agente/TAREAS.md`: 4 entradas abiertas (DEC-01, DEC-02, SUP-01, SUP-02).
- `docs/agente/ESTADO.md`: checkpoint con los dos juegos de campos.
- `docs/agente/TERMINADO`: marcador de runtime (ignorado por git) que evita que el supervisor
  relance el agente.

Las cifras del informe anterior (343 tests y 1 skip, 8 de Playwright, 89 tareas) son **una
hipótesis**: se vuelven a medir en F3, con la ruta definitiva.

## 7. `newsV2/` — análisis preliminar para DEC-01 (F4)

`newsV2/` **sí forma parte del proyecto** (es la gobernanza: plan rector, tarea, registro de
decisiones y riesgos), pero **no es versionable tal cual**:

| Contenido | Archivos | ¿Es contenido del proyecto? |
|---|---|---|
| `newsV2/neural-news/` (copia del repo **con su propio `.git`**, con `node_modules` de web y `apps/api/local-demo.db`) | 10 995 + 108 + 11 + 11 + 5 | **No**: es una instantánea duplicada y artefactos generados. Un `.git` anidado no se puede versionar (git lo trataría como submódulo). |
| `newsV2/flow-recovery/` (con `node_modules`) | 257 + 17 + 8 + 4 | Parcial: el código y los informes sí; `node_modules` no. |
| `newsV2/03_EVIDENCIA_FLOW/` (`revision_unificacion`, `source`, `reports`) | 228 + 17 + 4 | **Sí**: evidencia del port. |
| `newsV2/04_OPERACION/.env.example` | 1 | **Sí**: plantilla, sin valores reales. |

- **Fichero de más de 50 MB:** `newsV2/neural-news/apps/web/node_modules/@next/swc-win32-x64-msvc/next-swc.win32-x64-msvc.node` → está dentro de `node_modules` → artefacto generado, va a `.gitignore`.
- **Artefactos generados presentes:** `node_modules/` (dos árboles), la copia `newsV2/neural-news/` con su propio `.git`, y `newsV2/neural-news/apps/api/local-demo.db` (base de datos local).
- **Conclusión preliminar:** se cumple la condición de «forma parte del proyecto» y la de
  «sin secretos» **por comprobar**, pero **no** la de «sin artefactos generados». Decisión a
  ejecutar en F4: versionar **solo el contenido real** de gobernanza y evidencia, e ignorar
  por escrito la copia duplicada, los `node_modules` y la base local.

## 8. Versiones declaradas en el repositorio (línea base para F4)

| Sitio | Valor actual |
|---|---|
| `apps/web/package.json` | `"version": "0.1.0"` |
| `apps/api/pyproject.toml` | `version = "0.1.0"` |
| `apps/api/src/neuralnews/__init__.py` | `__version__` (lo consume `main.py` para OpenAPI y `/health`) |

No hay versión declarada superior o igual a `1.0.0-beta.1` → **la versión beta `1.0.0-beta.1`
es coherente con SemVer** y no hay que subirla.
