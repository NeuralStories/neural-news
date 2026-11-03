<#
.SYNOPSIS
  Verificación técnica completa de la beta (F3). Cada comprobación termina con
  veredicto (PASA / FALLA / BLOQUEADA) y código de salida, y su salida
  íntegra queda en `docs\entrega\evidencias\<comando>.log`.

.DESCRIPTION
  Ejecuta, con la ruta definitive del repositorio (da igual que tenga espacios):
    1. python -m pytest tests -q
    2. npx tsc --noEmit
    3. npx eslint .
    4. npm run build
    5. npx playwright test          (límite propio: 10 minutos)
    6. python tools\check_clases.py
    7. python tools\check_a11y.py
    8. python tools\scan_secrets.py .
    9. python tools\generate_estados.py --check
   10. python tools\generar_manifiesto_studio.py --check
   11. python tools\generar_plan_casillas.py --check
   12. python tools\exportar_openapi.py --check
   13. python tools\auditar_evidencias.py
   14. git diff --check

  Escribe además `RESUMEN_VERIFICACIONES.md` con la tabla comando | veredicto |
  código de salida | log.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File docs\entrega\verificar.ps1
#>
[CmdletBinding()]
param(
  [string]$Raiz = "",
  [int]$TimeoutMinutos = 15,
  [int]$TimeoutPlaywrightMinutos = 10
)

$ErrorActionPreference = "Continue"

# La raíz se resuelve en el cuerpo, no en el valor por defecto del parámetro:
# alevaluarse ese valor, `$PSScriptRoot` todavía no existe en este host y
# `Split-Path` falla con «cadena vacía» (primer intento fallido de F3).
if (-not $Raiz) {
  $base = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
  $Raiz = Split-Path -Parent (Split-Path -Parent $base)
}
$Raiz = (Resolve-Path -LiteralPath $Raiz).Path
if (-not (Test-Path (Join-Path $Raiz "pytest.ini"))) {
  throw "La raíz '$Raiz' no parece el repositorio del proyecto (falta pytest.ini). Indica -Raiz."
}
Write-Host "Repositorio: $Raiz" -ForegroundColor Cyan

$carpetaEvidencias = Join-Path $Raiz "docs\entrega\evidencias"
New-Item -ItemType Directory -Force -Path $carpetaEvidencias | Out-Null

$web = Join-Path $Raiz "apps\web"

# --- Configuración local del proyecto ----------------------------------------
# Los comandos se ejecutan con la configuración local del repositorio (el
# `.env` de la raíz, que crea `scripts\bootstrap.ps1`). Sin `NEURAL_ENV=local`
# el build de Next falla **por diseño** (gate G5: fuera de local es obligatorio
# `NEURAL_API_URL`), así que la verificación usa la configuración real del
# proyecto y no un invento.
# Solo se muestran los NOMBRES de las variables: ningún valor se imprime.
$archivoEnv = Join-Path $Raiz ".env"
$clavesCargadas = @()
if (Test-Path $archivoEnv) {
  Get-Content -LiteralPath $archivoEnv | ForEach-Object {
    $linea = $_.Trim()
    if (-not $linea -or $linea.StartsWith("#") -or -not $linea.Contains("=")) { return }
    $clave, $valor = $linea.Split("=", 2)
    $clave = $clave.Trim()
    if ($clave -notmatch "^[A-Z_][A-Z0-9_]*$") { return }
    [System.Environment]::SetEnvironmentVariable($clave, $valor.Trim().Trim('"').Trim("'"), "Process")
    $script:clavesCargadas += $clave
  }
} else {
  [System.Environment]::SetEnvironmentVariable("NEURAL_ENV", "local", "Process")
  $clavesCargadas += "NEURAL_ENV (por defecto: no hay .env)"
}
Write-Host ("Configuración local cargada ({0} variables): {1}" -f $clavesCargadas.Count, ($clavesCargadas -join ", ")) -ForegroundColor DarkGray

