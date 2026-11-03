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
`storage/`; se genera `backups/MANIFIESTO_SELLADO_2026-11-01.txt`; se verifican el backup
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

## 2026-11-02 — NN-117: reintegración selectiva del motor editorial (3 de 5)

**Decisión general (ADR-016):** el repo hermano se porta **capacidad a capacidad**, con test de
equivalencia, y **no** se copia ninguna carpeta. Lo que no entra, se descarta **con el motivo
escrito** — que es lo que evita que el port se convierta en deuda invisible.

### Lo que resultó ser el plan equivocado (y se corrigió)

El plan decía portar «zonas seguras / cámara» de `archive/neuralnews-20261101/apps/api/app/domain/camera.py`. Al mirarlo:

- `archive/neuralnews-20261101/apps/api/app/domain/camera.py` del hermano **no** trata de zonas seguras: trata de **presets de cámara y límites de
  glitch** (NN-052).
- Las zonas seguras (`SAFE_ZONE`) están en `archive/neuralnews-20261101/apps/api/app/domain/graphics.py` del hermano, y **no se usan en
  ningún sitio**: es código muerto.

Portar `SAFE_ZONE` tal cual habría sido **traer código muerto**. La carencia real estaba en el
**repo activo**: el gráfico de barras usaba el sistema de márgenes (`MARGIN_L/R/T/B`) y el **rótulo
usaba coordenadas fijas (80, 500)**, que no respetaban ese margen. Es decir: el rótulo podía salirse
del área que la interfaz de la plataforma cubre.

**Decisión:** NN-117.2 se resuelve **arreglando la incoherencia del repo activo** — el rótulo ahora
usa la zona segura compartida (`CARD_MARGIN_*`) y recorta el texto **por ancho real**, no por número
de caracteres. No se ha copiado nada del hermano.

### Lo que sí se ha portado

| Capacidad | De dónde | Qué se ha hecho |
|---|---|---|
| **Argon2id** (NN-117.5 → cierra NN-111.9) | `archive/neuralnews-20261101/apps/api/app/security/auth.py` | `hash_password` usa Argon2id; **la verificación PBKDF2 se mantiene**, así que las contraseñas ya guardadas siguen funcionando (el formato decide el algoritmo) |
| **Backup verificado de BD** (NN-117.1) | `scripts/db_backup.py` | Copia SQLite con la API de backup e `integrity_check`; `pg_dump --format=custom` para PostgreSQL; `verify` no toca la base viva. **Mejora sobre el original: la restauración de PostgreSQL sí se automatiza** contra una base aislada y se comparan los recuentos (en el hermano era manual) |
| **Bóveda de secretos** (NN-117.3) | `archive/neuralnews-20261101/apps/api/app/security/vault.py` | Fernet con `NEURAL_MASTER_KEY`. En la base de datos **sólo hay texto cifrado**; el valor en claro vive en memoria del proceso. Los 5 adaptadores resuelven la clave por «bóveda primero, entorno después» (11 puntos de acceso, todos verificados) |

**Lección aplicada de la Fase 2:** un port no es «copiar el fichero»: es **decidir qué capability
entra, comprobar que el código de origen hace lo que dice y que se usa**, y traer sólo lo vivo.

---

## 2026-11-02 — B23 y B24: dos fallos que sólo aparecieron al ejecutar el E2E

Los dos los destapó el **log del E2E**, no las pruebas: el E2E daba verde mientras el worker
registraba errores por debajo. Merece la pena señalar que **un E2E en verde no basta**: el log del
worker es parte de la evidencia.

### B23 — «Investigar» sobre una noticia aprobada fallaba

```
[worker] job #106 → RETRYABLE_FAILED — ValueError: Transición de estado no permitida
        en story: APPROVED → RESEARCHING
```

`APPROVED → RESEARCHING` no era una transición válida. El trabajo moría con un `ValueError` confuso
y **se reintentaba tres veces** sin explicar por qué. En demo las noticias se fusionan por tema, así
que la segunda prueba del E2E encontraba la noticia ya aprobada.

**Decisión:** reinvestigar una noticia aprobada es **legítimo** (puede haber evidencia nueva) y, como
al editar el guion, la aprobación queda **anulada**: hay que volver a aprobarla. Se añade la
transición y se invalida la aprobación activa en `research_story`.

