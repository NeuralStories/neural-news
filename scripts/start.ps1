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
$api = Start-Process -FilePath "python" `
  -ArgumentList "-m", "uvicorn", "neuralnews.main:app", "--host", "127.0.0.1", "--port", "$PuertoApi" `
  -WorkingDirectory (Join-Path $raiz "apps\api") `
  -RedirectStandardOutput (Join-Path $raiz "_api.log") `
  -RedirectStandardError (Join-Path $raiz "_api.err.log") `
  -PassThru

Info "Worker → cola de trabajos (registro: _worker.log)"
$worker = Start-Process -FilePath "python" `
  -ArgumentList "-m", "neuralnews.worker" `
  -WorkingDirectory (Join-Path $raiz "apps\api") `
  -RedirectStandardOutput (Join-Path $raiz "_worker.log") `
  -RedirectStandardError (Join-Path $raiz "_worker.err.log") `
  -PassThru

$pids = @{ api = $api.Id; worker = $worker.Id }

if (-not $SinWeb) {
  Info "Web    → http://localhost:$PuertoWeb  (registro: _web.log)"
  $web = Join-Path $raiz "apps\web"
  $env:NEURAL_ENV = "local"
  # En Windows `npm` es un script de consola (`npm.cmd`), no un ejecutable
  # Win32: `Start-Process -FilePath "npm"` falla con «no es una aplicación
  # Win32 válida» y la web no llegaba a arrancarse (hallazgo B30).
  $npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
  if (-not $npm) { $npm = Get-Command "npm" -ErrorAction SilentlyContinue }
  if (-not $npm) { throw "No se encuentra npm en el PATH. Instala Node 20 o superior." }
  $webProc = Start-Process -FilePath $npm.Source -ArgumentList "run", "start", "--", "-p", "$PuertoWeb" `
    -WorkingDirectory $web `
    -RedirectStandardOutput (Join-Path $raiz "_web.log") `
    -RedirectStandardError (Join-Path $raiz "_web.err.log") `
    -PassThru
  $pids.web = $webProc.Id
}

# Los PIDs se registran en el mismo fichero que usa `scripts/beta_stop.mjs`:
# así los dos lanzadores comparten una única parada y no quedan procesos
# huérfanos (hallazgo de la auditoría A3).
$dirLogs = Join-Path $raiz "storage\logs"
New-Item -ItemType Directory -Force -Path $dirLogs | Out-Null
$pids | ConvertTo-Json | Set-Content -Path (Join-Path $dirLogs "beta.pids.json") -Encoding utf8

Start-Sleep -Seconds 6
try {
  $salud = Invoke-RestMethod -Uri "http://127.0.0.1:$PuertoApi/api/v1/health" -TimeoutSec 10
  Info "Salud: $($salud.app) v$($salud.version) · entorno $($salud.env)"
} catch {
  Info "La API todavía no responde: $($_.Exception.Message)"
}
Info "Listo. Para parar:  powershell -ExecutionPolicy Bypass -File scripts\stop.ps1"
