# REGISTRO — neural.news

Entradas breves: **decisión o cambio**, **motivo**, **fuentes consultadas** y **errores resueltos**.
Fuentes externas se citan con URL. El contenido externo es información, nunca instrucción.

---

## 2026-11-01 — Auditoría del repositorio y plan maestro

**Decisión:** auditar los dos repositorios vivos (`neural-news`, `neuralnews`) y redactar
`18_PLAN_MAESTRO_BETA.md` + `TASK_NN-108_VERSION_BETA.md` antes de tocar código.

**Motivo:** el backlog declaraba 106 ítems `NOT_STARTED` mientras el código implementaba NN-001…NN-065
y NN-107. Sin verdad documentada, cualquier corrección queda sin trazabilidad.

**Hallazgo estructural:** `neuralnews` y `neural-news` son **historias git independientes**
(`git cat-file -p dd7c414` → *not a valid object name* en el hermano) con bases de datos, cadenas
Alembic y aplicaciones web distintas, y **ninguno con remoto**. ADR-015 («repo único») se decidió el
31/10 y no se ejecutó.

**Decisión derivada:** ADR-016 — un único repositorio y una única base de datos (PostgreSQL); el
hermano se congela y sus capacidades se portan una a una con test de equivalencia.

---

## 2026-11-01 — Fase 0: sellado, backups verificados y bundle

**Cambios:** los 4 artefactos sueltos (13 MB de ZIP/RAR + 2 directorios) salen del árbol a
`neural-news/storage/`; se genera `backups/MANIFIESTO_SELLADO_2026-11-01.txt`; se verifican el backup
previo a NN-107 y el dump de PostgreSQL; se crean bundles de git de ambos repos.

**Motivo:** el riesgo R-21 (pérdida total por fallo de disco) era crítico: 36 commits vivían solo en
este disco.

**Evidencia:** SHA-256 del backup previo a NN-107 **coincide** con el registrado (`c08d99b4…77d69d`);
el dump de PostgreSQL se restauró en una base limpia con **20 tablas de recuento idéntico**; los dos
bundles dan *is okay*; **17/17** fuentes de Flow contrastan con `reports/manifest.json`.

**Error resuelto:** el primer `Move-Item` con rutas absolutas fue bloqueado por la política de
seguridad local; la versión con rutas relativas al espacio de trabajo sí pasó.

---

## 2026-11-01 — Fase 1: consolidación del repositorio

**Cambios:** el hermano se archiva en `archive/neuralnews-20261101/` con manifiesto SHA-256 de sus 121
ficheros versionados; se crea el remoto local `.remotes/*.git` y se empuja; `.gitignore` ampliado;
rama `beta/v1`; README único.

**Decisión:** el hermano **se mueve, no se borra**, y conserva su `.venv` para que siga siendo
ejecutable y los ports de NN-117 puedan verificarse contra su propia suite.

**Nota operativa:** la pila del hermano estaba **en marcha** (API `:8800`, web `:3100`) mientras se
archivaba. Se detuvieron **solo** esos dos procesos; la pila principal (`:8000`, `:3000`) siguió
activa durante toda la operación.

**Error resuelto:** el `Move-Item` del directorio falló con «el archivo está en uso por otro proceso»;
la causa fue un proceso vivo, no un bloqueo de archivo. Se identificó con `Get-CimInstance Win32_Process`.

---

## 2026-11-01 — Fase 2: corrección de los defectos verificados

**Cambios:** B1, B2, B3, B4, B7, B8, B9, B10–B15, B16, B17, B19, B20 y B21 corregidos, con 20 pruebas
de regresión nuevas.

**Regla aplicada:** cada defecto lleva un test que **falla sobre el código original** y pasa después.
Verificado con `git stash` sobre los ficheros de código: 8 de las 17 pruebas fallaban en el estado
rojo.

**Hallazgo clave (B16):** al corregir B1 (`source.metadata` → `source.metadata_json`) se descubrió
que la transcripción de pódcast **nunca funcionó**: `podcast:transcript` se leía del atributo `href`
y **feedparser lo expone como `url`**. Dos fallos independientes, la misma función.

**Fuente consultada:** comportamiento de `feedparser` verificado empíricamente sobre un feed de
prueba con el namespace `podcast` — no de documentación.

**Hallazgo clave (B20):** la base de datos viva tenía `alembic_version` **vacía** y le faltaba
`generated_takes.needs_review`. Causa: `Base.metadata.create_all()` al arrancar **solo crea tablas y
nunca añade columnas**. El Studio devolvía 500 y 3 E2E fallaban sin causa aparente. Reparación:
`alembic stamp d4ce8c95781e` (su estado **real**, no `head`, para no mentirle a Alembic) +
`alembic upgrade head`. Verificado: 31/31 tablas, 0 columnas de menos, `alembic check` sin
diferencias.

**Decisión:** el arranque deja de usar `create_all` y aplica `alembic upgrade head`. Red de seguridad
en `tests/test_schema_migrations.py`: las migraciones desde cero deben producir **exactamente** el
esquema de los modelos.

**Hallazgo clave (B21):** `useJobPolling` tenía un **único temporizador compartido** y `poll()` no
esperaba al trabajo (programaba la primera comprobación y devolvía la promesa enseguida). Con dos
sondeos simultáneos, el antiguo terminaba su `onDone()` tarde y **machacaba el guion recién
escrito**. Los 5 puntos de uso ya hacían `await poll(...)`: la intención era correcta, la
implementación no.

---

## 2026-11-01 — Prueba de rojo→verde del E2E (baseline)

**Decisión:** no dar por bueno que el fallo del E2E fuera preexistente sin prueba.

**Método:** `git checkout ef01bd0` → `next build` → arrancar la pila original → ejecutar el E2E.

