# Notas de la beta — neural.news v1.0.0-beta.1

**Qué es esta beta:** una instalación **local** del motor editorial `neural.news` con el
NeuralStories Studio integrado, verificada con 14 comprobaciones automáticas.

---

## 1. Novedades de esta versión

- **Repositorio con nombre propio**: la carpeta `proyecto final` es ahora la **raíz real**
  del repositorio Git (antes `neural-news`). La historia, el commit y el remoto se
  conservan intactos.
- **Versión declarada y coherente**: `1.0.0-beta.1` en el paquete de la web, en
  `pyproject.toml`, en `__version__` del backend, en el contrato OpenAPI, en el endpoint de
  salud y **en el pie de la interfaz**. Un test lo comprueba: si dos sitios divergen, la
  suite falla.
- **Gobernanza dentro del repositorio**: el plan rector, el registro de decisiones y la
  evidencia del port de Flow pasan a estar en `docs/gobernanza/`, **con su manifiesto de
  SHA-256 verificado** y sin artefactos generados.
- **Plantilla de entorno completa**: `.env.example` recoge **las 30 variables** que lee el
  código (antes faltaban 14). Un test falla si se añade una variable y no se documenta.
- **Parche de seguridad**: Next.js 15.1.6 → **15.5.28** (mismo *major*). `npm audit
  --omit=dev` baja de 3 vulnerabilidades (2 altas y **1 crítica**) a **2** (1 alta y 1
  moderada).
- **Log del worker uniforme**: los cuatro `print()` sueltos del worker (arranque, barrido,
  fin de trabajo, error) se han sustituido por eventos JSON. El log ya no mezcla texto con
  JSON.
- **Centro de mantenimiento** en el Studio: auditoría SHA-256 de las fuentes y exportación
  del estado con manifiesto.
- **Métricas y alertas**: p95, tasa de fallo, duración, profundidad de cola, cola parada,
  lease vencido, presupuesto al 80 % y fallo repetido.
- **Rutas de modelo** con instantánea en el trabajo: cambiar la ruta después no altera un
  trabajo en marcha.

## 2. Problemas conocidos

| # | Problema | Alcance | Qué hacer |
|---|---|---|---|
| 1 | **2 avisos de seguridad** en dependencias transitivas de Next (`postcss`, `sharp`) | Build de la web | Requieren **Next 16**, un cambio ruptivo: no se aplican en la beta. El parche compatible ya está puesto. Revisar cuando salga la versión mayor |
| 2 | **`pip-audit` no está instalado** en la máquina de la entrega | Auditoría del lado Python | Instalarlo y auditar antes de la siguiente versión |
| 3 | **Animática sin locución** | Studio → Resultado | Es lo esperado: no hay TTS. El material exportado lo etiqueta |
| 4 | **Sin entorno virtual por proyecto** | Instalación | El backend usa el Python del sistema; si mueves la carpeta, reinstala (`pip install -e ".[dev]"`) |
| 5 | **Modo demo sin contenido real** | Todo el recorrido | Sin claves de proveedor no se llama a ningún servicio de pago: el contenido ficticio va marcado `DEMO` y usa el dominio reservado `.invalid` |
| 6 | **El manifiesto de la gobernanza tiene 3 ficheros desfasados** | `docs/gobernanza/MANIFEST_SHA256.json` | Se selló el 2026-10-30; después se actualizaron legítimamente `BACKLOG.csv`, `BACKLOG.json` (Fase 0) y el registro de decisiones (riesgo R-26). No se re-sella: el manifiesto es evidencia histórica |
| 7 | **El remoto es local** | Git | `.remotes/neural-news.git` está en el mismo disco. Sin copia externa hasta que se autorice un remoto remoto |

## 3. Requisitos para probar la beta

- **Windows** con PowerShell 7 (`pwsh`) — el arranque y la verificación están escritos para
  PowerShell; no hace falta WSL ni Bash.
- **Python 3.12** y **Node 20+** (probado con 3.12.6 / 24.20.0).
- **FFmpeg** en el `PATH` para la animática; **yt-dlp** para la transcripción de YouTube. Sin
  ellos, el resto de la beta funciona igual (con menos capacidades).
- **Espacio**: ~1,5 GB (incluye `node_modules`).
- **Nada de claves, nada de Docker, nada de internet** para el recorrido en modo demo.

## 4. Qué se espera de quien prueba la beta

1. **Que el recorrido llegue entero**: fuente → candidatos → investigación → guion →
   aprobación → lote → exportación, sin pasos manuales que no estén en la guía.
2. **Que los errores se vean con el motivo**: si un trabajo falla, la interfaz debe decir
   *por qué* (material insuficiente, presupuesto, conector) y no solo «falló».
3. **Que la aprobación siga siendo humana**: nadie debería poder aprovar un guion sin
   haberlo leído, y editar un guion aprobado debería **anular** esa aprobación.
4. **Que nada dependa de WSL, Bash ni cron**: la beta se usa con `pwsh`, `python`, `npm`,
   `npx` y `git`.
5. **Que los datos del usuario no se filtren**: el contenido de una fuente es dato, nunca
   instrucción; y las claves de proveedor no aparecen en la base sin cifrar.

## 5. Cómo informar de un problema

Ver [`GUIA_PRUEBAS_BETA.md`](GUIA_PRUEBAS_BETA.md) (plantilla de incidencia incluida).
Cada informe debe decir **qué se hizo**, **qué se esperaba**, **qué pasó** y **con qué
versión y comandos**, y adjuntar el log correspondiente de
`docs/entrega/evidencias/`.
