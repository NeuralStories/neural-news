# PROPUESTA VISUAL · Dashboard y capa de datos de `neural.news`

**Alcance:** propuesta documental de optimización de la superficie gráfica (dashboard, consola de operación, tablas y telemetría) y de la capa de datos que la alimenta.
**Regla original:** *no se ha modificado ni un byte del repositorio* — así se escribió este documento. **Actualización posterior:** el propietario autorizó continuar la implementación; lo aplicado queda registrado en la sección 6. La propuesta original (secciones 0–5) se conserva sin cambios.

---

## 6. IMPLEMENTACIÓN APLICADA (tras la autorización)

Trabajado sobre el árbol del otro agente (sin tocar sus cambios), con cero dependencias nuevas y las guardias del proyecto en verde.

### 6.1 Skins (la petición explícita: «me refería a skins»)
- `apps/web/app/globals.css`: 5 skins nuevos como **capas de tokens** (`html[data-skin=…]` + su variante `[data-tema="claro"]` cada uno): **Slate frío**, **Papel técnico** (IBM Plex), **Fósforo** (terminal mono), **Carbón** (2 px), **Plex cuadrado** (radios 0, IBM Carbon). El puente `@theme inline` propaga cada skin a todo el producto sin tocar componentes; la semántica ok/warn/crit/info/idle se conserva en todos.
- `apps/web/lib/apariencia.ts` (nuevo): catálogo, lectura y persistencia (`localStorage["neural.skin"]`, validada contra el catálogo).
- `apps/web/app/layout.tsx`: el script pre-paint aplica también `data-skin` (sin destello), con validación por lista blanca.
- Selector en dos sitios: cabecera (`select` nativo, clase nueva `.selector-skin`) y Configuración → panel «Apariencia» (chips `.filtro` con `aria-pressed` + descripción del skin activo).

### 6.2 Hallazgos aplicados
| Hallazgo | Estado | Cómo |
|---|---|---|
| F-1 marcadores tipográficos/emoji | ✅ | 21 usos en 12 ficheros del Studio (`✓ ✕ ⚠ ⏳ ⚓ 🍌`) → `IconoCheck/IconoCruce/IconoAlerta` (12–13 px) o texto plano; `ModalImportarLote` ya no adivina el tono con `startsWith('✓')`: el feedback viaja como `{tono, texto}` |
| F-2 carga muerta de Material Symbols | ✅ | `carga-fuente-iconos.tsx` eliminado; `layout.tsx` sin peticiones a terceros (0 en toda la app) |
| F-3 ancho de cabecera en `/ops` | ✅ | La cabecera comparte el `ancho` de `main` (1680 px) |
| F-4 horas sin fecha | ✅ | `hora()` en ops y configuración: hoy → `HH:MM:SS`; antes → `dd/mm HH:MM`; `title` con ISO en la columna creado |
| F-5 filtro de alerta roto | ✅ | El estado guarda el **código** de la alerta (estable entre ciclos); el chip «quitar filtro» funciona siempre |
| F-6 paginación `/v1/jobs` | ⏸ Post-beta | Requiere backend + contrato OpenAPI + pytest (fase 3 de la propuesta) |
| F-7 sondeo sin higiene | ✅ (parcial) | `AbortController` por ciclo (el nuevo aborta al anterior), pausa con `document.hidden` y lectura inmediata al volver; **lectura parcial**: cada bloque falla por su cuenta (`Promise.all` de lecturas aisladas), el panel que falla conserva su última lectura buena y la banda pasa a `lectura parcial` (tono warn) con los códigos |
| F-8 sondeo compartido de trabajos | ⏸ Post-beta | Invasivo para este tramo |

### 6.3 Densidad de `/ops`
- «Última lectura» sale de la rejilla de telemetría (era metadato, no métrica): la 8.ª celda es ahora «trabajos» (total de la ventana).
- «Reparto por tipo» ordenado descendente por recuento.
- Cabeceras ordenables en la tabla de trabajos (`#`, `estado`, `creado`): `aria-sort`, chevron `IconoOrden` (10 px, apagado cuando no manda), ciclo asc → desc → orden del servidor. Nueva clase `.orden-cabecera` en `globals.css` (guardia `check_clases` conforme).
- `TablaOps` extendida con `orden`/`alOrdenar` opcionales y `Columna.ordenable` — el criterio lo aplica la página, la pieza sigue sin saber ordenar datos.

