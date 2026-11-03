# Instrucciones para pasar al agente (Windows o Linux)

1. Descomprime el ZIP de entrega en una carpeta legible por el agente. Por ejemplo: `D:\Proyectos\neural-news-especificacion\` (el ejemplo no presupone la ruta real).
2. Crea/asigna una carpeta distinta y VACÍA para **nuevo repositorio**. Ejemplo: `D:\Proyectos\neural-news\`.
3. Abre el agente programador en su entorno que permita leer ambas carpetas, crear archivos, ejecutar terminal/servidores y pruebas. Si usa Codex Windows, selecciona como workspace el **repositorio nuevo**, no la antigua aplicación.
4. Adjunta o facilita **esta carpeta completa** (no solo el prompt), incluido `03_EVIDENCIA_FLOW`. Pega exactamente el texto íntegro de `PROMPT_UNICO_PARA_AGENTE.md`. No mezclar con prompts viejos.
5. Antes de 10h: preguntar al agente que verifique la ruta de lectura del paquete y la ruta de escritura del repo, que indique sin desvelar datos sensibles qué herramientas existen, que confirme pruebas. Si no puede leer archivos, no ha empezado.
6. Hasta tener los vídeos personales/handle, dejar la parte del presentador pendiente sin bloquear el pipeline restante.

## Archivos que NO necesita el agente
No entregues el viejo Plan Maestro ni los ZIP anteriores; están anulados. `flow-recovery.rar` ya figura íntegramente DENTRO del paquete nuevo. Evita cargar otros paquetes con instrucciones contradictorias.

## Ajustes necesarios del entorno (no secretos)
Node compatible actual, Python compatible actual, Docker+PostgreSQL, FFmpeg+ffprobe. El agente debe comprobar versiones antes de escoger. Para un arranque sin Docker se pueden configurar DB externa solo si está autorizada y no es productiva; no apuntar al servicio antiguo por intuición.
