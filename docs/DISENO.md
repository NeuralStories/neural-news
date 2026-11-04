# Sistema visual — neural.news

Este documento es la referencia del sistema visual de la web. La **consola de
operación** (`/ops`) es la superficie de referencia: es donde se fixaron los
tokens, los estados semánticos y los patrones de tabla y telemetría que el
resto de vistas van a reutilizar.

Regla del proyecto: **cero dependencias**. No hay Tailwind Components, ni
shadcn/ui, ni TanStack, ni Recharts, ni librerías de iconos. Todo se sostiene
sobre Tailwind (ya presente, v4) y sobre las clases propias de
`apps/web/app/globals.css`.

---

## 1. Tokens

Viven en `apps/web/app/globals.css` y se exponen al CSS como variables
(`--c-*`) y a Tailwind como utilidades (`--color-*` en `@theme inline`).

| Token | Utilidad | Oscuro | Claro |
|---|---|---|---|
| `--c-bg` | fondo de página | `#08080a` | `#f6f6f7` |
| `--c-surface` | panel, tarjeta | `#101013` | `#ffffff` |
| `--c-surface-2` | superficie elevada (métrica, fila) | `#16161a` | `#fafafa` |
| `--c-surface-3` | esqueleto de carga | `#1e1e23` | `#eeeef1` |
| `--c-line` | borde de 1 px | `#23232a` | `#dcdce2` |
| `--c-line-strong` | borde de control activo | `#34343d` | `#c0c0c9` |
| `--c-ink` / `--c-ink-2` / `--c-ink-3` | texto / secundario / terciario | `#e8e8ec` / `#a4a4ae` / `#6d6d77` | `#16161a` / `#52525c` / `#797982` |
| `--c-ok` | activo, nominal | emerald | `#047857` |
| `--c-warn` | degradado, aviso | amber | `#b45309` |
| `--c-crit` | fallo, crítico | rose | `#be123c` |
| `--c-info` | en curso, telemetría | sky | `#0369a1` |
| `--c-idle` | inactivo, sin dato | zinc | `#71717a` |

Los acentos son **funcionales**, no decorativos: un color significa una cosa y
sólo una. El estado de un trabajo, de una dependencia y de un proveedor usan la
misma escala.

**Tipografía.** Dos pilas, sin peticiones a terceros (el build no depende de la
red):

- sans: `Inter, "IBM Plex Sans", "Segoe UI Variable Text", system-ui…`
- mono: `"JetBrains Mono", "IBM Plex Mono", ui-monospace, "Cascadia Mono"…`

Toda cifra de telemetría va en monoespaciado con **cifras tabulares**
(`.metrica-valor`, `.tabla-ops .num`): las columnas de números no bailan al
refrescarse.

**Tema.** El oscuro es el de por defecto. El claro se activa con
`data-tema="claro"` en `<html>`; el conmutador está en la cabecera (componente
`AppShell`) y persiste en `localStorage` (`neural.tema`). Un script en línea en
`layout.tsx` aplica la preferencia **antes del primer pintado**: si se pusiera
desde React, la página se pintaría en oscuro y luego saltaría a claro.

## 2. Clases propias

`tools/check_clases.py` falla si una composición de utilidades **reimplementa en
línea** un componente del sistema (por ejemplo, escribir a mano
`rounded-lg border-neutral-800 bg-neutral-900 p-4` en vez de usar `.card`).
Las clases viven todas en `globals.css`.

| Clase | Para qué |
|---|---|
| `.card` · `.card-compact` · `.card-quiet` | panel, panel compacto, caja sin relieve |
| `.panel-header` · `.modal-actions` · `.inset` | cabecera de panel, pie de modal, caja de contenido técnico |
| `.btn` · `.btn-primary` · `.btn-danger` · `.btn-sm` · `.btn-sm-primary` | botones (todos con `active:scale-[0.98]`) |
| `.input` · `.input-compact` | campos |
| `.badge` · `.badge-ok` · `.badge-warn` · `.badge-err` · `.badge-info` · `.badge-neutral` · `.badge-demo` | etiquetas |
| `.table-base` · `.table-wrap` | tabla genérica y envoltorio con scroll |
| `.ops-panel` · `.ops-panel-head` · `.ops-panel-title` · `.ops-panel-meta` · `.ops-panel-body` | rejilla operativa |
| `.estado` · `.estado-punto` · `.estado-ok`… · `.estado-punto-ok`… | estado semántico (punto + etiqueta) |
| `.metrica` · `.metrica-label` · `.metrica-valor` · `.metrica-pista` | lectura de telemetría |
| `.tabla-ops` · `.tabla-ops .num` · `.tabla-ops .id` | tabla densa con cabecera pegajosa. La tabla tiene **ancho mínimo** (`min-w-[52rem]`) y cada columna declara su `ancho` como **mínimo**: sin eso la columna larga (título, tema) se estrangula y sus textos se parten en ocho líneas. La tabla se desplaza en horizontal dentro de su envoltorio |
| `.barra` · `.barra-relleno`(`-warn`/`-crit`/`-info`) | barra de una regla (tasa, presupuesto) |
| `.kv` · `.kv-clave` · `.kv-valor` | fila clave/valor |
| `.alerta-fila` · `.alerta-fila-err` · `.alerta-fila-warn` | aviso con franja de severidad |
| `.chip` · `.filtro` · `.filtro-on` | chip y botón de filtro |
| `.esqueleto` · `.vacio` | carga y estado vacío |