### B24 — dos borradores simultáneos chocaban con la restricción UNIQUE

```
Original exception was: (sqlite3.IntegrityError) UNIQUE constraint failed:
        script_versions.story_id, script_versions.version
```

El número de versión se calculaba como «el último + 1»: lectura y escritura separadas, con una
ventana de carrera. Al chocar, la sesión quedaba rota y el trabajo se perdía con un error interno
(*«This Session's transaction has been rolled back due to a previous exception during flush»*).

**Decisión:** el intento se hace dentro de un **savepoint**: si choca, sólo se revierte ese
savepoint (la transacción del manejador sigue viva) y se recalcula el número libre. Verificado
rojo→verde con una prueba que reproduce la carrera.

**Lección:** el mecanismo de prueba (un E2E que espera a su trabajo) era más estrecho que el
escenario real (dos workers procesando la misma noticia). Los dos fallos eran **del producto**, no de
las pruebas, y sólo se venían cuando había concurrencia de verdad.

---

## 2026-11-02 — Lección de método (reiterada)

Tres de los hallazgos críticos de la Fase 2 y de la Fase 3 aparecieron **al ejecutar**, no al leer
el código, y en todos los casos la causa era la misma: **el mecanismo de prueba era más estrecho
que la regla que debía comprobar**. Antes de dar por cerrado un requisito hay que demostrar que la
prueba que lo vigila **cubre el requisito entero**.

---

**Estado:** Fases 0, 1 y 2 **COMPLETADAS** y verificadas. Se crea `docs/agente/` dentro del repo
activo para que el checkpoint quede **bajo control de versiones** (parte del riesgo R-26).

**Nota sobre R-26:** la gobernanza de `docs/gobernanza/` sigue **fuera** de todo repositorio. Decidir si se
mueve a `docs/gobernanza/` (cambia rutas ya documentadas) o se versiona aparte requiere
autorización del propietario; **no se ejecuta sin ella**.

---

## 2026-11-02 — NN-113.6: un solo mapa de estado, generado desde el backend

**Qué:** el mapa estado→insignia estaba copiado en tres páginas y había un cuarto mapa **distinto**
en `DossierPanel.tsx`, con dos estados que no existen en el backend (`CONFIRMED`, `DESACTUALIZADA`).

**Decisión:** la fuente de verdad de estados y etiquetas es `apps/api/src/neuralnews/states.py`.
`tools/generate_estados.py` genera `apps/web/lib/estados.generado.ts` y `apps/web/lib/estados.ts`
es el **único** lugar donde vive el mapa de insignias (presentación).
`tests/test_estados_compartidos.py` falla si el fichero generado se desfasas o si alguien declara un
mapa de estados fuera del módulo compartido.

**B26 (nuevo, menor):** `DossierPanel` hacía su propio `fetch` al API: era un cuarto cliente HTTP y
se saltaba el cliente único. Corregido al usar `lib/http.ts`.

---

## 2026-11-02 — NN-113.13: el Studio se divide en hooks con nombre

`features/studio/App.tsx` tenía 907 líneas y mezclaba siete responsabilidades. Ahora el componente
es presentación y cableado, y la lógica vive en `features/studio/lib/`: `useHidratacionStudio`,
`useGuardadoPasos`, `useNoticiasStudio`, `useReferenciasStudio`, `useFlowStudio`,
`usePaqueteProduccion` y `usePromptFinal`. `NewsEditorialTab.tsx` (759 líneas) se dividió en la
lista y tres modales, en `components/news/`.

**Regla que no se toca:** al guardar, el estado del servidor manda en la primera carga. La
hidratación conserva esa regla (si el servidor trae un paso, gana; si no, se usa el valor objetivo).

---

## 2026-11-02 — NN-113.8 y NN-113.9: auditorías ejecutables, no opiniones

La auditoría de accesibilidad y el lint de clases se escriben como **scripts** que se ejecutan en la
sesión y devuelven código de salida: sin ellos, decir que la web es accesible no es una evidencia.

**B27 (nuevo, real):** el analizador de JSX usaba `[^>]*` para leer los atributos; dentro de los
manejadores hay flechas (`=>`) que cortaban la expresión regular a medias y los botones vacíos **no
se detectaban**. Con el escáner correcto aparecieron 8 botones sin nombre accesible y 51 campos sin
etiqueta: estaban ahí desde el principio. Corregidos → **0 bloqueantes, 0 avisos**.

**B28 (nuevo, real):** dos clases se usaban y **no existían**: `scrollbar-none` (la barra de
desplazamiento horizontal aparecía en Chromium) y `studio-root` (el envoltorio del Studio no tenía
altura, así que la raíz `min-h-full` no crecía). Ahora están definidas y el lint falla si se usa una
clase propia inexistente.

**Riesgo detectado al automatizar:** una migración que copia la etiqueta visual al `aria-label`
puede copiar la **equivocada** (la del campo anterior). Se revisaron una a una las 17 etiquetas
migradas y se corrigieron 8 que estaban mal: un `aria-label` incorrecto es peor que ninguno.

---

## 2026-11-02 — NN-113.12: un único sistema visual

Los componentes vivían en dos sitios: `globals.css` para las páginas del producto y reimplementados
en línea por el Studio. Ahora todos los componentes están definidos **una sola vez** en
`apps/web/app/globals.css` (con sus variantes compactas) y 44 composiciones en línea se sustituyen
por clases del sistema, visualmente idénticas. `tools/check_clases.py` falla si aparece una
reimplementación: **0 reimplementaciones en línea**.

---

## 2026-11-02 — NN-113.15: el Centro de mantenimiento, con datos veraces

`BackupModal` estaba en el repo **sin usar** (B18) y sus datos (`fullFilesMap`) ya no existían: el
código del Studio vive en el repositorio, no incrustado en la aplicación. Ahora se cablea con lo que
es verdad: el manifiesto de las fuentes lo calcula `tools/generar_manifiesto_studio.py` sobre los
ficheros reales (con SHA-256) y el estado del Studio se audita en el navegador. La interfaz dice de
forma expresa que **no** es un backup de la base de datos: eso es `scripts/db_backup.py` (dump de
PostgreSQL verificado).

---

## 2026-11-02 — Lección de método: no reconstruir bajo un servidor en marcha

Una tanda de E2E dio **7 fallos de 8** con el error boundary de React. La causa no era el código: un
`next start` de una sesión anterior seguía sirviendo el puerto 3000 y, al reconstruir
(`npm run build`), el navegador pidió chunks que ya no existían (HTTP 400) y React cayó al error
boundary. Con la pila limpia (web detenido antes de reconstruir): **8 passed**.

**Regla:** antes de `npm run build`, detener el servidor del puerto 3000. Es exactamente el
`EADDRINUSE` que se vio al intentar arrancar un segundo servidor.

---

## 2026-11-02 — NN-114: la instalación se ejecuta de verdad (y encuentra dos fallos)

El criterio de NN-114.1 es «clon limpio → pila arriba → suite verde». Eso no se comprueba
**escribiendo** el script: se comprueba **ejecutándolo**. Al ejecutarlo aparecieron dos fallos
reales que ningún lectura previa habría detectado.

**B30 (nuevo, real):** `scripts/start.ps1` arrancaba la API y el worker, pero **la web no**: en
Windows, `Start-Process -FilePath "npm"` falla con «no es una aplicación Win32 válida» porque
`npm` es `npm.cmd`. El script moría con error y la pila se quedaba a medias. Corregido resolviendo
`npm.cmd` con `Get-Command`. Verificado: API 200, web 200, worker activo.

**B31 (nuevo, real):** el CI usaba `working-directory: neural-news` en **todos** los pasos, pero el
repositorio **es** la raíz del producto (`apps/`, `infra/`, `tests/` en la raíz): al hacer checkout
en GitHub no existe ese directorio y el CI fallaría en el primer paso. Corregido: se usa el
directorio de trabajo por defecto y `cache-dependency-path` apunta a `apps/...`.

**B29 (nuevo, real):** `PUT /api/v1/settings/score-weights` devolvía **500** si un peso no era un
número («0,75» con coma decimal): la excepción se escapaba sin traducir. Ahora se rechaza con un
**422** que dice qué peso falla y por qué. Rojo→verde verificado con `git stash`.

**B26 (menor):** `DossierPanel` hacía su propio `fetch`: era un cuarto cliente HTTP y se saltaba el
cliente único. Corregido al usar `lib/http.ts`.

**NN-114.3 — módulos sin cobertura.** `providers/research.py`, `providers/video_analysis.py` y
`api/ops.py` tenían capacidad real sin ninguna prueba. Ahora hay 31 pruebas que comprueban las
reglas que importan: la evidencia de demo usa el dominio reservado `.invalid`, una opinión no se
«verifica», una afirmación sin evidencia **no** se marca como `SUPPORTED`, sin clave el adaptador
**falla** en vez de simular, y la salida de análisis de vídeo se marca siempre como
`VIDEO_ANALYSIS` con `is_verbatim=False`.

**NN-114.4 — el contrato OpenAPI se versiona y se verifica.** `tools/exportar_openapi.py` genera
`docs/openapi.json` desde la aplicación real y falla si el fichero versionado difiere. El test
`tests/test_openapi_exportado.py` lo comprueba en la suite: ya detectó un desfase real (la
descripción del endpoint que cambió al corregir B29).

**NN-114.6 — la suite no depende del directorio.** Con `pytest.ini` en la raíz y `pythonpath = .`,
la suite pasa desde la raíz **y** desde `apps/api` (`python -m pytest -q ../../tests` → exit 0).
Los dos pasos están en el CI.

**NN-114.7 — desviación.** No hay capacidad de grabar vídeo en esta sesión. Se deja
`evidence/instalacion_desde_clon_limpio.md` con la transcripción literal de la instalación real y
el hallazgo B30 que salió de ella.

---

## 2026-11-02 — Fase 8: métricas, alertas y presupuesto

**NN-115.3/.4 — `neuralnews/metrics.py`.** Antes el operador sólo veía trabajos sueltos. Ahora
`GET /api/v1/metrics` devuelve **métricas** (p95 y media de duración por rango más cercano, tasa
de fallo, profundidad de cola, desglose por tipo y por `error_kind`) y **alertas** (cola parada,
lease vencido, presupuesto al 80 % y fallo repetido del mismo tipo). Todo se calcula **de la base
de datos**, no de memoria: sobrevive a un reinicio y funciona con varios workers. La página
`/ops` los enseña arriba, con `role="alert"`.

**NN-115.5 — prueba cronometrada.** `tests/test_metricas_alertas.py` mide el tiempo desde el
fallo hasta que la alerta aparece en lo que consume la UI: **menos de 60 s**.

**NN-116 — el presupuesto ya se verificaba antes de la llamada** (`assert_paid_call_allowed` antes
de llamar al modelo, a la búsqueda o al análisis de vídeo; si se agota, el trabajo queda `FAILED`
con `error_kind="budget"`). Lo que faltaba era **decirlo**: estaba implementado y sin marcar en el
plan. Ahora las tres filas están con su evidencia.

**B32 (nuevo, real):** `tools/exportar_openapi.py` importaba la aplicación, y **importar la
aplicación aplica las migraciones pendientes**: al exportarlo con el E2E en marcha, la DDL de
SQLite tomó el bloqueo y la API en marcha **dejó de responder** (el E2E se quedó sin servicio y
tardó 25 min en expirar). El exportador ahora usa una **base temporal aislada**: el contrato
OpenAPI no depende de los datos. **Regla: ninguna herramienta que importe la aplicación puede
tocarla con la pila en marcha.**

---

## 2026-11-02 — NN-117.4, .6, .7 y .8: lo que faltaba del hermano

**NN-117.4 — rutas de modelo con instantánea.** Port de `model_routes` (migración `c0f68f32807d`
del hermano): tabla `model_routes` (tarea, proveedor, modelo, prioridad, revisión de configuración),
`jobs.model_snapshot` y `services/model_routes.py`. El trabajo **resuelve** su ruta al encolarse y
guarda la instantánea: cambiar la ruta después **no** altera un trabajo en marcha. Sin rutas
configuradas se usa el modelo de la configuración: **el comportamiento no cambia** por tener la
tabla.

**NN-117.6 — subtítulos SRT/VTT.** `services/subtitles.py` genera SRT y VTT desde los
`SourceSegment` reales, con el texto **íntegro** (un subtítulo que «mejora» el texto de la fuente
sería una falsificación) y tiempos monótonos comprobados.

**NN-117.7 — contradicciones de cifras.** `services/contradictions.py` **propone** la contradicción
(`action: "PROPOSED"`) y no cambia ningún estado: quien revisa es una persona. Adaptación al
vocabulario de este producto: el estado sugerido es `CONTRADICTED`, no `DISPUTED`.

**NN-117.8 — ADR de los descartes.** `docs/adr/ADR-022-descartes-del-port.md` deja por escrito, una
por una, las capacidades del hermano que **no** entran y por qué: planificador de feeds, *briefs*
versionados, catálogo de prompts, gráficos line/timeline/percentage, ZIP de Flow (que entra **con
adaptación**, no íntegro), CAS/clasificador de riesgo. Un descarte sin motivo escrito es deuda
invisible: al menos queda decidido y revisable.

---

## 2026-11-03 — Entrega de la beta local `1.0.0-beta.1`

**Qué se hizo.** El repositorio pasó a llamarse `proyecto final` (raíz real de Git), declaró su
versión beta, se documentó la entrega y se verificó con **14 comprobaciones automáticas** que
dejan veredicto, código de salida y log íntegro.

**Decisiones propias (con motivo):**

1. **La gobernanza entra como `docs/gobernanza/`, no como `newsV2/`.** `newsV2/` estaba **fuera**
   del repositorio (era hermana de la carpeta del producto): no se puede versionar lo que no está
   dentro. Se movió el contenido real (328 ficheros, 15,2 MB) y se redirigieron las referencias
   documentadas (README, `ESTADO_REAL.md`, `IMPLEMENTACION_REALIZADA.md`, plan y registro).
2. **Lo que no cumplía DEC-01 se queda fuera y se anota**: `newsV2/neural-news/` es una **copia
   duplicada del repositorio con su propio `.git`** (un `.git` anidado no se puede versionar: git
   lo trataría como submódulo) y `newsV2/flow-recovery/node_modules` contiene un binario de
   105 MB. No se ha tocado nada de ahí.
3. **El manifiesto SHA-256 de la gobernanza se conserva tal cual**, aunque 3 de sus ficheros ya no
   cuadren: se selló el 2026-10-30 y después se actualizaron legítimamente (el backlog en la
   Fase 0 y el registro de decisiones con R-26). Re-sellarlo escondería el cambio; el test
   documenta la excepción de forma explícita.
4. **La verificación se ejecuta con la configuración local del proyecto** (el `.env`): sin
   `NEURAL_ENV=local` el build falla **por diseño** (gate G5) y la comprobación no distinguiría
   «producto roto» de «entorno sin configurar».

**Hallazgos reales encontrados y corregidos en la entrega:**

- **B29**: `PUT /settings/score-weights` devolvía **500** con un peso no numérico; ahora **422**
  con el peso que falla.
- **B30**: `scripts/start.ps1` no arrancaba la web en Windows (`npm.cmd` no es un ejecutable
  Win32).
- **B31**: el CI usaba `working-directory: neural-news`, que no existe al hacer checkout.
- **B32**: importar la aplicación **aplica migraciones**: `exportar_openapi.py` con la pila en
  marcha dejaba la API sin responder. Ahora usa una base aislada.
- **B33**: `scripts/stop.ps1` no paraba el servidor del E2E (el patrón con barras normales no
  encajaba con la ruta de Next en Windows).
- **B34**: `tools/scan_secrets.py` **reventaba** al imprimir un hallazgo en una consola cp1252, y
  escaneaba el árbol de trabajo en vez de lo versionado (falsos positivos con el `.env` local).
- **B35**: la auditoría de evidencia del plan no comprobaba nada (comparaba la extensión con
  punto y la rama de símbolos se encontraba a sí misma en la documentación). Detectado al
  inyectar un fichero falso: rojo y luego verde.
- **B36**: cuatro `print()` del worker rompían el log JSON por evento; ahora son eventos
  `log_event`.
- **B37**: Next infería la raíz del workspace buscando un `package-lock.json` hacia arriba y cogía
  uno suelto del directorio personal: `outputFileTracingRoot` la fija en la raíz del repositorio.
- **B38**: la beta no tenía icono: el navegador pedía `/favicon.ico` y recibía un 404 en cada
  carga. Añadido `app/icon.svg`.

**Además:** la prueba real de **PostgreSQL** dejó de estar en *skip* (hay un PostgreSQL local:
`scripts/preparar_base_pg_test.py` crea una base aislada) → la suite queda en **386 tests y
0 skip**.

**Estado final:** `BETA_LISTA`. Rama `release/1.0.0-beta.1`, commit `1c63a3a`, tag anotado
`v1.0.0-beta.1`, **sin push**.

---

## 2026-11-03 — Auditoría de la entrega (y lo que encontró)

Se añade `scripts/auditar_entrega.mjs`: comprueba **una por una** las cuatro condiciones del
encargo contra el estado real (no contra lo que dice el informe). Resultado: **17/17 PASA**.

**B39 (nuevo, real):** el resumen de verificaciones se escribía en
`docs/entrega/RESUMEN_VERIFICACIONES.md`, pero **toda** la documentación lo enlazaba
desde `docs/entrega/RESUMEN_VERIFICACIONES.md`: un enlace roto en el README, en el resumen
completo y en el informe final. Lo detectó la auditoría (no un revisor: el fichero no existía
donde se decía que estaba). Corregido: el script de verificación lo escribe ahora en su sitio, y
el duplicado antiguo se ha retirado.

**B40 (menor):** la primera versión de la auditoría fallaba en «el checkpoint declara un único
estado beta» porque la expresión regular no admitía el acento grave del markdown
(`` `estado_beta`: BETA_LISTA ``). Era un fallo de la auditoría, no del checkpoint: se corrigió
la expresión y se volvió a ejecutar (17/17).

**Lección (la segunda de esta entrega):** una comprobación que **no puede fallar** no sirve.
La auditoría nació precisamente para eso: comprobado primero contra un estado real y con un
referente roto introducido a propósito, no contra un «parece que está bien».

---

## 2026-11-02 — B32 y B33: dos formas de romper la ejecución sin tocar el producto

Estos dos hallazgos no son del producto: son de **orquestación**, y los dos costaron
una tanda de E2E entera (25 minutos de espera y dos E2E cancelados).

**B32 — importar la aplicación aplica migraciones.** `tools/exportar_openapi.py` importa la
aplicación para leer su contrato OpenAPI; al importarla, la aplicación **aplica las migraciones
pendientes** sobre la base configurada. Con la pila en marcha, la DDL de SQLite tomó el bloqueo y la
API dejó de responder: el E2E se quedó sin servicio. El exportador ahora usa una **base temporal
aislada** (el contrato no depende de los datos) y deja `NEURAL_EXPORT_USE_LIVE_DB=1` para quien
quiera la base real a propósito. **Regla: ninguna herramienta que importe la aplicación puede
tocarla con la pila en marcha.**

**B33 — `stop.ps1` no paraba el servidor del E2E.** El patrón `next/dist/bin/next` (con barras
normales) no encaja con la ruta real en Windows
(`node_modules\.bin\\..\next\dist\bin\next`, con barras invertidas): el servidor se quedaba vivo.
**Regla:** lo que no se detiene, lo hereda la siguiente ejecución.

**La consecuencia encadenada (la que costó el tiempo):** un `next start` superviviente sirvió un
build **anterior**; al reconstruir, los chunks se sustituyeron en disco pero el servidor viejo
seguía sirviendo el manifiesto viejo, así que el navegador pedía chunks inexistentes (**HTTP
400**), la página se quedaba en «Cargando…» sin hidratar y el E2E agotaba el tiempo esperando un
botón que no aparecía nunca. **Esto ya había pasado una vez** (se creyó que era culpa del
refactor del Studio y no lo era).

**Se blindó por los dos lados:**
1. `scripts/stop.ps1` usa expresiones regulares que cubren las dos rutas de Next (B33).
2. `apps/web/playwright.config.ts` pone **`reuseExistingServer: false`**: el E2E levanta **siempre**
   su propia API, worker y web. Si un puerto está ocupado, Playwright lo dice con claridad en vez
   de envenenar la ejecución, y un servidor viejo ya no puede hacer de guía silencioso.

**Regla general:** antes de un E2E, `stop.ps1`; después de un `npm run build`, comprobar que
nadie sirve ese puerto.

---

## 2026-11-02 — Supervisor externo añadido por petición del propietario

El propietario ha añadido al proyecto un **mecanismo externo de relanzamiento**: `PROMPT.md` (el
prompt que se pasa al agente) y `supervisor.sh` (el guion de Bash que lo lanza, lee su etiqueta de
salida y gestiona la espera por cuota).

**Lo que había que adaptar para que encajara con este proyecto:**

1. El supervisor valida el proyecto con `grep -q "\[ \]" docs/agente/PLAN.md`: hacía falta ese
   fichero, con **casillas**, y no existía (el plan maestro es una tabla). Se añade
   `tools/generar_plan_casillas.py`, que **genera** `docs/agente/PLAN.md` desde
   `PLAN_MAESTRO.md`: una sola fuente de verdad y ninguna lista que pueda divergir.
   `tests/test_plan_casillas.py` falla si se desfasas.
2. **Bug real del generador (encontrado al ejecutarlo):** las tablas del plan maestro contienen
   pipes escapados (``local\|beta\|prod``). Partir la fila por cualquier pipe **desplazaba las
   columnas** y una fila completada (`NN-111.1`) aparecía como pendiente: el supervisor nunca
   habría dado el proyecto por terminado. Corregido partiendo solo por pipes **no** escapados.
3. Las decisiones del propietario **no** se marcan como `[ ]` en `PLAN.md`: no son tareas
   ejecutables y, de estarlo, el supervisor no cerraría nunca el proyecto. Viven en
   `docs/agente/TAREAS.md` (`DEC-01`, `DEC-02`, `SUP-01`, `SUP-02`).
4. `docs/agente/TERMINADO` e `docs/agente/espera.txt` son **estado de máquina**: se ignoran en git.
   `TERMINADO` está creado, así que el supervisor no relanza; **bórralo** para retomar el trabajo.
5. `AGENTE_CMD` en `supervisor.sh:5` sigue siendo un marcador de posición: hay que poner el comando
   real de esta máquina (`SUP-01`). Y el guion es **Bash** con `crontab`: en Windows hace falta
   WSL o Git Bash (`SUP-02`). **No se ha configurado ningún `crontab`**: no hay un programador
   real verificado en este sistema, y el mecanismo `cron_create` de la plataforma no se configura
   mientras el plan esté cerrado (§6.6.6).

**Corrección de un recuento:** se afirmaba que el plan tenía «95 filas COMPLETADAS»; el
número real de **filas de tarea es 89** (las 6 de más eran líneas de texto que contienen la
palabra). El checkpoint dice 89.

---

## 2026-11-02 — B35: la auditoría de evidencia audtaba nada (y nadie lo notó)

El contrato exige comprobar que lo marcado COMPLETADA lo esté de verdad (§3.4 del `/goal`). La
suite, el E2E y los lints ya lo cubrían por el lado del **comportamiento**, pero no por el lado de
las **referencias**: una fila podía citar un fichero borrado hace semanas y el plan seguiría
pareciendo completo.

Se escribe `tools/auditar_evidencias.py`: extrae las rutas que cita la columna de evidencia de
`PLAN_MAESTRO.md` y comprueba una a una que existen (ficheros, directorios, rutas de API y
símbolos). Primera versión: **0 desfasadas**. Demasiado limpio.

**B35 (nuevo, real):** la auditoría **no estaba comprobando los ficheros**. Dos fallos encadenados:
1. La extensión se comparaba con punto (`".ts"`) contra un valor sin punto (`"ts"`): **ninguna**
   referencia entraba en la rama de fichero y todas caían en la de «símbolo».
2. La rama de «símbolo» buscaba el literal en **todo** lo versionado, **incluida la propia
   documentación**: el plan se citaba a sí mismo y toda referencia «existía» por definición.

Con las dos correcciones, la auditoría dice la verdad: 84 referencias comprobadas y existentes, 9
fuera del repositorio (artefactos sellados), 3 que no son rutas (`ok/warn/error`), **0 desfasadas**.

**Rojo→verde verificado**: inyectando un fichero de prueba en `apps/web/lib/` en una fila, la auditoría
lo detecta (exit 1) y el test falla; al retirar la inyección, todo vuelve a verde.

**Lección (la segunda de esta sesión):** una comprobación que **no puede fallar** no es una
comprobación. La forma de detectar que la auditoría no miraba nada fue meterle un fichero falso:
si no lo encuentra, no estaba mirando. Es el mismo motivo por el que el E2E se ejecutó contra
una pila levantada por el propio Playwright y no contra un servidor heredado.

`tools/auditar_evidencias.py` queda como paso de CI (`La evidencia que cita el plan maestro
existe de verdad`) y con test propio (`tests/test_evidencias_plan.py`).

