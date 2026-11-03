# NeuralStories Studio (recuperación funcional)

Interfaz mínima operativa construida sobre los **17 archivos recuperados** de Google Flow
(`flow-recovery/source/`, que se conservan intactos como referencia). Esta aplicación los
compila de forma independiente y añade la recepción del contrato editorial.

## Requisitos

- Node.js 24 (probado con 24.20). No se necesita ninguna clave ni proveedor externo.

## Instalación y ejecución local

```bash
cd apps/studio
npm install
npm run dev        # desarrollo en http://localhost:5173
npm run build      # compilación de producción (carpeta dist/)
npm run preview    # sirve dist/ en http://localhost:4173
npm test           # 8 pruebas del consumidor del contrato (Node, sin navegador)
```

## Qué funciona en este entorno

1. **Recepción del traspaso editorial** (`production_handoff.v1`): pestaña «1. Noticias» →
   tarjeta «Traspaso desde neural.news». Acepta el JSON descargado del backend editorial
   (`GET /api/v1/stories/{id}/handoff`) por archivo o pegado. Valida el contrato, verifica el
   SHA-256 del guion aprobado y rechaza reimportaciones antes de añadir nada.
2. **Redacción y escaleta** recuperadas: alta manual, importación por lotes, duplicados,
   aprobación y activación de una noticia en el estudio.
3. **Guion & escenas** recuperados: despiece automático del guion en tomas de ~8 s con
   prompts preliminares por escena (`utils/scriptAnalyzer.ts`).
4. **Personaje, plató CRT, voz y movimientos**: presets canon de solo lectura
   (`constants.ts`); aún no vinculados a recursos licenciados (ver RIESGOS.md R05/R07).

## Qué está desactivado a propósito

- `Flow.generate.image`, `Flow.generate.video` y `Flow.media.select` se resuelven a un
  **stub simulado** (`src/flow-sdk/index.ts`) que rechaza con un mensaje claro: no hay
  proveedor de pago conectado (RIESGOS.md R06). La exportación `Flow.download` sí funciona
  (descarga local del navegador).
- No hay publicación automática de ningún contenido.

## Decisiones de integración

- El **canon del contrato** vive en `packages/contracts/production_handoff.v1.schema.json`;
  `src/contracts/` contiene una copia para el empaquetado del navegador y las pruebas
  comprueban que ambas coinciden byte a byte (JSON igual).
- El consumidor TypeScript (`src/lib/handoffConsumer.ts`) es el espejo del consumidor Python
  (`packages/contracts/consumer/`): mismo esquema, misma verificación de hash, mismas reglas
  anti-duplicado. El registro de importaciones se guarda en `localStorage`
  (clave `nn-handoff-registry-v1`) y es inyectable para pruebas.
- El código recuperado no se modificó salvo `src/studio/App.tsx` (montar la tarjeta de
  traspaso y su manejador); los originales siguen en `flow-recovery/source/`.
- Los iconos (`Material Symbols`) y la tipografía se cargan de Google Fonts; sin conexión,
  la interfaz sigue siendo funcional (los iconos se muestran como texto).