### 6.4 Verificación (todas con veredicto y salida 0)
`check_clases.py` OK · `check_a11y.py` 0 bloqueantes · `scan_secrets.py` 0 hallazgos · `tsc --noEmit` 0 errores · `eslint .` 0 problemas · `npm run build` (NEURAL_ENV=local) compila 11/11 · generadores `--check` al día (el manifiesto del Studio se **regeneró** tras editar sus ficheros) · Playwright: tanda completa final tras los arreglos de 6.6 (ver resultado en la conversación; los 3 specs fallidos se validaron individualmente en verde antes del cierre).

### 6.6 E2E: qué falló y por qué (15 tests tras la ampliación del otro agente, navegador `edge`)
1. **studio-reintegration** — roto por MI cambio de texto: el spec buscaba `Guardado ✓`; el marcador tipográfico ya no existe. Corregido el spec (`/Guardado/`, intención intacta) en `studio-reintegration.spec.ts`, `beta-journey.spec.ts` y `vertical-production.spec.ts`. ✅ Reejecutado: pasa.
2. **beta-journey** — roto por la migración **en curso del otro agente**: el flujo de transcripción se dividió en «Transcribir» (pide, feedback `Transcribiendo…`) y «Buscar transcripción» (solo lee), dentro del panel de detalle al que se llega con «Ver el detalle» de la fila. Spec adaptado a ese flujo con su nuevo texto. ✅ Reejecutado: pasa (15 s).
3. **critical-flow** — roto por la misma migración: la métrica nueva «afirmaciones» del resumen hace que `locator("section").filter({hasText}).first()` resuelva al panel equivocado (75 resoluciones al resumen). Spec adaptado: el panel se delimita por su **cabecera** (`getByRole("heading", { name: "Afirmaciones" })`); la expectativa `/Sin verificar|Confirmada/` se queda intacta (las etiquetas siguen existiendo en `estados.generado.ts`). ✅ Reejecutado: pasa.

### 6.5 Archivos tocados
`globals.css` · `layout.tsx` · `lib/apariencia.ts` (nuevo) · `lib/api.ts` (señal de aborto en las 5 lecturas) · `components/app-shell.tsx` · `components/ui/{icono,tabla}.tsx` · `app/ops/page.tsx` · `app/configuracion/page.tsx` · `features/studio/{App,BackgroundTab,MovementTab,ReferencesTab,ResultTab,ScriptTab,TopNavigation,CharacterSheetTab,ProductionVertical,BackupModal}.tsx` · `features/studio/components/news/{ModalImportarLote,ModalNoticiaIndividual,ModalNuevoBloque,ListaNoticias}.tsx` · `data/manifiestoStudio.generado.json` (regenerado) · eliminado `components/carga-fuente-iconos.tsx`.



---

## 0. Veredicto sobre la base existente

La implementación en curso (rama `release/1.0.0-beta.1`, HEAD `4191d16`, ~20 ficheros en el árbol de trabajo) **ya cumple la mayor parte del protocolo «Operational Identity»**. Auditado contra las 8 reglas del prompt:

