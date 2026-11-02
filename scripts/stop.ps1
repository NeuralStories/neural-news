<#
  Para la pila de neural.news (NN-114.1).

  Mata **sólo** los procesos de este proyecto: se busca por la línea de comandos
  (uvicorn neuralnews / neuralnews.worker / next start en apps\web), no por
  nombre de proceso, para no tocar nada ajeno.
#>
[CmdletBinding()]
param([switch]$Forzar)

$ErrorActionPreference = "SilentlyContinue"

# Expresiones regulares (no comodines): en Windows la ruta del ejecutable de
# Next es «…\node_modules\.bin\\..\next\dist\bin\next», con **barras
# invertidas**, y el patrón con barras normales no encajaba: el servidor del
# E2E se quedaba vivo y el siguiente E2E reutilizaba un build viejo (chunks
# 400 y página sin hidratar). Hallazgo B33.
$patrones = @(
  'neuralnews\.main:app',
  '-m\s+neuralnews\.worker',
  'next[\\/]dist[\\/]bin[\\/]next'
)

$procesos = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='node.exe'"
$objetivos = $procesos | Where-Object {
  $cmd = $_.CommandLine
  $cmd -and ($patrones | Where-Object { $cmd -match $_ })
}

if (-not $objetivos) {
  Write-Host "No hay procesos de neural.news en marcha."
  exit 0
}

foreach ($p in $objetivos) {
  Write-Host "Deteniendo PID $($p.ProcessId): $($p.CommandLine)"
  Stop-Process -Id $p.ProcessId -Force
}

Start-Sleep -Seconds 2
$restantes = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='node.exe'" |
  Where-Object {
    $cmd = $_.CommandLine
    $cmd -and ($patrones | Where-Object { $cmd -match $_ })
  }
if ($restantes) {
  Write-Host "Quedan procesos sin detener:"
  $restantes | ForEach-Object { Write-Host "  PID $($_.ProcessId)" }
  if ($Forzar) {
    $restantes | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Write-Host "Detenidos a la fuerza."
  }
} else {
  Write-Host "Pila parada."
}
