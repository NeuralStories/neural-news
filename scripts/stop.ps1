<#
  Para la pila de neural.news (NN-114.1).

  Mata **sólo** los procesos de este proyecto: se busca por la línea de comandos
  (uvicorn neuralnews / neuralnews.worker / next start en apps\web), no por
  nombre de proceso, para no tocar nada ajeno.
#>
[CmdletBinding()]
param([switch]$Forzar)

$ErrorActionPreference = "SilentlyContinue"

$patrones = @(
  "neuralnews.main:app",
  "-m neuralnews.worker",
  "next/dist/bin/next"
)

$procesos = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='node.exe'"
$objetivos = $procesos | Where-Object {
  $cmd = $_.CommandLine
  $cmd -and ($patrones | Where-Object { $cmd -like "*$_*" })
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
    $cmd -and ($patrones | Where-Object { $cmd -like "*$_*" })
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