| Regla del prompt | Estado | Evidencia |
|---|---|---|
| Base neutra monotona + acentos semánticos estrictos (ok/warn/crit/info) | ✅ Cumplida | `globals.css` §tokens: `--c-ok/warn/crit/info/idle`, tema oscuro por defecto + claro vía `data-tema`, puente `@theme inline` |
| Tipografía: sans neutra + mono estricto con cifras tabulares | ✅ Cumplida | Pilas `Inter/IBM Plex Sans` y `JetBrains Mono/IBM Plex Mono`; `tabular-nums` en `metrica-valor`, `tabla-ops .num`, `kv-valor` |
| Iconos SVG (nada de emojis como marcador) | ⚠️ **Parcial** | `components/ui/icono.tsx` correcto (SVG 16 px, trazo 1,75, `currentColor`), pero quedan **9 usos de `✓ ✕ ⚠ 🍌`** como marcador de estado en el Studio (detalle en F-1) |
| Rejillas asimétricas, densidad antes que decoración | ✅ Cumplida | `/ops` usa `xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]`; tarjetas prohibidas ausentes |
| Bordes 1px, radios `rounded-sm–md` máx. | ✅ Cumplida | 0 apariciones de `rounded-xl/2xl/3xl` en `app/`, `components/`, `features/` |
| Microinteracción táctil (`active:scale-[0.98]`, cero layout-shift) | ✅ Cumplida | `.btn`, `.btn-sm*`, `.filtro` llevan `active:scale-[0.98]` + `focus-visible:ring`; esqueletos con la forma del contenido |
| Estados Loading/Empty/Error obligatorios | ✅ Cumplida | `estados.tsx` (`EsqueletoMetrica/Panel/Tabla`, `Vacio`), `/ops` con error + reintento + código en crudo; patrón `codigoDeError()` en la portada |
| Virtualización >100 filas; hojas memoizadas | ⚠️ **Parcial** | `Metrica`, `Estado`, `FilaOps` memoizados; pero `TablaOps` no ordena ni virtualiza y el backend limita a 50–200 filas (detalle en F-4/F-5) |

**Conclusión:** no hay que rehacer nada; hay que **cerrar 8 hallazgos concretos** (F-1…F-8) y decidir 2 opciones de arquitectura de datos (O-A/O-B). Estimación total: 1,5–2 días de trabajo del agente, manteniendo verdes las 14 comprobaciones.

---

## 1. Hallazgos (con fichero y línea)

### F-1 · Marcadores de estado con caracteres tipográficos/emoji — violación directa del prompt
- `features/studio/components/CharacterSheetTab.tsx:158` → `🍌 Nano Banana Pro` (emoji como etiqueta de proveedor).
- `features/studio/components/BackupModal.tsx:105,139,230` → `✓ Paquete descargado`, `✕`, `Íntegro ✓`.
- `features/studio/components/news/ModalImportarLote.tsx:84,126,136` → `✓ Importadas con éxito…`, `✕`, `feedback.startsWith('✓')`.
- `features/studio/components/ScriptTab.tsx:103,105` → `⚠ Verificando integridad`, `✓ 100% Integridad Textual`.
- `features/studio/components/ProductionVertical.tsx:289` → `⚠ Revisar: el guion cambió`.

**Propuesta:** sustituir por `IconoCheck` / `IconoCruce` / `IconoAlerta` de `components/ui/icono.tsx` (mismo trazo 1,75, 16 px, alineados en línea con la etiqueta). **Ojo:** `ModalImportarLote.tsx:136` decide el tono con `feedback.startsWith('✓')` — al sustituir el texto hay que cambiar el criterio (p. ej. que `setStatusMessage` reciba `{ tono, texto }` en vez de adivinarlo del prefijo). El badge de «Nano Banana Pro» pasa a `badge-neutral` con el nombre en texto, sin glifo.
**Cobertura:** `tools/check_a11y.py` no mira esto hoy; propuesta de regla nueva (extensión de `check_clases.py` o del a11y) que falle si aparece un carácter de `[\u2190-\u21FF\u2300-\u27BF\uFE0F\u1F300-\u1FAFF]` en JSX de estado.

### F-2 · Petición a terceros muerta en `layout.tsx` (única dependencia externa del sistema visual)
`app/layout.tsx:41` carga `Material Symbols Outlined` desde Google Fonts (vía `CargaFuenteIconos`, `media="print"` no bloqueante). **No existe ni un uso** de esas clases en `app/`, `components/` ni `features/` (búsqueda de `symbols-outlined|Material` → 0 resultados). La migración a los SVG en línea dejó la carga huérfana.
**Propuesta:** eliminar el `<CargaFuenteIconos …/>`, el componente de carga de iconos y su comentario. Beneficio: 0 peticiones fuera de origen en toda la app (el build ya no dependía de la red; ahora tampoco el runtime), y desaparece el único punto donde un proveedor tercero podía retrasar la pintura de iconos.
**Riesgo:** cero. Verificación: build + Playwright + `grep -r "symbols-outlined"` → 0.

