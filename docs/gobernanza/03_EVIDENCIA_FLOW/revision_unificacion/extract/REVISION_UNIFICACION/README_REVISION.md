# Revisión para decidir una sola aplicación

**Fecha:** 29-10-2026. **Directorio activo:** `C:\Users\haxth3\Documents\news_Neural`. Este paquete es una fotografía de revisión. No contiene una implementación nueva ni cambia los módulos actuales.

## Leer en este orden

1. [ESTADO_REAL.md](ESTADO_REAL.md): hechos comprobados en la aplicación publicada y límites de la prueba.
2. [MAPA_NAVEGACION_ACTUAL.md](MAPA_NAVEGACION_ACTUAL.md): rutas, ocho secciones de Studio y recorrido ficticio completo hasta trabajo de composición en cola.
3. [INVENTARIO_FUNCIONAL.md](INVENTARIO_FUNCIONAL.md): dos aplicaciones, API, módulos y 17 archivos de Flow.
4. [MATRIZ_UNIFICACION.md](MATRIZ_UNIFICACION.md): comparativa y decisión propuesta para conservar, fusionar o retirar.
5. [PROPUESTA_FLUJO_UNICO.md](PROPUESTA_FLUJO_UNICO.md): arquitectura y puertas de aceptación para discutir antes de programar.
6. `CAPTURAS/`: 42 PNG reales de escritorio, obtenidos del navegador en la URL publicada. Los nombres con `inicial` documentan transiciones o estados de carga; `01-fuentes-inicial.png` todavía muestra la pantalla previa a la navegación. Los archivos originales siguen en `auditoria-funcional-real/capturas`.

## Contenido del ZIP

`REVISION_UNIFICACION_NEURAL_NEWS.zip` contiene esta carpeta de revisión y una carpeta `CODIGO/` con una copia de los archivos fuente **tal como estaban en el árbol de trabajo**, incluidos cambios no confirmados: API, web, Studio, pruebas, contratos, migraciones, fixtures y los 17 archivos de Flow. `MANIFIESTO_ARCHIVOS_SHA256.txt` enumera cada entrada y su SHA-256. No se incluyeron `.git`, `.env`/ejemplos de credenciales, `storage`, bases de datos, `node_modules`, `.next`, `dist`, `public/studio`, caches, resultados de tests ni ZIPs anteriores.

El script `crear_paquete_revision.py` documenta la selección. El ZIP es una copia para estudiar y **no** debe reemplazar el checkout ni sus archivos sin confirmar. Los archivos de Flow se incluyen para evaluación técnica; su procedencia/licencia/activos deben validarse antes de uso público.

## Reproducir sin servicios de pago

La URL publicada se puede inspeccionar en modo DEMO: `https://desktop-hta6ms6.tailf8096f.ts.net:8443`. La revisión se hizo allí, no en una supuesta versión teórica. Para una instancia local limpia, en el checkout original (no sobre el ZIP):

```powershell
cd C:\Users\haxth3\Documents\news_Neural\apps\api
python -m pip install -e ".[dev]"
python -m uvicorn neuralnews.main:app --host 127.0.0.1 --port 8000
```

En otras terminales:

```powershell
cd C:\Users\haxth3\Documents\news_Neural\apps\api
python -m neuralnews.worker
```

Antes de abrir `/estudio`, construir Studio para que Vite lo publique en `apps/web/public/studio`:

```powershell
cd C:\Users\haxth3\Documents\news_Neural\apps\studio
npm ci
npm run build
```

```powershell
cd C:\Users\haxth3\Documents\news_Neural\apps\web
npm ci
npm run dev
```

Abrir `http://localhost:3000` y elegir modo demo. El proyecto usa configuración demo por defecto; no añadir claves ni activar servicios facturables para reproducir esta revisión. Studio vive en `apps/studio`; `vite.config.ts` genera el build bajo `apps/web/public/studio` y `/estudio` lo carga en un `iframe` del mismo origen. El ZIP omite builds, dependencias y datos locales. Las instrucciones operativas completas del checkout están en `docs/OPERATIONS.md`.

## Estado y seguridad

No se ejecutó `git clean/reset/checkout` ni se hizo commit. No se utilizó generación de pago ni se publicó contenido. La prueba añadió una fuente y noticia **ficticias** en el modo DEMO de la aplicación publicada, y guardó un plan local; se conservaron para no ejecutar borrados. El trabajo FFmpeg local estaba `QUEUED` en la última captura, sin resultado confirmado. No se copian credenciales, cookies, tokens ni bases de datos en el paquete.
