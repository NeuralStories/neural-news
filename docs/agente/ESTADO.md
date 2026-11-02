# ESTADO — checkpoint de sesión · neural.news

## Última actualización

2026-11-02 16:30 (Europe/Madrid) — **Fases 0–4 y 7 cerradas**; Fase 5 (NN-113) **EN CURSO**
(`.1`–`.5`, `.7`, `.10`, `.11`, `.14`, `.16`, `.17` **commiteadas** en `f8a7b40`; `.6`, `.8`, `.9`,
`.12`, `.13`, `.15` **verificadas, sin commitear**); Fase 6 (NN-114) y Fase 8 (NN-115/116) pendientes.

## Capacidades disponibles

| Capacidad | Estado | Detalle |
|---|---|---|
| Archivos persistentes | ✅ | `neural-news/` (repo git activo, rama `beta/v1`), `newsV2/` (gobernanza, **fuera de git**), `archive/`, `backups/`, `.remotes/` |
| Ejecución de comandos | ✅ | PowerShell 7 en Windows; `python` 3.12.6 con FastAPI/SQLAlchemy/Alembic/pytest; `node` 24, Next.js 15.1.6, Playwright (Edge del sistema), ESLint 9 |
| Base de datos | ✅ | PostgreSQL 16.9 nativo en `pglocal/` (**puerto 5433**, en marcha); SQLite en `neural-news/storage/` (esquema en `d5e3f9a2b7c1`, migrado y verificado) |
| Red | ⚠️ | Sin remoto remoto de git: el remoto es **local** (`.remotes/*.git`). Internet disponible (descarga de fuentes), usado de forma puntual |
| Consulta de cuota | ❌ | **No disponible**: no hay ninguna herramienta de cuota en esta plataforma. Estado: **desconocido** |
| Programador / reanudación | ❌ | **No disponible**: no hay herramienta de creación de tareas programadas. Reanudación = reejecutar este mismo `/goal` |
| Multiagente | ⚠️ | Disponible, pero el subagente de lint **fue cortado por el límite de uso** a mitad; su trabajo se terminó a mano |
| Manipulación de ficheros | ⚠️ | `Remove-Item` está bloqueado; para eliminar, `rm <ruta>` (lanzador con papelera) o `git rm` |

## Tarea actual y estado

**NN-113 — Frontend (Fase 5).** EN CURSO.

Hecho y verificado: `.1` (fronteras de error y estados de carga), `.2` (ESLint ejecutable),
`.3` (script `typecheck`), `.4` (cliente HTTP único con `ApiError`), `.5` (error del trabajo
propagado), `.6` (mapa de estado único y generado), `.7` (0 `any`), `.8` (a11y: 0 bloqueantes),
`.9` (lint de clases inexistentes), `.10` (fuente de iconos sin bloquear), `.11` (idempotencia
por contenido), `.12` (sistema visual único), `.13` (archivos grandes divididos), `.14`
(`webServer` en Playwright), `.15` (Centro de mantenimiento cableado), `.16` (B23), `.17` (B24).

**NN-113 completa salvo el commit de este lote.**

## Último punto verificado

**NN-113.6 / .8 / .9 / .12 / .13 / .15 — COMPLETADAS con evidencia E.**

- `python -m pytest tests -q` → **exit 0** (suite completa, 1 skip).
- `npx eslint .` → **0 problemas**. `npx tsc --noEmit` → **0 errores**. `npm run build` → compila.
- `npx playwright test` → **8 passed, 0 fallos** (1,6 min).
- **NN-113.6 — un solo mapa de estado.** `tools/generate_estados.py` genera
  `apps/web/lib/estados.generado.ts` desde `apps/api/src/neuralnews/states.py` (fuente de verdad) y
  `apps/web/lib/estados.ts` es el único mapa de insignias. Se eliminaron **3 copias** del mapa
  (noticias, noticias/[id], fuentes) y un **4º mapa distinto** con dos estados inexistentes
  (`CONFIRMED`, `DESACTUALIZADA` en `DossierPanel`). `tests/test_estados_compartidos.py` (5) falla
  si el generado se desfasas o si alguien declara un mapa fuera del módulo compartido
  (rojo→verde verificado con `git stash`).