### F-3 · Incoherencia de ancho entre cabecera y consola en `/ops`
`components/app-shell.tsx:75` define `ancho = "max-w-[1680px]"` para `/ops` y lo aplica a `main` y `footer`, pero la `div` interna de la cabecera (línea 80) está clavada a `max-w-6xl`: con la ventana abierta, los controles de la cabecera (tema, salir, marca) no alinean con los bordes de la rejilla de operación, que sí ocupan 1680 px.
**Propuesta:** elevar `ancho` a la cabecera (`<div className={`mx-auto flex ${ancho} …`}`). Rejilla continua de borde a borde.

### F-4 · Marca de tiempo sin fecha en la consola de operación
`app/ops/page.tsx:73` (`hora()`) y `app/configuracion/page.tsx:67` formatean con `toLocaleTimeString` **solo la hora**. En una consola que mira trabajos de días anteriores, `18:04:11` es ambiguo: no distingue «hace 5 s» de «ayer». Un monitor de operaciones necesita temporalidad sin ambigüedad.
**Propuesta** (dos niveles, igual que un panel industrial):
1. Valor visible en `font-mono tabular-nums`: `dd HH:MM` si es de hoy, `dd/mm HH:MM` si no (la hora sola queda para la fila de estado, que ya va acompañada de `lectura HH:MM:SS`).
2. `title` con ISO completo (ya existe el patrón `title=` en la columna detalle).

### F-5 · El filtro de alerta se rompe con el autorefresco (bug de UX real)
`app/ops/page.tsx:394-399`: el chip «quitar filtro» compara por **identidad de objeto** (`actual === alerta.trabajos`). Cada ciclo de 15 s trae arrays nuevos, así que tras el primer refresco la comparación deja de cuadrar: el filtro sigue aplicado pero el chip vuelve a decir «ver N trabajos» y el operador ya no puede quitarlo de forma fiable (y si lo pulsa de nuevo, re-aplica).
**Propuesta:** guardar el **código de la alerta** (`alerta.codigo`) en el estado, no la referencia del array; derivar `trabajosDeAlerta` con `useMemo` desde `alertas`. El botón pasa a ser un toggle estable (`filtro-on` ⇄ neutro) entre refrescos.
**Cobertura:** añadir aserción al E2E de `/ops` (activar filtro → esperar 2 ciclos → el chip sigue siendo «quitar filtro»).

### F-6 · Contador «N de M» miente: el backend recorta la lista
`api.listJobs()` (web, `lib/api.ts`) no pasa parámetros; el backend `apps/api/src/neuralnews/api/ops.py:44` responde **`limit` por defecto 50, capado a 200, sin `offset`, sin filtros, sin total**. Resultado en `/ops`: la cabecera «Trabajos» muestra `X de 50` aunque existan 500 trabajos, y los chips de filtro y las métricas de la tabla solo cuentan sobre esa ventana. Además los filtros estado/tipo se aplican en cliente sobre una lista truncada: un trabajo fallido nº 51 es **invisible para el operador**, que es justo el caso de uso de la vista.
**Propuesta (backend, compatible hacia atrás):**
```
GET /api/v1/jobs?limit=50&offset=0&status=FAILED&type=export_batch&order=created_at:desc
→ { items: [...], total: 437, limit: 50, offset: 0 }
```
- Índice necesario: `(created_at DESC)` ya existe por el `order_by`; el filtro por `status` puede servirse sin índice en la beta (la tabla es pequeña) y se anota como trabajo futuro.
- La web pasa filtros al servidor (los chips de `/ops` ya viven en la URL: solo cambia la llamada) y muestra `X de {total}` real con paginación por «cargar más» o cursor.
- `exportar_openapi.py --check` exigirá regenerar el contrato (está en su ciclo de comprobaciones, no es un salto).
**Cobertura:** pytest de parametrizada (status/tipo/offset/total) + el caso límite de `limit > 200`.