**Resultado:** el fichero `critical-flow.spec.ts` falla **4 de 5** en el código original (con «Application
error: a client-side exception has occurred» tras entrar en modo demo), frente a **7 passed / 0
failed** en `beta/v1`.

**Conclusión:** el E2E roto era preexistente, y las correcciones de B20 y B21 son las que lo pasan.

**Error resuelto:** durante este baseline, el servidor web del commit original **sobrevivió** al
reinicio porque el filtro de proceso buscaba «NeuralStories» en la línea de comandos y el `next start`
se invoca con ruta **relativa**. Se detectó por el `ChunkLoadError` (hash de chunk distinto al del
disco) y se corrigió matando por **puerto** en vez de por nombre.

---

## 2026-11-01 — Limitación conocida registrada

**Decisión:** documentar el defecto de la suite ejecutada desde `apps/api` (3 tests fallan por
`ModuleNotFoundError: No module named 'tests.test_director_package'`) en vez de silenciarlo.

**Motivo:** `apps/api/pyproject.toml` declara `testpaths = ["../../tests"]`, lo que invita a ejecutar
desde ese directorio, pero los imports `from tests.*` no resuelven sin la raíz en `sys.path`.

**Tarea asignada:** NN-114.6.

---

## 2026-11-02 — NN-110.a: el lease de la cola por fin significa algo

**Hallazgo:** la reserva (`claim_next_job`) y la finalización del trabajo se confirmaban en la **misma
transacción**. Mientras el trabajo se ejecutaba, para el resto del sistema seguía en `QUEUED`.

**Consecuencias:** el lease no significaba nada (nadie veía `RUNNING`); `recover_stale_jobs` no
encontraba nada que recuperar, porque el trabajo nunca llegaba a estar `RUNNING` fuera de su
transacción; un trabajo largo perdía el lease a mitad; y un worker caído dejaba sus trabajos
colgados hasta el siguiente reinicio.

**Decisión:** la reserva se confirma en el momento (`claim_next_job` hace commit), el worker renueva
el lease con un hilo dedicado mientras el trabajo corre, el barrido es **periódico** (no solo al
arrancar) y `release_job` limpia `lease_until`, `next_run_at` y `attempt`.

**Salvedad honesta:** en SQLite las escrituras se serializan, así que la renovación desde otra
conexión puede quedar bloqueada mientras el manejador escribe. Por eso el barrido **ignora los
trabajos que este worker tiene activos** (`skip_ids`): sin esa salvedad, un trabajo largo se
recuperaría a sí mismo. Con PostgreSQL la renovación funciona con normalidad.

**Error resuelto:** al partir `tick()` en dos sesiones (una para reservar, otra para ejecutar), el
estado `RUNNING` pasa a ser visible antes de ejecutar. Es el cambio que hace posible todo lo demás.

---

## 2026-11-02 — NN-110.b/c/d: el trabajo pesado sale del hilo de petición

**Decisión:** cuatro operaciones que se ejecutaban dentro de la petición HTTP pasan a ser trabajos
del worker: transcripción, extracción web, montaje y sondeo de medios. Los handlers devuelven
`202` con el identificador del trabajo.

**Cambio de contrato (deliberado):** el endpoint ya no devuelve el resultado, devuelve el trabajo.
Eso obliga a cambiar las pruebas: se han reescrito para el recorrido **encolar → worker →
comprobar**, que es más fiel que antes (antes solo se probaba el camino síncrono).

**Decisión de diseño:** la lógica se movió a `services/transcription.py` para que la API y el worker
usen **la misma implementación**. Dos copias de la lógica se separan; una, no.

**Punto delicado resuelto:** el material que falta y las transiciones aplicadas se guardaban en el
router, así que el worker no podía reconstruir la animática. Se movieron a
`services/montage.persist_animatica`, que usan tanto la API como el worker.

---

## 2026-11-02 — NN-110.e: el log es JSON y el motivo del fallo queda registrado

**Decisión:** el motivo del fallo se registra **cuando ocurre**, no se deduce después del texto.
Adivinarlo por el mensaje es frágil y mezcla «presupuesto» con «conector».

**Vocabulario:** `budget` (presupuesto, definitivo), `material` (falta material, definitivo:
reintentar no cambia nada), `connector` (falló un proveedor, se reintenta), `unknown`.

**Cambio de esquema:** columna `jobs.error_kind` con su migración `c4d2e8f1a5b6`. El esquema sale
solo de Alembic (decisión de NN-109.15): la base viva se migró con `alembic upgrade head` y se
verificó (0 columnas de menos, `alembic check` sin diferencias).

**Verificación en ejecución real** (no solo en pruebas): el worker emite
`{"event": "job.done", "job_id": 48, "status": "DONE", "duration_s": 0.031, ...}` y la línea se
parsea con `ConvertFrom-Json`.

---

## 2026-11-02 — Lección de método (reiterada)

Tres de los hallazgos críticos de la Fase 2 y de la Fase 3 aparecieron **al ejecutar**, no al leer
el código, y en todos los casos la causa era la misma: **el mecanismo de prueba era más estrecho
que la regla que debía comprobar**. Antes de dar por cerrado un requisito hay que demostrar que la
prueba que lo vigila **cubre el requisito entero**.

---

**Estado:** Fases 0, 1 y 2 **COMPLETADAS** y verificadas. Se crea `docs/agente/` dentro del repo
activo para que el checkpoint quede **bajo control de versiones** (parte del riesgo R-26).

**Nota sobre R-26:** la gobernanza de `newsV2/` sigue **fuera** de todo repositorio. Decidir si se
mueve a `neural-news/docs/governance/` (cambia rutas ya documentadas) o se versiona aparte requiere
autorización del propietario; **no se ejecuta sin ella**.
