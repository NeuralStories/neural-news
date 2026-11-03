<#
  Auditoría A1 — clon limpio desde la rama corregida.

  Reproduce, paso a paso y sin supuestos, lo que haría alguien que clona el
  repositorio por primera vez:

    1. clonar la rama
    2. crear el .env a partir de .env.example
    3. instalar el backend (venv + `pip install -e apps/api[dev]`)
    4. instalar la web (`npm ci`)
    5. pytest, typecheck (tsc), lint (eslint), build y Playwright
    6. arrancar la pila en otros puertos (3001/8001) y comprobar 200 + /health
    7. parar y comprobar que no quedan procesos

  Cada paso deja su registro en `docs/entrega/evidencias/auditoria/` y su
  código de salida en el resumen JSON. El script NO borra el clon: su ruta se
  imprime al final para que la limpieza sea una decisión explícita.

  Uso:
    pwsh -NoProfile -File tools/auditoria/verificar_clon_limpio.ps1 `
         -Destino "$env:TEMP/beta-audit2" -Rama "release/1.0.0-beta.1"
#>
[CmdletBinding()]
param(
  [string]$Destino = "$env:TEMP/beta-audit2",
  [string]$Rama = "release/1.0.0-beta.1",
  [int]$PuertoApi = 8001,
  [int]$PuertoWeb = 3001,
  [switch]$ReutilizarClon
)

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$evidencias = Join-Path $raiz "docs\entrega\evidencias\auditoria"
New-Item -ItemType Directory -Force -Path $evidencias | Out-Null

$resumen = @()
$logActual = $null

function Log([string]$mensaje) {
  $marca = (Get-Date).ToString("HH:mm:ss")
  Write-Host "[$marca] $mensaje"
  if ($logActual) { Add-Content -Path $logActual -Value "[$marca] $mensaje" -Encoding utf8 }
}

function Paso([string]$nombre, [scriptblock]$bloque) {
  $global:logActual = Join-Path $evidencias ("A1_clon_" + $nombre + ".log")
  Set-Content -Path $global:logActual -Value ("=== $nombre ===" + [Environment]::NewLine) -Encoding utf8
  Log "--- $nombre ---"
  $global:LASTEXITCODE = 0
  $salida = & $bloque 2>&1
  $codigo = $LASTEXITCODE
  $salida | Out-String | Add-Content -Path $global:logActual -Encoding utf8
  Log ("$nombre -> exit $codigo")
  $script:resumen += [pscustomobject]@{ paso = $nombre; exit = $codigo }
  return $codigo
}

Write-Host "=== A1: clon limpio ($Rama) en $Destino ==="

# --- 1. clonar ---------------------------------------------------------------
$logActual = Join-Path $evidencias "A1_clon_01_clone.log"
Set-Content -Path $logActual -Value "=== clonar ===" -Encoding utf8
if ((Test-Path $Destino) -and $ReutilizarClon) {
  Log "Se reutiliza el clon existente en $Destino"
} else {
  if (Test-Path $Destino) {
    Write-Host "ERROR: el destino ya existe. Usa otra ruta o -ReutilizarClon (esta comprobación no borra nada)."
    exit 2
  }
  git clone --branch $Rama $raiz $Destino 2>&1 | Out-String | Add-Content -Path $logActual -Encoding utf8
  if ($LASTEXITCODE -ne 0) { Write-Host "FALLA: no se pudo clonar (exit $LASTEXITCODE)"; exit 1 }
  Log "Clon creado en $Destino"
}

# --- 2. .env -----------------------------------------------------------------
Copy-Item (Join-Path $Destino ".env.example") (Join-Path $Destino ".env")
Log ".env creado a partir de .env.example"

# --- 3. backend --------------------------------------------------------------
$venv = Join-Path $Destino ".venv"
python -m venv $venv
$py = Join-Path $venv "Scripts\python.exe"
& $py -m pip install --quiet --upgrade pip 2>&1 | Out-Null
& $py -m pip install --quiet -e (Join-Path $Destino "apps\api[dev]") 2>&1 | Out-String |
  Add-Content -Path (Join-Path $evidencias "A1_clon_02_install_backend.log") -Encoding utf8
if ($LASTEXITCODE -ne 0) { Write-Host "FALLA: la instalación del backend falló (exit $LASTEXITCODE)"; exit 1 }
Log "Backend instalado en la venv del clon"

# --- 4. web ------------------------------------------------------------------
Push-Location (Join-Path $Destino "apps\web")
npm ci 2>&1 | Out-String | Add-Content -Path (Join-Path $evidencias "A1_clon_03_install_web.log") -Encoding utf8
$codigoInstalacion = $LASTEXITCODE
Pop-Location
if ($codigoInstalacion -ne 0) { Write-Host "FALLA: `npm ci` falló (exit $codigoInstalacion)"; exit 1 }
Log "Web instalada (npm ci)"

# --- 5. comprobaciones --------------------------------------------------------
# Los bloques NO usan `exit`: dentro de un scriptblock invocado con `&`,
# `exit` terminaría el script entero. El código de salida se toma de
# $LASTEXITCODE justo después de la última orden nativa del bloque.
$codigoPytest = Paso "04_pytest" { Push-Location $Destino; & $py -m pytest tests -q; Pop-Location }
$codigoTsc = Paso "05_typecheck" { Push-Location (Join-Path $Destino "apps\web"); npm run typecheck; Pop-Location }
$codigoLint = Paso "06_lint" { Push-Location (Join-Path $Destino "apps\web"); npm run lint; Pop-Location }
$codigoBuild = Paso "07_build" {
  # El build exige saber el entorno: `NEURAL_ENV=local` es la instalación de
  # escritorio (lo mismo que hace ahora `scripts/bootstrap.ps1`). Fuera de local
  # hay que definir NEURAL_API_URL y el build falla a propósito.
  $env:NEURAL_ENV = "local"
  Push-Location (Join-Path $Destino "apps\web")
  npm run build
  Pop-Location
}

# Playwright: el config levanta su propia pila en 3000/8000.
$codigoE2e = Paso "08_playwright" { Push-Location (Join-Path $Destino "apps\web"); npm run e2e; Pop-Location }

# --- 6. arranque en otros puertos -------------------------------------------
$logActual = Join-Path $evidencias "A1_clon_09_arranque.log"
Set-Content -Path $logActual -Value "=== arranque en $PuertoApi/$PuertoWeb ===" -Encoding utf8
$env:NEURAL_BETA_API_PORT = "$PuertoApi"
$env:NEURAL_BETA_WEB_PORT = "$PuertoWeb"
$env:NEURAL_BETA_API_URL = "http://127.0.0.1:$PuertoApi"
$env:NEURAL_BETA_WEB_URL = "http://localhost:$PuertoWeb"
$env:NEURAL_BETA_PYTHON = $py
node (Join-Path $Destino "scripts\beta_start.mjs") 2>&1 | Out-String | Add-Content -Path $logActual -Encoding utf8
$codigoArranque = $LASTEXITCODE

$salud = $null
try {
  $salud = Invoke-RestMethod -Uri "http://127.0.0.1:$PuertoApi/api/v1/health" -TimeoutSec 15
} catch { }
$webOk = $false
try {
  $r = Invoke-WebRequest -Uri "http://localhost:$PuertoWeb" -UseBasicParsing -TimeoutSec 15
  $webOk = ($r.StatusCode -eq 200)
} catch { }

"salud=$($salud | ConvertTo-Json -Compress)" | Add-Content -Path $logActual -Encoding utf8
"web_status_ok=$webOk" | Add-Content -Path $logActual -Encoding utf8
$version = if ($salud) { $salud.version } else { "sin respuesta" }
Log "Arranque: api=$($salud -ne $null) version=$version web200=$webOk (exit $codigoArranque)"
$resumen += [pscustomobject]@{ paso = "09_arranque"; exit = $(if ($salud -and $webOk) { 0 } else { 1 }) }

# --- 7. parar ----------------------------------------------------------------
node (Join-Path $Destino "scripts\beta_stop.mjs") 2>&1 | Out-String | Add-Content -Path $logActual -Encoding utf8
Start-Sleep -Seconds 3
$restantes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match "neuralnews\.main:app|-m\s+neuralnews\.worker") }
$libres = $true
foreach ($p in @($PuertoApi, $PuertoWeb)) {
  if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) { $libres = $false }
}
"procesos_restantes=$($restantes.Count) puertos_libres=$libres" | Add-Content -Path $logActual -Encoding utf8
Log "Parada: procesos restantes=$($restantes.Count) puertos libres=$libres"
$resumen += [pscustomobject]@{ paso = "10_parada"; exit = $(if ($restantes.Count -eq 0 -and $libres) { 0 } else { 1 }) }

# --- resumen -----------------------------------------------------------------
$resumen | ConvertTo-Json -Depth 3 | Set-Content -Path (Join-Path $evidencias "A1_clon_resumen.json") -Encoding utf8
Write-Host ""
Write-Host "=== Resumen A1 ==="
$resumen | Format-Table -AutoSize | Out-String | Write-Host
Write-Host "Clon en: $Destino (la auditoría NO lo borra: bórralo cuando quieras)"
if ($resumen | Where-Object { $_.exit -ne 0 }) { exit 1 }
exit 0