### F-7 · Sondeo sin higiene: 5 peticiones/15 s aunque la pestaña esté oculta y sin cancelación
`app/ops/page.tsx:132-164`: `Promise.all` de 5 endpoints cada 15 s (`setInterval`), sin `AbortController`, sin pausa cuando `document.hidden`, y un fallo de **cualquiera** de los 5 tira la lectura entera (aunque 4 respondan). Es el patrón correcto en la idea (el dato viejo no se tira), pero sobrecarga y fragiliza.
**Propuesta mínima (0 dependencias):**
- `AbortController` por ciclo: el refresco nuevo cancela el anterior en vuelo (evita respuestas desordenadas al pulsar «actualizar» durante una lectura lenta).
- Pausa en `visibilitychange` (oculto → parar el intervalo; visible → leer inmediatamente y reprogramar). El operador no está mirando: no se sondea.
- Fallos **por bloque**: la salud puede fallar y que la tabla y las métricas sigan leyéndose. Envolver cada llamada en un helper `capturar(promesa)` que devuelva `{ok, dato} | {err}`, y pintar por panel un estado de error parcial (franja warn con el código), manteniendo el principio «el dato viejo no se tira».
**Propuesta con dependencia (opción O-A, ver §3):** TanStack Query centraliza esto (`refetchInterval`, `refetchIntervalInBackground: false`, `placeholderData: keepPreviousData`, invalidaciones). Solo si se acepta añadir ~13 kB gzip.

### F-8 · Doble sondeo de trabajos por página
`lib/hooks.ts` (`useJobPolling`) sondea `GET /v1/jobs/{id}` cada 800 ms **por componente**; el editor de noticias y `/fuentes` pueden tener 2–3 trabajos en vuelo → 3 hilos de sondeo independientes que además no ven la consola `/ops` (que sondea la lista entera cada 15 s).
**Propuesta:** un único temporizador compartido (módulo o `useSyncExternalStore`): una cola de ids interesados, un `getJob` por ciclo por id (800 ms se mantiene), y `Metrica/Estado` memoizados consumen el mismo flujo. Sin tocar la API. Es la versión ligera de «aislar los contadores de alta frecuencia en hojas memoizadas» que pide el prompt.

---

## 2. Propuesta visual (superficie gráfica)

### 2.1 `/ops` — refinamientos sobre la rejilla actual (sin rediseño)

La estructura asimétrica `2fr/1fr` es correcta; se proponen 5 ajustes de densidad:

```
┌ OPERACIÓN ──────────── ● nominal ── v1.0.0-beta.1 · local ── [auto 15 s] [actualizar] ┐
├ ALERTAS (solo si hay) ─ franja roja/ámbar por severidad, acción «ver N trabajos» ─────┤
├──────────────────────────────┬────────────────────────────┤
│ TELEMETRÍA · ventana 24 h    │ CONSUMO DE HOY             │
│  8 métricas en rejilla 4×2   │  3 métricas + barra 2px    │
│  ─ reparto por tipo (desc)   │  ─ por proveedor (kv)      │
│  ─ fallos por motivo (kv)    │ DEPENDENCIAS (kv + punto)  │
│ TRABAJOS · 37 de 437         │ PROVEEDORES (kv + punto)   │
│  [filtro estado][tipo][cols] │ COLA (resumen)             │
│  tabla densa, ordenable,     │                            │
│  paginación servidor, sticky │                            │
└──────────────────────────────┴────────────────────────────┘
```

1. **«Última lectura» deja de ser la 8.ª métrica** (`ops/page.tsx:461-465`): la temporalidad de la lectura es metadato del panel, no telemetría. Se muda a la cabecera de la banda de estado (ya hay un hueco: `lectura HH:MM:SS`), y la 8.ª celda pasa a ser `tasa de reintento` o se deja a 7 métricas con la rejilla `sm:grid-cols-4` sin hueco forzado.
2. **«Reparto por tipo» ordenado por recuento descendente** (hoy sale en orden de inserción del objeto) y con barra de regla (`.barra` reutilizada, 2 px) en vez de solo chips cuando hay >6 tipos: más denso y comparable de un vistazo.
3. **Cabecera de tabla ordenable**: clic en `th` ordena en cliente (campos `id`, `estado`, `creado`) con indicador `▲/▼` hecho con SVG de 8 px (no caracteres), `aria-sort` incluido. Es lo que exige la regla de tablas del prompt; TanStack Table **no hace falta** para 1 tabla con 6 columnas: una función `ordenar(filas, clave, dir)` de 10 líneas tipada y probada basta y mantiene el «cero dependencias».
4. **Fila seleccionada**: al filtrar desde una alerta, las filas objetivo llevan `bg-info/5` durante esa interacción — el ojo encuentra la relación alerta→trabajo sin leer ids.
5. **Estados de error parcial por panel** (consecuencia de F-7): cada panel de la columna de contexto lleva su micro-estado `● error lectura` con el código HTTP en mono; la banda global solo pasa a `degradado` si lo que falla es salud o métricas.

