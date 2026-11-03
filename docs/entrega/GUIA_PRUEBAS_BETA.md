# Guía de pruebas de la beta — neural.news v1.0.0-beta.1

Pruebas **a mano**, paso a paso, sobre la instalación local. Cada prueba dice qué hacer,
qué se espera y qué significa si falla. Al final, la plantilla para informar de
incidencias.

---

## 0. Preparación (una vez)

```powershell
cd "C:\Users\haxth3\Documents\NeuralStories\proyecto final"

powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

Debe terminar con «Listo.». Si falla, **no sigas**: el resto de pruebas no valen.

```powershell
pwsh -NoProfile -File scripts\start.ps1
```

Debe mostrar la URL de la web, la de la API y «Salud: neural.news v1.0.0-beta.1».

---

## 1. Comprobación rápida de que todo está en pie (2 min)

| # | Acción | Se espera |
|---|---|---|
| 1.1 | Abre http://localhost:3000 | La página de acceso, con el botón «Entrar en modo demo» |
| 1.2 | Pulsa «Entrar en modo demo» | Entras al producto; en la barra superior, «neural.news v1.0.0-beta.1» en el pie |
| 1.3 | Abre http://127.0.0.1:8000/api/v1/health | JSON con `"ok": true`, `"version": "1.0.0-beta.1"` y el detalle de cada dependencia |
| 1.4 | Abre http://localhost:3000/ops | La página de Operación con la salud, el consumo de hoy, los trabajos y las métricas |
| 1.5 | En `/ops`, comprueba «Estado de proveedores» | Cada proveedor con su estado; los que necesitan clave, **sin** clave y declarados como no configurados |

> Si 1.3 falla, mira `apps\api\_api.log`. Si la web no carga, `apps\web\_web.log`.

## 2. Recorrido editorial completo (10 min)

| # | Acción | Se espera |
|---|---|---|
| 2.1 | **Fuentes → «Añadir fuente»** → pega `https://www.youtube.com/watch?v=aqz-KE-bpKQ` (vídeo de prueba público) y confirma | La fuente aparece en la lista con estado «Pendiente» y **sin duplicados** si la vuelves a añadir |
| 2.2 | Espera a que el worker la procese (o pulsa «Actualizar») | El estado pasa a «Lista» (o «Solo información básica» si no hay transcripción) y hay transcripción o aviso claro |
| 2.3 | **Noticias**: busca la noticia extraída | Aparece con fecha real, verificación y **posibles duplicados marcados** |
| 2.4 | Pulsa «Investigar» | La noticia se investiga; **ninguna afirmación queda «confirmada» sin evidencia**, y la evidencia de demo va marcada `DEMO` |
| 2.5 | Abre la noticia y mira las afirmaciones | Cada una con su estado y su nota de verificación; las opiniones quedan «No verificable» |
| 2.6 | Abre el **Estudio** y revisa los 8 pasos | Cada paso carga su estado guardado (no se pierde al recargar) |
| 2.7 | En «Guion», edita el texto y guarda; **aprueba** la versión | «Aprobar esta versión» funciona sobre la versión **más reciente** |
| 2.8 | Vuelve a editar el guion **después** de aprobar | La aprobación queda **anulada** y la interfaz lo dice |
| 2.9 | **Lotes → nuevo lote**, selecciona noticias y exporta | Se genera el paquete (ZIP con manifiesto JSON, guiones MD y storyboard) y se puede descargar |

## 3. Lo que la beta **no** debe hacer (pruebas negativas)

| # | Acción | Se espera |
|---|---|---|
| 3.1 | Intenta aprobar un guion sin haberlo leído | No hay atajo: la aprobación exige una acción explícita sobre la versión concreta |
| 3.2 | Busca una afirmación «confirmada» sin evidencia | No existe: sin evidencia, el estado es `UNVERIFIED` |
| 3.3 | Mira `/ops` con el worker parado | En menos de un minuto aparece la alerta **«cola parada»** |
| 3.4 | Configura `NEURAL_PAID_SERVICES_ENABLED=false` con claves presentes | Ningún trabajo llama a un proveedor de pago: el presupuesto manda |
| 3.5 | Intenta arrancar la web **sin** `NEURAL_ENV=local` | El build **falla** con un mensaje que dice qué definir (no compila a medias) |

## 4. Verificación automática (si quieres comprobarlo todo)

```powershell
pwsh -NoProfile -File docs\entrega\verificar.ps1
```

14 comprobaciones con veredicto, código de salida y log. Resumen en
`docs/entrega/RESUMEN_VERIFICACIONES.md`.

## 5. Plantilla de incidencia

Copia este bloque en el informe y rellénalo **todo**. Un informe sin pasos exactos no
sirve.

```markdown
### Incidencia: <titular corto>

- **Versión**: 1.0.0-beta.1 (rama release/1.0.0-beta.1, commit <hash>)
- **Fecha y hora**: <AAAA-MM-DD HH:MM, zona horaria>
- **Entorno**: Windows <versión> · Python <versión> · Node <versión>
  · con/sin FFmpeg · con/sin yt-dlp · con/sin claves de proveedor
- **Cómo se arrancó**: scripts\bootstrap.ps1 + scripts\start.ps1
- **Qué esperaba**: <qué debía ocurrir>
- **Qué pasó**: <qué ocurrió, con el texto exacto del mensaje>
- **Pasos para reproducir**:
  1. <paso>
  2. <paso>
  3. <paso>
- **Frecuencia**: siempre / a veces (¿cuántas de N veces?) / solo la primera vez
- **Logs adjuntos**: <p. ej. apps\api\_api.log, apps\api\_worker.log, apps\web\_web.log>
- **Resultado esperado**: <qué debería haber pasado>
```

**Reglas para el informe:**

1. Pega los mensajes **exactos**, no una descripción.
2. Adjunta el log correspondiente (API, worker o web) y di **qué línea** mirar.
3. Si el problema es visual, adjunta una captura y describe el ancho de la ventana.
4. No incluyas **claves ni contraseñas** en el informe: si aparece una clave en un log,
   **rótala** y dilo.
5. Si el problema es «no funciona el proveedor X», di qué clave usaste **por su nombre**,
   nunca su valor.
