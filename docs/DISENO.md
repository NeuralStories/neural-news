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
| `.tabla-ops` · `.tabla-ops .num` · `.tabla-ops .id` | tabla densa con cabecera pegajosa |
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

## 4. Reglas para las vistas que vengan

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

## 5. Comprobaciones

`npm run typecheck`, `npm run lint`, `npm run build`,
`python tools/check_clases.py` y `python tools/check_a11y.py` (0 bloqueantes,
0 avisos) son obligatorios antes de dar por buena una vista. La suite completa
del repositorio (`docs/entrega/verificar.ps1`) incluye además las pruebas de
Playwright: el conmutador de tema y el ancho ampliado de `/ops` no deben
romper la navegación.