### 2.2 Tabla densa como patrón reutilizable (no solo en `/ops`)

`TablaOps` ya es genérica; se formaliza como el único patrón de tabla del producto (fuente, noticias, lotes ya migran hacia ella):

- **Alturas de fila fijas** (`py-1`, sin `leading` variable) para que el refresco de 15 s no baile: ya está así; se documenta como restricción en el comentario del componente.
- **Columna anclada a la izquierda en scroll horizontal** (`sticky left-0 bg-surface`) para móvil: la E2E de 390 px ya existe, esto la refuerza.
- **Virtualización**: puerta de decisión explícita — `if (filas.length > 100)` render con `@tanstack/react-virtual` (~3 kB). Hoy el backend trunca a 50–200, así que la virtualización es **fase 4**, activada solo cuando F-6 deje traer listas largas.
- **Cifras alineadas por la coma decimal**: `font-variant-numeric: tabular-nums` ya está; añadir `text-align: right` en `.num` (hoy lo pone la prop `numerica` del `th`/`td`, coherente).

### 2.3 Iconos: un solo sistema, 0 peticiones

- Los 15 glifos de `icono.tsx` se quedan (geometría Lucide, trazo 1,75, 16/20 px).
- Se eliminan los restos de Material Symbols (F-2) y los caracteres `✓ ✕ ⚠ 🍌` (F-1).
- Glifos a añadir (mismas convenciones): `IconoDescargar` (paquetes/backup), `IconoDuplicado` (dedupe de importación), `IconoIntegridad` (escudo-check, para la discrepancia léxica de ScriptTab), `IconoRelojPausa` (autorefresco en pausa).
- Regla de uso: 16 px en línea con etiqueta `text-xs`; 20 px solo en estados vacíos y cabeceras de panel.

### 2.4 Tipografía: ya correcta; una decisión pendiente

Las pilas de fuentes caen a las del sistema si Inter/JetBrains Mono no están instaladas (decisión razonable: el build no depende de la red). **En una máquina Windows limpia el mono real será Consolas**, que no tiene la misma x-height que JetBrains Mono: los bloques de telemetría medirán distinto según la máquina.
**Propuesta (opcional, fase 4):** autoalojar 2 woff2 estáticos con `next/font/local` — `Inter 400/600` + `JetBrains Mono 400/700` en subsets `latin` ≈ **60–90 kB total** (nada que ver con los 4 MB de la variable que se descartó). Va en el repo, sin petición de red ni en build ni en runtime, y elimina la variabilidad entre máquinas del operador. Si se declara fuera de alcance, añadir a `globals.css` un comentario de que la pila de fallback es **contrato** (los tamaños dependen de ella).

### 2.5 Tema claro

Los acentos ya se recalculan por tema (`#047857` etc.). Propuesta de blindaje: extender `tools/check_a11y.py` con una verificación de contraste de los 5 pares `(tono · fondo de superficie)` en las dos bases (los tokens están en un solo sitio, es una tabla estática). Así el tema claro deja de ser «lo que se ve bien» y pasa a estar garantizado por el mismo ciclo que ya corre en cada entrega.

---

## 3. Propuesta de capa de datos (dashboard ↔ backend)

Dos opciones, mutuamente excluyentes. La A mantiene el «cero dependencias» que el otro agente defiende con `check_clases.py`; la B compra infraestructura a cambio de ~26 kB gzip.

| | **O-A · Sin dependencias (recomendada para la beta)** | **O-B · Con librerías (post-beta)** |
|---|---|---|
| Estado servidor | Fetch propio + `AbortController` + higiene de F-7/F-8 | TanStack Query (`refetchInterval`, caché por `queryKey`, `keepPreviousData`) |
| Tipado de payloads | **Generación de tipos desde `openapi.json`** (ya existe el exportador): un generador (generar_tipos_web.py) que emita lib/api.tipos.generado.ts; cero Zod a mano y el contrato deja de poder desincronizarse — es la versión del proyecto de «Zod para payloads entrantes» | Ídem + Zod solo en bordes externos (webhooks/imports) |
| Estado de filtros | URL `searchParams` nativa (ya implementada) — se mantiene | Ídem (nuqs innecesario aquí) |
| Tablas | `TablaOps` + orden en cliente + paginación servidor de F-6 | TanStack Table v8 si aparecen tablas con >6 columnas y visibilidad compleja |
| Coste | 0 kB, ~1 día | ~26 kB gzip, ~2 días, migración de 6 vistas |