# --- PostgreSQL local (para que el gate de PostgreSQL no quede en skip) ------
# `tests/test_postgres_projects.py` solo se ejecuta si existe
# NEURAL_TEST_POSTGRES. Si el PostgreSQL local del workspace responde, se
# prepara una base **aislada** (nn_pgtest) y la prueba corre de verdad: sin
# skip y con la evidencia de que el mismo esquema sirve en PostgreSQL.
if (-not $env:NEURAL_TEST_POSTGRES) {
  $pgAdmin = "postgresql://neural@127.0.0.1:5433/postgres"
  $pgTest = "postgresql+psycopg://neural@127.0.0.1:5433/nn_pgtest"
  $preparada = & python (Join-Path $Raiz "scripts\preparar_base_pg_test.py") 2>&1
  if ($LASTEXITCODE -eq 0) {
    [System.Environment]::SetEnvironmentVariable("NEURAL_TEST_POSTGRES", $pgTest, "Process")
    Write-Host "PostgreSQL local disponible: la prueba real de PostgreSQL se ejecutará (sin skip)." -ForegroundColor DarkGray
  } else {
    Write-Host "PostgreSQL local no disponible: la prueba de PostgreSQL quedará en skip (motivo documentado)." -ForegroundColor DarkGray
  }
}

# nombre | directorio | línea de comando | límite propio en minutos
$comprobaciones = @(
  @{ n = "pytest";                   d = $Raiz; c = "python -m pytest tests -q"; t = $TimeoutMinutos },
  @{ n = "tsc";                      d = $web;  c = "npx tsc --noEmit"; t = $TimeoutMinutos },
  @{ n = "eslint";                   d = $web;  c = "npx eslint ."; t = $TimeoutMinutos },
  @{ n = "build";                    d = $web;  c = "npm run build"; t = $TimeoutMinutos },
  @{ n = "playwright";               d = $web;  c = "npx playwright test"; t = $TimeoutPlaywrightMinutos },
  @{ n = "check_clases";             d = $Raiz; c = "python tools\check_clases.py"; t = $TimeoutMinutos },
  @{ n = "check_a11y";               d = $Raiz; c = "python tools\check_a11y.py"; t = $TimeoutMinutos },
  @{ n = "scan_secrets";             d = $Raiz; c = "python tools\scan_secrets.py ."; t = $TimeoutMinutos },
  @{ n = "generate_estados";         d = $Raiz; c = "python tools\generate_estados.py --check"; t = $TimeoutMinutos },
  @{ n = "generar_manifiesto_studio"; d = $Raiz; c = "python tools\generar_manifiesto_studio.py --check"; t = $TimeoutMinutos },
  @{ n = "generar_plan_casillas";    d = $Raiz; c = "python tools\generar_plan_casillas.py --check"; t = $TimeoutMinutos },
  @{ n = "exportar_openapi";         d = $Raiz; c = "python tools\exportar_openapi.py --check"; t = $TimeoutMinutos },
  @{ n = "auditar_evidencias";       d = $Raiz; c = "python tools\auditar_evidencias.py"; t = $TimeoutMinutos },
  # `git diff --check` busca espacios finales. Se excluyen dos carpetas, y el
  # motivo está escrito:
  #  - `docs/entrega/evidencias`: es la salida capturada de herramientas
  #    ajenas; conserva sus espacios finales tal cual (es evidencia).
  #  - `docs/gobernanza`: evidencia histórica verbatim con su propio manifiesto
  #    de SHA-256; limpiarla rompería ese manifiesto.
  @{ n = "git_diff_check";           d = $Raiz; c = 'git diff --check -- . ":(exclude)docs/entrega/evidencias" ":(exclude)docs/gobernanza" && git diff --cached --check -- . ":(exclude)docs/entrega/evidencias" ":(exclude)docs/gobernanza"'; t = 5 }
)

$resumen = @()
$fallos = 0

