# ADR-022 — Descartes del port: qué **no** entra del repositorio hermano y por qué

**Estado:** vigente · **Decisión relacionada:** ADR-016 (un único repositorio y una
única base de datos) · **Fecha:** 2026-11-02

## Contexto

`archive/neuralnews-20261101/` (el hermano congelado) y `neural-news` (el
repositorio activo) implementaban el mismo encargo con **bases de datos, cadenas
de migraciones y aplicaciones web distintas**, y ninguno con remoto. ADR-016
decidió: un solo repositorio, una sola base de datos (PostgreSQL), y el hermano
**congelado como fuente de capacidades**: se porta **capacidad a capacidad**, con
test de equivalencia, y **no** se copia ninguna carpeta.

Eso obliga a responder, para cada capacidad del hermano que no entra, **por
qué**. Sin ese escrito, los descartes se convierten en deuda invisible: nadie
sabe si son una decisión o un olvido.

## Regla aplicada

> Una capacidad del hermano entra si (a) es necesaria para el recorrido de la
> beta, (b) se puede portar **con su test de equivalencia**, y (c) no exige
> material o credenciales que no tenemos. Si falla (a), (b) o (c), **se descarta
> por escrito** y su código **no** se copia.

Lo que sí ha entrado (con test de equivalencia) hasta ahora: backup verificado
de base de datos (NN-117.1), zonas seguras (NN-117.2), bóveda de secretos
(NN-117.3), Argon2id (NN-117.5), rutas de modelo (NN-117.4), subtítulos
SRT/VTT (NN-117.6) y contradicciones de cifras (NN-117.7).

## Los descartes

### 1. Programador de feeds con *jitter* (hermano: NN-028, `app/scheduler/`)

**Qué era:** un proceso que recorría periódicamente las fuentes RSS, con
dispersión aleatoria (*jitter*) e idempotencia por periodo.

**Por qué no entra:** el producto **no** tiene un catálogo de feeds que el
proveedor deba vigilar por su cuenta. La entrada de contenido en la beta es
**explícita**: la persona aporta una URL, un texto o un archivo, y el sistema lo
analiza. Un planificador que recorre fuentes por su cuenta implica una política
de qué se vigila y con qué frecuencia, y esa política pertenece al operador de
la instalación, no al producto. Además, el *mismo* trabajo puede hacerlo el
`worker` con un tipo de trabajo de **recogida periódica** cuando exista una
fuente que lo justifique, sin arrastrar un proceso y una tabla propias.

**Estado:** `NO_IMPLEMENTADO` (fuera de la primera ventana). No es código muerto
en este repositorio: nunca se copió.

### 2. *Briefs* editoriales versionados con abstención honesta (hermano: NN-033)

**Qué era:** un documento de encargo editorial con versiones, able de responder
«INSUFICIENTE_MATERIAL» cuando no había material suficiente.

**Por qué no entra:** el motor de investigación que **sí** entra
(`services/research.py`) ya aplica la misma regla en el sitio donde importa: si
una afirmación no tiene evidencia, queda `UNVERIFIED` y con la nota de que no
se ha encontrado evidencia. Un *brief* como entidad persistida y versionada
sería una segunda capa de gobierno editorial sobre un motor que ya es honesto
en su salida, sin aportar capacidad observable al recorrido de la beta.

**Estado:** `NO_IMPLEMENTADO`. La capacidad equivalente (abstención honesta) está
cubierta y probada en el módulo que entra.

### 3. Catálogo de prompts versionado (hermano: NN-042)

**Qué era:** un catálogo de plantillas de prompt con versión y hash, para poder
cambiar un prompt sin reescribir código y con trazabilidad de qué prompt usó
cada resultado.