**Recomendación:** O-A ahora; O-B se reevalúa cuando exista una segunda consola (p. ej. la cola del worker en vivo). Los dos únicos cambios de backend inmediatos son **F-6** (paginación/filtros/total en `/v1/jobs`) y, opcionalmente, un **endpoint agregado**:

```
GET /api/v1/ops/resumen  →  { salud, metricas, alertas, uso, proveedores, trabajos[] }
```
una sola transacción de lectura + una única comprobación de sesión; el cliente de `/ops` pasa de 5 peticiones a 1 por ciclo (los endpoints individuales se conservan: la OpenAPI es contrato versionado). Con `ETag` derivado del `max(created_at)` de trabajos + ventana de métricas, los ciclos sin cambios devuelven `304` y el panel apenas mueve bytes. Marcar como « Ideas post-beta» si se prefiere no tocar la API en la beta.

---

## 4. Plan de fases (para ejecutar cuando se autorice)

Cada fase termina con la suite de 14 comprobaciones en verde + evidencia en `docs/entrega/evidencias/`, respetando el ciclo del agente (EN CURSO → verificar → COMPLETADA).

**Fase 1 — Limpieza visual (0 deps, ~2 h)**
1. F-2: eliminar `CargaFuenteIconos` y su uso en `layout.tsx`.
2. F-1: sustituir `✓/✕/⚠/🍌` por iconos del sistema (incluido el criterio de tono de `ModalImportarLote`).
3. F-3: alinear el ancho de la cabecera con `main` en `/ops`.
4. F-4: marcas de tiempo con fecha (`hora()` de ops y configuración).
5. F-5: filtro de alerta por código (toggle estable) + aserción E2E.
6. F-8 (§2): sondeo compartido de trabajos.
*Instalación necesaria: ninguna.*

**Fase 2 — Densidad de `/ops` (0 deps, ~3 h)**
1. Ordenación en cliente de `TablaOps` (con `aria-sort`) + fila objetivo resaltada.
2. «Última lectura» fuera de la rejilla de telemetría; reparto por tipo ordenado desc.
3. Error parcial por panel (helper `capturar`) + higiene de sondeo de F-7 (abort + visibilidad).
*Instalación necesaria: ninguna.*

**Fase 3 — Backend del dashboard (~4 h, con pytest)**
1. F-6: `/v1/jobs` con `offset/status/type/total/order` + pruebas + regeneración del contrato OpenAPI.
2. Web: filtros server-side en `/ops`, contador real `N de {total}`.
*Instalación necesaria: ninguna (todo es código del repo).*

**Fase 4 — Decisiones que sí requieren instalar (solo con autorización)**
| Paquete | Tamaño aprox. | Para qué | Comando |
|---|---|---|---|
| `@tanstack/react-virtual` | ~3 kB gzip | Virtualización de `TablaOps` >100 filas | `npm i @tanstack/react-virtual` (en `apps/web`) |
| `next/font/local` + 4 woff2 (Inter, JetBrains Mono) | 60–90 kB en repo | Tipografía idéntica en cualquier máquina | no npm: ficheros en `apps/web/app/fonts/` |
| `@tanstack/react-query` (opción O-B) | ~13 kB gzip | Caché/invalidaciones centralizadas | `npm i @tanstack/react-query` |
| Zod (solo si se elige O-B) | ~14 kB gzip | Validación en bordes externos | `npm i zod` |

*Recomendación explícita: en la beta solo la fase 1–3; la 4 va a «Ideas post-beta» salvo el `react-virtual`, que se activa en el momento en que F-6 haga real la lista larga.*

**Guardarrails respetados por esta propuesta:** `check_clases.py` (toda clase nueva vive en `globals.css` §sistema), `check_a11y.py` (se extiende, no se rodea), `exportar_openapi.py --check` (regeneración declarada en fase 3), sin `rounded-3xl`, sin spinners, sin terceros, versionado de contrato intacto, y sin tocar estados antiguos del plan sin evidencia.

