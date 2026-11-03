# P1 — Inventario del código recuperado de Flow

[VERIFICADO: `flow-recovery/reports/manifest.json`, SHA-256 de los archivos locales] Hay **17 archivos TS/TSX**, todos presentes; tamaño y hash local coinciden con el manifiesto. `manifest.json` informa segunda lectura del visor y 0 imports relativos faltantes. Esto acredita la copia local, no la procedencia oficial ni la integridad de una aplicación original de Google Flow.

[VERIFICADO: `python` con `zipfile.testzip()` y SHA-256] El ZIP tiene 17 entradas, CRC válido, hash del ZIP igual al manifiesto y 0 discrepancias de tamaño/hash en los 17 archivos de disco.

## Archivos (ruta relativa a `flow-recovery/source/`)

| Archivo / tipo | Bytes | SHA-256 | Finalidad e imports comprobables |
|---|---:|---|---|
| `types.ts` TS | 5417 | `0b056841ce6032d0e61edc97f79b4acb704605b9271517804c27482201207168` | Tipos de noticia, referencias, escenas y paquete Studio; sin imports (`types.ts:139-188`). |
| `constants.ts` TS | 18345 | `4beff456d88eb795dfd25ee22bb76e9c9f0c1b1ad932d243aceb45d26158e07e` | Presets de personaje, fondo, voz y datos de ejemplo; importa `./types` (`constants.ts:1,12,35,59,111,174,213`). |
| `utils/scriptAnalyzer.ts` TS | 8556 | `eaed27ace4a1122c54127b307526deb99969aaf758f93c09cf026d786ebad4fd` | Análisis de duración y división en escenas; importa `../types` (`scriptAnalyzer.ts:1,14,67`). Funciones puras recuperables. |
| `components/TopNavigation.tsx` TSX | 5493 | `14bef9fdf6076a065e1bb7c95adf4baa41ef2ddd7dde56615e9daf857110074b` | Navegación de pestañas; importa `react`, `../types` (`TopNavigation.tsx:1-25`). |
| `components/CharacterSheetTab.tsx` TSX | 10447 | `9983605b590fbea46c2850df8e4b7f92b3d504f7850bc73b2c4a328682808702` | UI de hoja de personaje; importa `react`, `flow-sdk`, `../types`, `../constants` (`CharacterSheetTab.tsx:1-14`). |
| `components/BackgroundTab.tsx` TSX | 6536 | `2ef38256286a22a054a10147d1e2a73c850c2e4b5589f9bbae6fdf6d48b57940` | UI de fondo/plato; importa `react`, `../types`, `../constants` (`BackgroundTab.tsx:1-14`). |
| `components/ScriptTab.tsx` TSX | 11075 | `c71aec22fc3991533c86afaa08878ef5fe7f130820f9ff73718e067b5d1acde7` | UI para guion y escenas editables; importa `react`, `../types` (`ScriptTab.tsx:1-13,34-39`). |
| `components/VoiceTab.tsx` TSX | 4901 | `7ea7008160015b0a459f02a18bc2a9e456a20f3dfbeff24055a11c0fea97217c` | UI de perfil y velocidad de voz; importa `react`, `../types` (`VoiceTab.tsx:1-9`). No se encontró motor de voz en estos archivos. |
| `components/MovementTab.tsx` TSX | 2913 | `1c45716fe8461692a5fed25f4efc746b8324740359706250b09b675ce635471c` | UI de movimientos de cámara; importa `react`, `../types` (`MovementTab.tsx:1-9`). |
| `components/ResultTab.tsx` TSX | 14791 | `6aac2e67bd90092e2f785d1dd5a23d69367d5712a60e5a7adca71dc736a91fd1` | Presentación de plan y resultado de vídeo entregado por el padre; importa `react`, `../types` (`ResultTab.tsx:1-31,124`). |
| `components/HelpModal.tsx` TSX | 4114 | `904e7b3763a2470cedd00665df35e8ddab1e681e73d22d344834fcd58d9086d5` | Ayuda UI; importa `react` (`HelpModal.tsx:1-8`). |
| `App.tsx` TSX | 50640 | `cb8c1b7ad562c4626873c5132441373dfae3f435099463ea0a2abb067c90f6f7` | Orquestador React: estado de artículos, importación/exportación y llamadas Flow; importa `react`, `flow-sdk` y módulos internos (`App.tsx:1-40,123,395-469,498-529`). Contiene además cadenas de código embebidas para descarga de backup (`App.tsx:549-702`); no son módulos adicionales. |
| `components/ReferencesTab.tsx` TSX | 24039 | `8754060e417a19aebcf51eee4ded1485511c311d988cbec63588af0f60b82cc0` | UI de referencias visuales/editoriales e importación de JSON; importa `react`, `flow-sdk`, `../types` (`ReferencesTab.tsx:1-26,71-73,170-177`). |
| `components/NewsEditorialTab.tsx` TSX | 39006 | `bd4baec902ea84f79cb51f8d61173a61b84da9584549dea0ca1c84481926d969` | UI de noticias e importación de lote JSON; importa `react`, `../types`, `../constants`, `../utils/newsDeduplication` (`NewsEditorialTab.tsx:1-28,146-209`). |
| `utils/newsDeduplication.ts` TS | 5139 | `438c2ddd37bed68e173e9f5959499138abbb557da0e55dacf57a7a17de1ddeea` | Detección local de artículos repetidos; importa `../types` (`newsDeduplication.ts:1,65`). Función pura recuperable. |
| `data/sourceManifest.ts` TS | 3280 | `18cac4f2e07e278369c3d8637ece73beecf8c40f5baa728571bfaad2a1977e13` | Metadatos/hash del backup descargable y `computeSha256`; sin imports (`sourceManifest.ts:1,7,77`). |
| `components/BackupModal.tsx` TSX | 12427 | `9300e91d1222337dae93ecb72f7eb6beb5a2400d871c499dc4b238c693c17fd1` | Comprueba contenido embebido y descarga JSON usando Flow; importa `react`, `flow-sdk`, `../data/sourceManifest` (`BackupModal.tsx:1-3,44,82-117`). |