- **NN-113.13 — archivos grandes.** `features/studio/App.tsx` 907 → **478** líneas (7 hooks nuevos
  en `features/studio/lib/`); `NewsEditorialTab.tsx` 759 → **240** (lista y 3 modales en
  `components/news/`). **Ningún fichero de la web supera las 500 líneas.**
- **NN-113.8 — a11y.** `tools/check_a11y.py` (auditoría ejecutable): **0 bloqueantes · 0 avisos**
  (partía de 8 botones sin nombre accesible y 51 campos sin etiqueta). El analizador escanea JSX
  carácter a carácter: con `[^>]*` las flechas `=>` de los manejadores cortaban la expresión
  regular y **los botones vacíos no se detectaban** (B27).
- **NN-113.9 — lint de clases.** `scrollbar-none` y `studio-root` se usaban y **no existían**
  (B28): la barra de desplazamiento aparecía en Chromium y el envoltorio del Studio no tenía
  altura. Ahora están definidas y `tools/check_clases.py` + `tests/test_clases_web.py` lo vigilan.
- **NN-113.12 — sistema visual.** Todos los componentes viven **una sola vez** en
  `app/globals.css`; 44 composiciones en línea sustituidas por clases del sistema y
  `tools/check_clases.py` falla si vuelve a haber reimplementación: **0 reimplementaciones**.
- **NN-113.15 — Centro de mantenimiento.** El botón «Mantenimiento» abre el `BackupModal` con
  datos veraces: manifiesto de las fuentes generado por `tools/generar_manifiesto_studio.py`
  (SHA-256 reales) y SHA-256 del estado del Studio calculado en el navegador. La interfaz dice
  que **no** es un backup de la base de datos (eso es `scripts/db_backup.py`).

**NN-113.4 / .5 / .11 + B23 (NN-113.16) + B24 (NN-113.17) — COMPLETADAS y COMMITEADAS**
(`f8a7b40`, empujado a `origin beta/v1`).

**NN-113.2 / .3 / .7 — COMPLETADAS con evidencia E.**

- `npx eslint .` → **0 problemas** (antes: el script `npm run lint` **no era ejecutable**; al
  hacerlo funcionar aparecieron 38 errores y 6 avisos reales).
- `npx tsc --noEmit` → **0 errores**. Los 10 `any` se sustituyeron por tipos reales
  (`ConfiguracionImportada`, `NoticiaImportada`, `mensajeDeError`).
- `npm run build` → compila (9 páginas).
- Los 38 errores de lint eran reales: código muerto (16 variables sin usar), `any`, comillas sin
  escapar en JSX y una interfaz vacía. Al retirarlos se eliminaron también props que el Studio
  **nunca usó** (`editorialReferences` y `onAssignArticleToBlock` en `NewsEditorialTab`,
  `onUpdateVisualRefStatus` en `ReferencesTab`, tres props de `ResultTab`).

**Bug real encontrado y corregido al verificar (B22):** en la página de noticia, el aviso
«Guardado como versión N» salía **antes** de refrescar el estado; pulsar «Aprobar esta versión»
actuaba entonces sobre la versión anterior y la API la rechazaba (exige la más reciente). Ahora el
estado se refresca **antes** de avisar y los botones se bloquean mientras se guarda. Lo detectó el
E2E `beta-journey` (falló 1 de 7 en una pasada).

**Falso positivo-costoso (lección):** una tanda de E2E dio **7 fallos de 8** con el error boundary
de React. La causa **no** era el código: un `next start` de una sesión anterior seguía sirviendo el
puerto 3000 y, al reconstruir, el navegador pidió chunks inexistentes (HTTP 400). **Regla: antes de
`npm run build`, detener el servidor del puerto 3000.**

## Trabajo a medias sin verificar

- **NN-113**: `.6`, `.8`, `.9`, `.12`, `.13` y `.15` están verificadas pero **sin commitear**.
- **NN-114**: `pytest.ini` en la raíz (la suite ya pasa desde cualquier directorio),
  `scripts/bootstrap.ps1`, `scripts/start.ps1`, `scripts/stop.ps1` y `.github/workflows/ci.yml`
  **escritos pero sin ejecutar de extremo a extremo**.