---

## 5. Lo que NO se propone (y por qué)

- **Rediseño de marca/logo/portada:** la portada ya usa el sistema y el prompt no pide identidad comercial.
- **Tremor/Recharts:** con las métricas actuales (contadores, tasas, barras de regla de 2 px) una librería de gráficos es peso muerto; si aparece una serie temporal real (histórico de cola por hora), primero el endpoint y luego se decide, con los mismos criterios (ejes mínimos, tooltip sobrio).
- **SSE/WebSocket para telemetría:** el ciclo de 15 s con 304 es suficiente para una consola local; introducir un canal push es otro proceso del servidor para algo que el operador mira por rafagas. A «post-beta».
- **Dark/light como tema de marca:** ya existe y es correcto; no se toca.

---

*Documento redactado tras revisar: `globals.css`, `layout.tsx`, `app-shell.tsx`, `components/ui/*`, `lib/{api,http,hooks,types}.ts`, `app/{page,loading,error,ops}/*`, `app/{fuentes,lotes,noticias,configuracion,estudio}/page.tsx`, `features/studio/**` (muestreo), `apps/api/src/neuralnews/api/ops.py`. Ningún fichero del repositorio fue editado; ninguna dependencia fue instalada.*

---

## 7. PLAY DE COHERENCIA VISUAL (verificado en navegador, 8 rutas × escritorio/móvil)

Recorrido real con la pila en producción local: medidas de desborde (`scrollWidth`, contenedores con `overflow-x` activo) y captura por vista, en 1440×900 y 390×844, tema oscuro base + muestreo de claro y dos skins.

**Resultado de la matriz:** 0 desbordes horizontales de página en las 8 rutas en los dos tamaños; los desplazamientos horizontales quedan confinados a los envoltorios de tabla (regla del ancho mínimo), que es el comportamiento previsto.

**Incoherencias encontradas y corregidas en este mismo pase:**

| # | Hallazgo (evidencia) | Corrección |
|---|---|---|
| P-1 | Columnas **aplastadas a una letra por línea** cuando la tabla no quepa: la columna sin `ancho` declarado es la elidida (p. ej. `notas` en la ficha de noticia). El `min-w` de la tabla evita el estrangulamiento del título, pero cualquier columna secundaria sin mínimo sigue siendo víctima. | `ancho: "12rem"` en `notas` (ficha); regla documentada: **toda columna no flexible declara su mínimo**. |
| P-2 | Cabecera del panel de /fuentes incoherente: 7 controles en `acciones` partían la cabecera en 3 filas y aplastaban el título (en móvil, la etiqueta quedaba a ~55 px). | Los 3 filtros se mudan a una **fila propia** bajo la cabecera (envuelve en pantallas estrechas); en `acciones` quedan solo los 4 chips de columna. Anchos de filtro en `style` porque `@apply w-full` de `.input-compact` (regla sin capa) vence a las utilidades `w-*` de Tailwind v4. |
| P-3 | Barra de desplazamiento gruesa de Chromium (16 px con flechas) dentro de los paneles: tapaba la última columna y desdecía del trazo de 1 px. | Nueva clase `.tabla-contenedor` en `globals.css` (scrollbar de 8 px, pulgar `--c-line-strong`, `scrollbar-width: thin`) aplicada en el envoltorio de `TablaOps`. |
| P-4 | Concordancia de textos: «1 posibles · #9» (duplicados), «1 afirmaciones» / «0 evidencias» (ficha). | Pluralización correcta («1 posible», «1 afirmación»). |

**Verificación tras corregir:** `check_clases.py` OK · `check_a11y.py` 0 bloqueantes · `tsc --noEmit` 0 · `eslint .` 0 · `npm run build` compila 11/11 · `npx playwright test` **15 passed (2,7 min)** · re-inspección visual de /fuentes y de la ficha confirmando cabecera limpia, filtros en fila y notas legibles.

**Restante consciente:** la tabla de lotes existentes desplaza en horizontal dentro de la columna lateral (consecuencia aceptada de la regla del ancho mínimo; las columnas ya declaran sus mínimos), y F-6/F-8 siguen post-beta.
