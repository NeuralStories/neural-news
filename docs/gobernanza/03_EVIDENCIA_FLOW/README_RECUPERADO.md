# Extractor de NeuralStories Studio para Google Flow

Herramienta de lectura del editor de Flow. No modifica la aplicación, no genera vídeos y guarda el perfil de Chrome fuera del proyecto. El URL predeterminado es el proyecto `2611c905…` confirmado por el usuario; `--url` permite cambiarlo.

## Requisitos

- Node.js 20 o posterior.
- Google Chrome instalado.
- Cuenta con acceso al proyecto de Flow.

## Ejecutar

En Windows (PowerShell) o macOS (Terminal), dentro de esta carpeta:

```sh
npm install
npm test
npm run extract
```

El programa abre Chrome con un perfil dedicado. Si aparece Google, inicia sesión tú mismo y vuelve al proyecto. La espera predeterminada es de 10 minutos; se ajusta con `--auth-timeout 1200` (segundos). El perfil se conserva entre ejecuciones en `LOCALAPPDATA/NeuralFlowRecovery/chrome-profile` en Windows o `~/Library/Application Support/NeuralFlowRecovery/chrome-profile` en macOS. Nunca se empaqueta.

Si Google muestra «el navegador o la aplicación no sean seguros», inicia sesión primero en un Chrome normal con un **perfil dedicado distinto**, antes de conectar Playwright:

```sh
npm run chrome:login
```

Inicia sesión en la ventana que se abre y comprueba que puedes ver el proyecto. Cierra esa ventana y ejecuta:

```sh
npm run chrome:manual
npm run extract -- --cdp
```

`chrome:manual` abre el mismo perfil separado con un puerto CDP limitado a `127.0.0.1`. El extractor solo acepta la conexión registrada por este lanzador; no se adjunta al perfil principal de Chrome ni exporta cookies. Deja abierto ese Chrome hasta terminar. Si Google también bloquea el inicio de sesión en `chrome:login`, detén el proceso y usa una exportación oficial o manual del editor.

La salida aparece en `source/`, `reports/` y `neural-news-source.zip`. Si falta algún archivo o no se logra verificar, el ZIP se llama `neural-news-source-INCOMPLETE.zip`. Si no se captura ningún archivo, no se crea ZIP. Para una nueva ejecución tras una captura parcial, usa una carpeta nueva con `--output RUTA` para no sobrescribir la anterior.

```sh
npm run extract -- --url "https://flow.google.com/project/…/tool/…" --output "./segundo-intento"
```

## Qué comprueba

El programa intenta leer un modelo de editor expuesto, después copiar mediante teclado y finalmente leer un DOM no virtualizado. Guarda bytes UTF-8 y calcula SHA-256, tamaño y líneas. Compara una segunda lectura cuando es posible, revisa sintaxis TypeScript/TSX e imports relativos, detecta contenidos idénticos y genera `manifest.json`, `errors.json`, `extraction-report.md` y un diagnóstico del editor.

La ruta de un archivo se marca como inferida si Flow no expone la ruta en el DOM y se usa el inventario de referencia. En ese caso hay que contrastarla con el árbol visible. Un archivo corto puede ser válido; uno vacío siempre falla. Un hash local no prueba que el editor haya entregado el archivo completo. Tampoco se declara la aplicación ejecutable sin una compilación real.

El extractor preliminar para macOS mencionado en las instrucciones no se adjuntó: solo se recibió el texto. Este código es una implementación nueva basada en los requisitos recibidos. Se validó en una sesión autorizada de Flow el 28 de octubre de 2026: detectó 17 archivos, leyó todas las líneas numeradas del visor y repitió la lectura tras cambiar de archivo. Si cambia la interfaz, `reports/editor-diagnostic.json` ayuda a ajustar los selectores.
