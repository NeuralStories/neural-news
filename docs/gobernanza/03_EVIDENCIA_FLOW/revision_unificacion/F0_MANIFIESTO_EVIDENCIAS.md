# F0 — Manifiesto de evidencias (NN-107, 31/10/2026)

## Evidencias recibidas y verificadas

| Evidencia | SHA-256 | Notas |
|---|---|---|
| `REVISION_UNIFICACION_NEURAL_NEWS.zip` (original, `Documents/news_Neural/`) | `d710c9f8ba90fa9bf72b46c055fd596220a913c44de58078c7caa7be79a1d70c` | Coincide con el declarado por el propietario; 3.166.835 bytes; 226 entradas; foto 29/10/2026 22:47 |
| Copia en evidencias (`03_EVIDENCIA_FLOW/revision_unificacion/REVISION_UNIFICACION_NEURAL_NEWS.zip`) | `d710c9f8ba90fa9bf72b46c055fd596220a913c44de58078c7caa7be79a1d70c` | Idéntica byte a byte al original |
| Extracto de análisis (`03_EVIDENCIA_FLOW/revision_unificacion/extract/`) | — | Solo lectura; nunca sobrescribe el repo activo |

## Resultado de la auditoría diferencial

- **Comparación de las 17 fuentes Flow vs Studio del ZIP: 12 idénticas + 5 modificadas + 0 ausentes** (confirmado por SHA-256 archivo a archivo). Modificadas: `App.tsx`, `TopNavigation.tsx`, `constants.ts`, `utils/scriptAnalyzer.ts`, `data/sourceManifest.ts`.
- **Módulos exclusivos del ZIP** (no existen en el repo activo): `providers/av_generation.py`, `services/av_jobs.py`, `services/av_render.py`, `services/editorial_status.py`, `services/handoff.py`, `api/av.py`, `packages/contracts` (production_handoff.v1 + consumidor Python), `fixtures/handoff`, `apps/studio` completo (6 componentes + shim `flow-sdk` + apiClient), 7 tests.
- **Módulos compartidos: 17/26 idénticos**; divergen (activo más nuevo): `config.py`, `models.py`, `states.py`, `worker_tasks.py`, `services/{batches,dedupe,research,scripts,sources}.py`.
- **Portabilidad:** los módulos av requieren `BatchBudget` y `RenderOutput` (presentes en el ZIP, ausentes en el activo) → 2 modelos + migración + router `av.py` en F1.

## Backup del repo activo (previo a cambios estructurales)

| Evidencia | SHA-256 |
|---|---|
| `backups/neural-news-pre-NN107-F0-20261031.zip` (189 ficheros, 20,5 MB; excluye node_modules/.next/__pycache__/test-results/.git) | `c08d99b4b0fea383bea0c8b4ee77775e6d19ff0822cd7858bebb39116f77d69d` |
| Manifiesto junto al ZIP (`neural-news-pre-NN107-F0-20261031.SHA256.txt`) | — |

## Evidencia documental (dentro del ZIP, no verificada contra Flow remoto)

- `REVISION_UNIFICACION/ESTADO_REAL.md` — 11 hallazgos reproducibles con causa localizada (R-BUG-1 #2, R-BUG-2 #5; nuevos: #3 verificación inflada, #4 duración 8 s/8,8 s, #9 FFmpeg simulado, #10 estados de proveedor contradictorios).
- `REVISION_UNIFICACION/CAPTURAS/` — 30 capturas de la integración en ejecución (incluida composición encolada, no confirmada).
- `REVISION_UNIFICACION/MANIFIESTO_ARCHIVOS_SHA256.txt` — manifiesto interno de la revisión anterior.

## Estados del gate

- F0: **SUPERADO** (autorización del propietario: «puede comenzar»; gate cerrado con matriz definitiva + backup + ADRs actualizados).
- F1–F5: **AUTORIZADAS** sin nueva aprobación por fase; conflictos arquitectónicos → documentar alternativas antes de decidir (mandato del propietario).
- Evidencia original `03_EVIDENCIA_FLOW/source/` y `flow-recovery/source/`: intacta (D1).
