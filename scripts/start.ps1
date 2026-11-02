<#
  Levanta la pila completa de neural.news: API, worker y web (NN-114.1).

  Cada proceso en su propia ventana de PowerShell, con su registro propio.
  Ctrl+C en esta ventana no corta los hijos: se cierran con scripts\stop.ps1.
#>
[CmdletBinding()]
param(
  [int]$PuertoApi = 8000,
  [int]$PuertoWeb = 3000,
  [switch]$SinWeb
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Info([string]$mensaje) { Write-Host $mensaje -ForegroundColor Cyan }

Info "API    → http://127.0.0.1:$PuertoApi  (registro: _api.log)"
Start-Process -FilePath "python" `
  -ArgumentList "-m", "uvicorn", "neuralnews.main:app", "--host", "127.0.0.1", "--port", "$PuertoApi" `
  -WorkingDirectory (Join-Path $raiz "apps\api") `
  -RedirectStandardOutput (Join-Path $raiz "_api.log") `
  -RedirectStandardError (Join-Path $raiz "_api.err.log")

Info "Worker → cola de trabajos (registro: _worker.log)"
Start-Process -FilePath "python" `
  -ArgumentList "-m", "neuralnews.worker" `
  -WorkingDirectory (Join-Path $raiz "apps\api") `
  -RedirectStandardOutput (Join-Path $raiz "_worker.log") `
  -RedirectStandardError (Join-Path $raiz "_worker.err.log")

if (-not $SinWeb) {
  Info "Web    → http://localhost:$PuertoWeb  (registro: _web.log)"
  $web = Join-Path $raiz "apps\web"
  $env:NEURAL_ENV = "local"
  Start-Process -FilePath "npm" -ArgumentList "run", "start", "--", "-p", "$PuertoWeb" `
    -WorkingDirectory $web `
    -RedirectStandardOutput (Join-Path $raiz "_web.log") `
    -RedirectStandardError (Join-Path $raiz "_web.err.log")
}

Start-Sleep -Seconds 6
try {
  $salud = Invoke-RestMethod -Uri "http://127.0.0.1:$PuertoApi/api/v1/health" -TimeoutSec 10
  Info "Salud: $($salud.app) v$($salud.version) · entorno $($salud.env)"
} catch {
  Info "La API todavía no responde: $($_.Exception.Message)"
}
Info "Listo. Para parar:  powershell -ExecutionPolicy Bypass -File scripts\stop.ps1"