## 3. Componentes (`apps/web/components/ui/`)

| Componente | Para qué |
|---|---|
| `<Estado tono etiqueta detalle variante>` | estado semántico; `variante="punto"` para celda compacta. **Memoizado** (el refresco de la consola no debe repintarlo). |
| `<Metrica etiqueta valor sufijo pista tono>` | lectura de telemetría. **Memoizada**. |
| `<Panel titulo meta acciones relleno>` | panel de la rejilla. `relleno="flush"` para tablas. |
| `<TablaOps columnas filas claveFila vacio>` | tabla densa genérica y tipada; columnas con `numerica` (alineación y cifras tabulares) y `secundaria` (ocultables). |
| `<EsqueletoMetrica>` `<EsqueletoTabla>` `<EsqueletoPanel>` `<Vacio>` | estados de carga y vacío con **la forma del contenido final** (sin *layout shift*, sin spinners). |
| `icono.tsx` | iconos SVG en línea de 16 px, trazo 1,75, `currentColor`. Sin librería de iconos. |

## 4. Estado de la migración

Todas las rutas de `apps/web/app` están migradas al sistema.

| Ruta | Qué es | Sistema aplicado |
|---|---|---|
| `/` | acceso en modo demo | `Panel`, `Vacio`, `kv`, `alerta-fila`, error con código literal y reintento |
| `/fuentes` | inventario de fuentes | alta con modos URL/texto/fichero, `TablaOps` con filtros **en la URL** (estado, proveedor, texto, página) y columnas ocultables; detalle de la fuente en columna lateral (`Metrica`, `kv`, `Estado`, transcripción) |
| `/noticias` | catálogo de noticias | banda de `Metrica`, `TablaOps` con filtros en la URL (estado, orden, texto, página) y 3 columnas ocultables; duplicados en `<details>` |
| `/noticias/[id]` | ficha de una noticia | cabecera con `Estado`, telemetría, rejilla 2:1, afirmaciones y evidencias en `TablaOps` densas, versiones de guion, prompts en `inset`, storyboard |
| `/estudio` | lanzador del Studio | alta de proyecto (`Panel`, `input`), `TablaOps` de proyectos con `Estado`, `Metrica` de resumen; el Studio (`features/studio`) hereda la base por tokens |
| `/lotes` | lotes de producción | `Metrica` de resumen, catálogo de noticias y de lotes en `TablaOps` con filtros en la URL, reordenación accesible (subir/bajar con nombre), exportación y ZIP |
| `/configuracion` | proveedores y ajustes | paneles por sección, `TablaOps` de proveedores con `Estado`, `kv` de ajustes, conmutador de tema |
| `/ops` | consola de operación | banda de estado, alertas con filtro, telemetría en `Metrica`, `TablaOps` de trabajos con filtros en la URL y columnas ocultables, columna de contexto (consumo, dependencias, proveedores) |

### Cómo se hizo sin reescribir 3 800 líneas

La escala de color heredada (`neutral-*`, `sky-*`, `emerald-*`, `rose-*`,
`amber-*`) se **redirige a los tokens** en `@theme inline`. Con eso, el Studio
y el resto de vistas heredan la base nueva (oscura y clara) sin tocar su
lógica; después, una pasada mecánica (`tools/auditoria/migrar_tokens_web.py`)
retira los patrones prohibidos que quedaban: radios largos, sombras
decorativas, gradientes de acento, `text-white` (invisible en tema claro) y los
spinners (el icono de recarga no gira: el estado va en la etiqueta).

### Skins (apariencia)

Un skin es un **intercambio de variables CSS**, no un tema alternativo con
componentes: `data-skin` sobre `<html>` y un bloque de tokens por skin en
`globals.css`. La semántica de los acentos (`ok`/`warn`/`crit`/`info`/`idle`)
es idéntica en todos; sólo cambia la familia de tono, el radio y la pila
tipográfica.

| Skin | Qué cambia |
|---|---|
| `base` (Industrial) | zinc casi negro, radios 4 px, Inter + JetBrains Mono |
| `slate` | neutros azules de sala de control, mismo ritmo que la base |
| `papel` | papiro cálido, tipografía IBM Plex |
| `fosforo` | verdor CRT, todo monoespaciado |
| `carbon` | negro puro, radios 2 px, máxima densidad de fila |
| `plex` | IBM Carbon: radios 0, acento azul, trazo cuadrado |