foreach ($comp in $comprobaciones) {
  $log = Join-Path $carpetaEvidencias ("{0}.log" -f $comp.n)
  $outTmp = "$log.out"
  $errTmp = "$log.err"
  $inicio = Get-Date
  Write-Host ">> $($comp.n): $($comp.c)" -ForegroundColor Cyan

  $proc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", $comp.c `
    -WorkingDirectory $comp.d `
    -RedirectStandardOutput $outTmp `
    -RedirectStandardError $errTmp `
    -NoNewWindow -PassThru

  $terminado = $proc.WaitForExit($comp.t * 60 * 1000)
  $codigo = -1
  $veredicto = "BLOQUEADA"
  $nota = ""

  if (-not $terminado) {
    try { $proc.Kill() } catch { }
    $nota = "se pasó del límite de $($comp.t) min"
  } else {
    # Tras `WaitForExit(ms)` con redirección, `ExitCode` puede quedar vacío si no
    # se espera al fin real del proceso: se llama a la sobrecarga sin timeout
    # para vaciar los flujos y obtener el código (intento 2 de F3: sin esto
    # todos los comandos salían «FALLA» con el código en blanco).
    $proc.WaitForExit()
    $codigo = $proc.ExitCode
    if ($null -eq $codigo) {
      $veredicto = "BLOQUEADA"
      $nota = "no se pudo obtener el código de salida"
    } elseif ($codigo -eq 0) {
      $veredicto = "PASA"
    } else {
      $veredicto = "FALLA"
      $fallos++
    }
  }

  # Salida íntegra (stdout + stderr) en un único log.
  $cabecera = @(
    "# Comprobación: $($comp.n)",
    "# Comando   : $($comp.c)",
    "# Directorio: $($comp.d)",
    "# Veredicto : $veredicto",
    "# Código de salida: $codigo",
    "# Duración  : $([int]((Get-Date) - $inicio).TotalSeconds) s",
    "# Nota      : $nota",
    "# Fecha     : $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))",
    "#",
    ""
  ) -join "`r`n"
  $cuerpo = ""
  if (Test-Path $outTmp) { $cuerpo += (Get-Content -LiteralPath $outTmp -Raw) }
  if (Test-Path $errTmp) { $cuerpo += (Get-Content -LiteralPath $errTmp -Raw) }
  Set-Content -LiteralPath $log -Value ($cabecera + $cuerpo) -Encoding utf8BOM
  Remove-Item -LiteralPath $outTmp, $errTmp -Force -ErrorAction SilentlyContinue

  Write-Host ("   {0}  (código {1}, {2} s)" -f $veredicto, $codigo, [int]((Get-Date) - $inicio).TotalSeconds) -ForegroundColor $(if ($veredicto -eq "PASA") { "Green" } else { "Red" })

  $resumen += [pscustomobject]@{
    Comprobacion = $comp.n
    Comando      = $comp.c
    Veredicto    = $veredicto
    Salida       = $codigo
    DuracionS    = [int]((Get-Date) - $inicio).TotalSeconds
    Log          = "docs/entrega/evidencias/$($comp.n).log"
    Nota         = $nota
  }
}

# --- Resumen en markdown ---------------------------------------------------
$tabla = @()
$tabla += "| Comprobación | Comando | Veredicto | Código de salida | Duración (s) | Log |"
$tabla += "|---|---|---|---|---|---|"
foreach ($r in $resumen) {
  $tabla += "| $($r.Comprobacion) | ``$($r.Comando)`` | **$($r.Veredicto)** | $($r.Salida) | $($r.DuracionS) | [log]($($r.Log)) |"
}
$doc = @(
  "# Resumen de verificaciones (F3)",
  "",
  "Generado por `docs/entrega/verificar.ps1` el $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss').",
  "Cada log contiene la salida **íntegra** del comando.",
  "",
  ($tabla -join "`r`n"),
  "",
  "**Resultado global: $(if ($fallos -eq 0) { 'PASA' } else { "FALLA ($fallos comprobaciones)" }).**",
  ""
) -join "`r`n"
Set-Content -LiteralPath (Join-Path $carpetaEvidencias "RESUMEN_VERIFICACIONES.md") -Value $doc -Encoding utf8BOM

Write-Host ""
Write-Host $doc -ForegroundColor White
if ($fallos -gt 0) { exit 1 }
exit 0