## Dependencias, recursos y límites

- [VERIFICADO: imports en `manifest.json`, `App.tsx:1-38`] Los imports relativos resuelven dentro de los 17 archivos. Externos: `react` y `flow-sdk`. `flow-recovery/package.json:5-15` es **del extractor**, contiene `playwright-core` y `typescript`; no declara React ni `flow-sdk`. `flow-recovery/node_modules/flow-sdk` no existe.
- [VERIFICADO: búsqueda de archivos en `flow-recovery/source/`] No hay `package.json`, lockfile propio, `index.html`, `tsconfig.json`, configuración de Vite/Next, CSS, imágenes, audio ni vídeo. `flow-recovery/reports/manifest.json` marca `compileTested: false`. **Conclusión:** no hay base para declarar la app autónoma o ejecutable; no se ejecutó build.
- [VERIFICADO: `App.tsx:277,320,363,424,529`; `ReferencesTab.tsx:71-73`; `BackupModal.tsx:117`] La selección/generación de imágenes, la descarga y la generación de vídeo usan métodos de `Flow`. Contrato, runtime, región, precios y licencia de `flow-sdk` no están presentes: [BLOQUEADO] compilación/ejecución independiente hasta conseguir documentación o un adaptador definido.
- [VERIFICADO: `constants.ts:111-174,213-368`] Las referencias visuales iniciales apuntan a URLs externas de Unsplash y los artículos/fuentes de ejemplo están codificados en TS. No son archivos locales ni prueban la identidad, la autorización de uso o la verdad factual del presentador. [BLOQUEADO] derechos/licencias y activos definitivos; responsable propuesto: producción.
- [VERIFICADO: búsqueda de `LICENSE`, `COPYING` y metadatos de licencia en `flow-recovery/source/`] No se encontró licencia de los 17 archivos ni de los recursos citados. [BLOQUEADO] validar procedencia y derechos antes de publicar o reutilizar assets; responsable propuesto: propietario del proyecto.
- [VERIFICADO: `NewsEditorialTab.tsx:146-181`, `App.tsx:440-469`] Existen dos importadores: lote JSON (`articles`/`noticias` o array) y configuración Studio. Ninguno consume directamente el ZIP editorial ni verifica criptográficamente aprobación/hash. `approvalStatus` puede venir del JSON entrante. Son superficies de prueba local, no prueba de traspaso seguro.

**Funciones recuperables sin proveedor:** `analyzeScriptFor8Seconds`, `splitScriptIntoScenes` y `checkArticleDuplicate` (`utils/`). La UI puede reutilizarse tras resolver scaffold y runtime. Ninguna llamada `Flow.generate.*` fue ejecutada en esta auditoría.
