# Estimaciones y capacidad — sin prometer cifras no medidas

Este documento traduce el backlog nuevo de 106 tareas en **estimaciones orientativas de ingeniería**, no en un contrato de productividad. No incluyen demoras por cuentas externas, adquisición de videos, diseño artístico final, revisión humana, medios de terceros ni incidentes de infraestructura. La ventana autónoma de 10h es un límite de operación, no el plazo garantizado de producto completo.

## Cálculo del backlog inicial
| Etapa | Tareas | Suma de estimaciones | Significado |
|---|---:|---:|---|
| A | 23 | 765 min = 12 h 45 min | Base inicial, incluye 5 ampliaciones de riesgo |
| A — núcleo CORE | 18 | 590 min = 9 h 50 min | Máximo teórico sin margen suficiente; se ejecuta best-effort |
| A — STRETCH | 5 | 175 min = 2 h 55 min | No prometer dentro de 10 h |
| B | 38 | 2600 min = 43 h 20 min | Captación/LLM/biblioteca/animática evolucionada |
| C | 25 | 2360 min = 39 h 20 min | Montaje, episodios, QC, costes |
| D | 20 | 2305 min = 38 h 25 min | Integraciones y escalado |
| **TOTAL** | **106** | **8030 min = 133 h 50 min** | Estimación sin contingencias |

**Riesgo real:** CORE deja solo 10 minutos de margen en 10 horas (1,7%). Por tanto, NO debe prometerse completar los 18 ítems. Con reserva operativa del 25–35% una sesión de 10h dispone de **390–450 minutos netos** de ingeniería; el agente debe ejecutar CORE en orden y reportar exactamente dónde llegó. El objetivo de la sesión es un recorrido vertical verificable, incluso si queda pendiente una pantalla secundaria o la primera gráfica renderizada.

**Estimación para planificación con contingencia:** 8030 min × 1,25 = 10.037,5 min (167 h 17 min 30 s); ×1,35 = 10.840,5 min (180 h 40 min 30 s). No equivale a coste de proveedor ni a plazo calendario, porque hay tareas secuenciales y revisiones humanas. Coste de programación = `horas reales * tarifa/hora`, no hay tarifa acordada.

## Coste audiovisual general
Sin tarifas comprobadas, solo se puede cuantificar estructura: `cost_total = LLM + TTS + imágenes + vídeo + render/computación + almacenamiento + distribución + revisiones`. Mantener estimado, reservado y realmente facturado separados. Límite inicial real = 0 para operaciones pagadas, y la app no debe intentar cobrarlas.

## Eficiencia esperada (objetivos, no métricas actuales)
- Reutilizar medios aprobados y graphics para evitar generaciones repetidas.
- Regeneración por dependencia, no por episodio entero.
- Render programático para rótulos, porcentajes, barras y comparativas.
- Animática revisable antes de generación video IA.
- Cache por hash de inputs, versión, ratios, licencias y estado aprobación. Medir hit-rate real.

## Plan de QA presupuestado
Las estimaciones A ya incluyen tareas QA específicas pero no permiten cobertura industrial total. Antes de abrir producción al público son necesarios tests de seguridad, accesibilidad, regresión de modelos, derechos, gastos, recuperación y evidencia real. Un proveedor que no esté disponible deja pruebas `BLOCKED`, no inventar `PASS`.
