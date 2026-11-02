#!/bin/bash

# --- CONFIGURACIÓN ---
# Reemplaza esto con el comando real que lanza a tu agente y le pasa el PROMPT.md
AGENTE_CMD="tu_comando_de_agente_aqui --prompt PROMPT.md"
# ---------------------

LOCKFILE="/tmp/agente.lock"
ESPERA_FILE="docs/agente/espera.txt"
PLAN_FILE="docs/agente/PLAN.md"

# 1. Evitar ejecuciones simultáneas
if [ -e "$LOCKFILE" ] && kill -0 $(cat "$LOCKFILE") 2>/dev/null; then
    echo "El agente ya está en ejecución."
    exit 0
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# 2. Si el proyecto está marcado como terminado, no hacer nada
if [ -f "docs/agente/TERMINADO" ]; then
    echo "Proyecto completado. No se ejecuta nada."
    exit 0
fi

# 3. Comprobar si estamos en período de espera por cuota
if [ -f "$ESPERA_FILE" ]; then
    REANUDAR_EN=$(cat "$ESPERA_FILE")
    AHORA=$(date +%s)
    if [ "$AHORA" -lt "$REANUDAR_EN" ]; then
        echo "Aún esperando cuota. Saliendo sin gastar."
        exit 0
    else
        rm -f "$ESPERA_FILE"
    fi
fi

# 4. Ejecutar el agente y capturar su salida
echo "Iniciando ciclo del agente..."
OUTPUT=$(eval "$AGENTE_CMD" 2>&1)
echo "$OUTPUT"

# 5. Analizar errores de cuota directos en la salida (429, Rate limit)
if echo "$OUTPUT" | grep -qi -E "rate limit|429|quota exceeded"; then
    echo "Se detectó límite de cuota. Pausando por 1 hora."
    # Pausa de 3600 segundos (1 hora). Ajusta según tu proveedor.
    echo $(($(date +%s) + 3600)) > "$ESPERA_FILE"
    exit 0
fi

# 6. Analizar las etiquetas del Agente
if echo "$OUTPUT" | grep -q "\[ESTADO: INTERVENCION\]"; then
    echo "El agente requiere intervención humana. Deteniendo automatización."
    touch "docs/agente/TERMINADO"
    exit 1
fi

if echo "$OUTPUT" | grep -q "\[ESTADO: ESPERA_CUOTA\]"; then
    echo "El agente solicitó espera de cuota. Pausando 1 hora."
    echo $(($(date +%s) + 3600)) > "$ESPERA_FILE"
    exit 0
fi

if echo "$OUTPUT" | grep -q "\[ESTADO: PROYECTO_COMPLETADO\]"; then
    # Verificar que no mienta leyendo el PLAN.md
    if grep -q "\[ \]" "$PLAN_FILE"; then
        echo "El agente reportó completado, pero PLAN.md aún tiene tareas '[ ]'. Forzando continuación en el próximo ciclo."
    else
        echo "Validado: El proyecto está 100% completado."
        touch "docs/agente/TERMINADO"
    fi
    exit 0
fi

echo "Ciclo terminado con estado CONTINUAR. Listo para el próximo relanzamiento."
exit 0