**Por qué no entra (todavía):** la trazabilidad de qué prompt se usó **sí** es
necesaria, pero en este producto se resuelve de otro modo y con menos piezas: el
trabajo guarda en su payload el **modelo** que se usó (ver ADR-023, rutas de
modelo) y el resultado guarda la referencia al guion por *hash* (migración
`b3c1d9e4f7a2`, «invalidación de prompts por hash de guion»). Es decir: la
pregunta «¿qué prompt generó este resultado?» ya tiene respuesta trazable en
la base de datos. El catálogo completo (plantillas, editor, versionado) es
capacidad de la fase de producción, no de la beta.

**Estado:** `NO_IMPLEMENTADO` en esta ventana; la trazabilidad sí está.

### 4. Gráficos line / timeline / percentage (hermano: NN-054)

**Qué era:** generadores de gráficos de líneas, líneas de tiempo y porcentajes
a partir de los datos de una noticia.

**Por qué no entra:** está **declarado fuera de alcance** por el encargo de la
beta (no forma parte del recorrido de la noticia) y sus datos de origen (series
numéricas verificadas) no existen todavía en este producto: las afirmaciones se
guardan como texto con estado de verificación, no como series. Portar el
generador sin las series sería código muerto; portar las series sin el generador
no es una decisión de esta fase.

**Estado:** `NO_IMPLEMENTADO` (fuera de alcance declarado). Consta en «Ideas
fuera de alcance» del plan maestro.

### 5. ZIP de Flow con manifiesto SHA-256 (hermano: NN-062)

**Qué era:** un paquete ZIP del Studio con el código fuente y un manifiesto de
hashes, descargable desde la aplicación.

**Por qué no entra tal cual:** la **capacidad sí entra**, pero con la forma que
el producto necesita: el «Centro de mantenimiento» (NN-113.15) audita las
fuentes del Studio con su SHA-256 real —calculado por
`tools/generar_manifiesto_studio.py` sobre los ficheros del repositorio— y
exporta el estado del Studio con su manifiesto. Lo que **no** entra es la
distribución del código fuente de la aplicación a través de la propia
aplicación: en este producto el código está en el repositorio, y una copia
distribuida desde dentro sólo añade superficie de exposición sin beneficiario
claro. La interfaz dice explícitamente que **no** es un backup de la base de
datos (eso es `scripts/db_backup.py`).

**Estado:** capacidad **portada con adaptación**; la distribución del código
fuera del repo se **descarta**.

### 6. Aprobación CAS, clasificador de riesgo IA, *follow-ups* con protección de
ciclos (hermano: NN-033/035/036/040)

**Qué eran:** tres capacidades del motor editorial hermano: aprobación con
comparación atómica, un clasificador que distingue «anuncio» de «disponibilidad»
y un encadenamiento de tareas con protección de ciclos.

**Por qué no entran tal cual:** la aprobación con comparación atómica **sí**
existe en este producto, pero resuelta en otro sitio y con otro nombre: la
aprobación de una versión de guion es una fila de `approvals` con estado
`ACTIVE`/`SUPERSEDED` y la invalidación por *hash* de guion (migración
`b3c1d9e4f7a2`). Reimplementar el «CAS» del hermano sería duplicar una
garantía que ya está. El clasificador de riesgo y los *follow-ups* con
protección de ciclos pertenecen a la fase de producción y no tienen recorrido
en la beta.

**Estado:** `NO_IMPLEMENTADO` en esta ventana (la garantía equivalente de
aprobación sí está, con otro diseño).

## Consecuencias

- El repositorio activo **no** contiene código del hermano que no se haya
  portado con su test: no hay carpetas copiadas.
- Cada descarte tiene su motivo escrito **aquí**, no en el historial de un
  ticket cerrado.
- Si alguna vez entra una capacidad descartada, este ADR se actualiza con el
  motivo del cambio de criterio: una decisión sin registro es una decisión que
  nadie puede revisar.

## Referencias

- ADR-016 — repositorio único y base de datos única (en
  `docs/agente/REGISTRO.md`, 2026-11-01).
- `docs/agente/PLAN_MAESTRO.md` — filas NN-117.1–.8 e «Ideas fuera de alcance».
- `archive/neuralnews-20261101/` — el hermano congelado (fuente de capacidades).