Cada skin define sus **dos bases** (oscura y clara). El catálogo vive en
`apps/web/lib/apariencia.ts` (`SKINS`, `aplicarSkin`, `skinGuardado`), la
persistencia es `localStorage["neural.skin"]` y el atributo lo pone un script
en línea en `layout.tsx` **antes del primer pintado** (sin destello), igual
que `data-tema`. El selector está en la cabecera y también en el panel
«Apariencia» de Configuración.

### Iconos: un solo sistema, cero peticiones

Los marcadores de estado del Studio eran **glifos tipográficos y emoji**
(✓ ✕ ⚠ ⏳ ⚓ 🍌). Ahora todos son iconos SVG del sistema
(`apps/web/components/ui/icono.tsx`): 16 px, trazo 1,75, `currentColor`.
Con ello la web **no hace ninguna petición a terceros**: la única que quedaba
(carga de Material Symbols en `layout.tsx`) era además una petición muerta y
se ha eliminado (`components/carga-fuente-iconos.tsx`).

## 5. Reglas para las vistas que vengan

1. **Cero dependencias nuevas.** Si hace falta algo (tabla virtualizada,
   gráficas), se escribe o se deja para después; no se añade una librería sin
   decidirlo.
2. **Cifras en monoespaciado y tabulares.** Etiquetas en versalitas de 10–11 px
   con tracking amplio (`.ops-panel-title`).
3. **Bordes de 1 px y radio pequeño** (`rounded-sm`/`rounded-md`). Nada de
   `rounded-3xl` en superficies de datos.
4. **Rejilla asimétrica.** Nada de tres tarjetas idénticas: panel ancho a la
   izquierda (lo que se lee) y columna de contexto a la derecha (lo que se
   consulta).
5. **Todo elemento interactivo con estado de carga, vacío y error**, y el error
   con su código literal y un reintento.
6. **El dato viejo no se tira**: si un refresco falla, se conserva la última
   lectura marcada como obsoleta.
7. **Sin spinners circulares**: el esqueleto tiene la forma del contenido.

## 6. Comprobaciones

`npm run typecheck`, `npm run lint`, `npm run build`,
`python tools/check_clases.py` y `python tools/check_a11y.py` (0 bloqueantes,
0 avisos) son obligatorios antes de dar por buena una vista. La suite completa
del repositorio (`docs/entrega/verificar.ps1`) incluye además las pruebas de
Playwright: el conmutador de tema y el ancho ampliado de `/ops` no deben
romper la navegación.

`apps/web/e2e/sistema-visual.spec.ts` recorre **todas** las rutas migradas y
comprueba, en **oscuro y claro**: que la vista responde, que no desborda
horizontalmente, que el conmutador de tema cambia el fondo de verdad (atributo
`data-tema` y color computado) y que no hay errores de consola.

### El E2E es parte del contrato de la interfaz

Al migrar una vista, sus rótulos, cabeceras de tabla y botones **no se
tienen que renombrar**: el E2E del repositorio los busca por texto. Concretamente
se conservan:

- rótulos: «Entrar en modo demo», «Añadir fuente», «Aportar texto, archivo o
  transcripción», «Registrar y analizar», «Volver a analizar», «Analizar
  vídeo», «Buscar transcripción», «Investigar», «Guardar borrador»,
  «Aprobar esta versión», «Preparar escenas», «Crear lote», «Crear y abrir el
  Studio», «Nombre», «Proporción», «Noticia del motor editorial»;
- encabezados: «Fecha real», «Verificación», «Duplicados», «Puntuación»,
  «Título», «Tipo», «Enlace», «Acciones»;
- encabezados de página: «Fuentes registradas», «Añadir fuente».

`tools/auditoria/comparar_cabeceras.py` compara las cabeceras de cada vista
migrada con las del tag y avisa de las que el E2E podría dejar de encontrar;
`tools/auditoria/alinear_cabeceras.py` las deja en su forma canónica.

### Comprobaciones propias de la migración

Además de las del repositorio:

- `node tools/auditoria/capturar_vistas.mjs` — recorre todas las rutas en
  oscuro y claro, comprueba que no desbordan y deja una captura por vista en
  `docs/entrega/evidencias/vistas/` (con `resumen.json`: fondo computado,
  desborde y errores de consola).
- `node tools/auditoria/diagnostico_red.mjs` — qué peticiones fallan por ruta.
- `python tools/auditoria/migrar_tokens_web.py` — pasada mecánica de tokens
  (radios, sombras, gradientes, `text-white`, spinners).

La propuesta visual completa, con los hallazgos auditados y lo que queda
pendiente, está en `docs/entrega/PROPUESTA_VISUAL_DASHBOARD.md`.