## Archivos modificados desde el último checkpoint

Sin commitear (desde `f8a7b40`):

- **Backend**: `apps/api/src/neuralnews/states.py` (etiquetas de verificación, tipo de afirmación y
  paquete; `ESTADOS_DE_LA_APLICACION`).
- **Herramientas**: `tools/generate_estados.py`, `tools/generar_manifiesto_studio.py`,
  `tools/check_clases.py`, `tools/check_a11y.py` (nuevos).
- **Web**: `apps/web/lib/estados.ts`, `lib/estados.generado.ts` (nuevos);
  `features/studio/data/manifiestoStudio.generado.json` (nuevo, generado);
  `features/studio/lib/` (7 hooks nuevos); `features/studio/components/news/` (4 ficheros nuevos);
  `features/studio/App.tsx`, `components/NewsEditorialTab.tsx`, `components/BackupModal.tsx`,
  `components/TopNavigation.tsx`, `components/DossierPanel.tsx`, `components/ReferencesTab.tsx`,
  `components/ResultTab.tsx`, `components/ScriptTab.tsx`, `components/CharacterSheetTab.tsx`,
  `components/BackgroundTab.tsx`, `components/VoiceTab.tsx`, `components/MovementTab.tsx`,
  `app/noticias/page.tsx`, `app/noticias/[id]/page.tsx`, `app/fuentes/page.tsx`,
  `app/lotes/page.tsx`, `app/configuracion/page.tsx`, `app/estudio/page.tsx`, `app/globals.css`.
- **Pruebas**: `tests/test_estados_compartidos.py`, `tests/test_clases_web.py`,
  `tests/test_manifiesto_studio.py` (nuevos).
- **Documentación**: `docs/agente/PLAN_MAESTRO.md`, `docs/agente/REGISTRO.md`,
  `docs/agente/ESTADO.md`.

## Bloqueos y lo que se necesita para resolverlos

| # | Bloqueo | Qué se necesita |
|---|---|---|
| 1 | **R-26**: la gobernanza (`newsV2/`) está fuera de todo repositorio — sin historial, sin remoto, sin copia | **Decisión del propietario**: (a) moverla a `neural-news/docs/governance/` y redirigir las referencias, o (b) versionarla como repositorio propio. No bloquea las fases 5, 6 y 8 |
| 2 | Sin **remoto remoto** de git | **Decisión del propietario**: ¿GitHub/GitLab con credenciales, o el remoto local es suficiente? Afecta a la duración del backup, no a la ejecución |
| 3 | **Cuota desconocida**: no hay forma de consultar la capacidad restante | Ninguna acción; se aplica la sección 8 del objetivo si la capacidad baja |

## Autorizaciones pendientes

1. **Mover `newsV2/` al control de versiones** — cambia rutas documentadas → requiere autorización.
2. **Crear un remoto remoto** (GitHub/GitLab) — acción externa → requiere autorización.
3. **Publicar en producción** — fuera del alcance de este plan; no se hará.

## Cuota y fecha de reinicio

**Desconocido.** No hay herramienta de consulta de cuota en esta plataforma. La capacidad se controla
guardando checkpoint tras cada tarea completada.

## PRÓXIMA ACCIÓN EXACTA

Commitear el lote de NN-113 verificado (`.6`, `.8`, `.9`, `.12`, `.13`, `.15`) y empujarlo a
`origin beta/v1` con el mensaje «NN-113: mapa de estado único, auditoría de accesibilidad,
sistema visual unificado y Studio dividido en hooks». Antes de commitear, comprobar que
`apps/web/features/studio/data/manifiestoStudio.generado.json` está regenerado
(`python tools/generar_manifiesto_studio.py`), porque los hooks que has tocado cambian sus
hashes. Después, seguir con **NN-114** (Fase 6): un solo comando para levantar la pila
(`scripts/bootstrap.ps1` + `scripts/start.ps1` + `scripts/stop.ps1`), ejecutarlos **de extremo a
extremo**, y comprobar que `.github/workflows/ci.yml` refleja la matriz real (pytest, eslint,
tsc, build, E2E).
