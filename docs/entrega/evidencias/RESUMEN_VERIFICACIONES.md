# Resumen de verificaciones (F3)

Generado por docs/entrega/verificar.ps1 el 2026-11-03 09:55:33.
Cada log contiene la salida **íntegra** del comando.

| Comprobación | Comando | Veredicto | Código de salida | Duración (s) | Log |
|---|---|---|---|---|---|
| pytest | `python -m pytest tests -q` | **PASA** | 0 | 120 | [log](docs/entrega/evidencias/pytest.log) |
| tsc | `npx tsc --noEmit` | **PASA** | 0 | 7 | [log](docs/entrega/evidencias/tsc.log) |
| eslint | `npx eslint .` | **PASA** | 0 | 8 | [log](docs/entrega/evidencias/eslint.log) |
| build | `npm run build` | **PASA** | 0 | 33 | [log](docs/entrega/evidencias/build.log) |
| playwright | `npx playwright test` | **PASA** | 0 | 99 | [log](docs/entrega/evidencias/playwright.log) |
| check_clases | `python tools\check_clases.py` | **PASA** | 0 | 1 | [log](docs/entrega/evidencias/check_clases.log) |
| check_a11y | `python tools\check_a11y.py` | **PASA** | 0 | 2 | [log](docs/entrega/evidencias/check_a11y.log) |
| scan_secrets | `python tools\scan_secrets.py .` | **PASA** | 0 | 3 | [log](docs/entrega/evidencias/scan_secrets.log) |
| generate_estados | `python tools\generate_estados.py --check` | **PASA** | 0 | 0 | [log](docs/entrega/evidencias/generate_estados.log) |
| generar_manifiesto_studio | `python tools\generar_manifiesto_studio.py --check` | **PASA** | 0 | 0 | [log](docs/entrega/evidencias/generar_manifiesto_studio.log) |
| generar_plan_casillas | `python tools\generar_plan_casillas.py --check` | **PASA** | 0 | 0 | [log](docs/entrega/evidencias/generar_plan_casillas.log) |
| exportar_openapi | `python tools\exportar_openapi.py --check` | **PASA** | 0 | 3 | [log](docs/entrega/evidencias/exportar_openapi.log) |
| auditar_evidencias | `python tools\auditar_evidencias.py` | **PASA** | 0 | 14 | [log](docs/entrega/evidencias/auditar_evidencias.log) |
| git_diff_check | `git diff --check -- . ":(exclude)docs/entrega/evidencias" ":(exclude)docs/gobernanza" && git diff --cached --check -- . ":(exclude)docs/entrega/evidencias" ":(exclude)docs/gobernanza"` | **PASA** | 0 | 0 | [log](docs/entrega/evidencias/git_diff_check.log) |

**Resultado global: PASA.**

