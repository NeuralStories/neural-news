<#
  Auditoría A2, A3 y A4 — comprobaciones con veredicto, código de salida y log.

  Cada comprobación escribe una línea `PASA|FALLA  <código>  <detalle>` en
  `docs/entrega/evidencias/auditoria/A2_A3_A4.log` y devuelve 1 si algo falla.

  Nota de PowerShell: `exit` dentro de un scriptblock invocado con `&` termina
  el script entero. Por eso los bloques **no** llaman a `exit`: fijan
  `$global:codigoComprobacion` y es la función la que decide.

  Uso:
    pwsh -NoProfile -File tools/auditoria/verificar_a2_a3_a4.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$evidencias = Join-Path $raiz "docs\entrega\evidencias\auditoria"
New-Item -ItemType Directory -Force -Path $evidencias | Out-Null
$log = Join-Path $evidencias "A2_A3_A4.log"
Set-Content -Path $log -Value ("=== A2, A3 y A4 — auditoría independiente ===" + [Environment]::NewLine) -Encoding utf8

$global:fallos = 0

function Comprobacion([string]$nombre, [scriptblock]$bloque) {
  $global:codigoComprobacion = 0
  $global:LASTEXITCODE = 0
  $salida = & $bloque *>&1 | Out-String
  $codigo = $global:codigoComprobacion
  if ($codigo -eq 0 -and $global:LASTEXITCODE -ne 0) { $codigo = $global:LASTEXITCODE }
  $linea = ($salida -replace "`r?`n", " | ").Trim()
  if ($linea.Length -gt 400) { $linea = $linea.Substring(0, 400) + "…" }
  $veredicto = if ($codigo -eq 0) { "PASA" } else { "FALLA" }
  if ($codigo -ne 0) { $global:fallos++ }
  Add-Content -Path $log -Value ("$veredicto  exit=$codigo  $nombre :: $linea") -Encoding utf8
  Write-Host "$veredicto  $nombre (exit $codigo)"
}

Write-Host "== A2: coherencia documental =="

Comprobacion "A2.1 el directorio de gobernanza es docs/gobernanza (y no docs/governance)" {
  $existe = Test-Path (Join-Path $raiz "docs\gobernanza")
  $otro = Test-Path (Join-Path $raiz "docs\governance")
  Write-Host "docs/gobernanza=$existe docs/governance=$otro"
  if ($existe -and -not $otro) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Comprobacion "A2.2 enlaces y rutas de los documentos" {
  python (Join-Path $raiz "tools\auditoria\comprobar_enlaces.py")
  $global:codigoComprobacion = $LASTEXITCODE
}

Comprobacion "A2.3 .env.example refleja todas las variables que lee el codigo" {
  python (Join-Path $raiz "tools\auditoria\comprobar_configuracion.py") --sin-health
  $global:codigoComprobacion = $LASTEXITCODE
}

Write-Host "== A3: ciclo en frio =="

Comprobacion "A3.1 parada en frio (sin pila en marcha): sin errores" {
  node (Join-Path $raiz "scripts\beta_stop.mjs")
  $global:codigoComprobacion = $LASTEXITCODE
}

Comprobacion "A3.2 arranque: API y web responden con la version de la beta" {
  node (Join-Path $raiz "scripts\beta_start.mjs")
  $api = $null
  try { $api = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 20 } catch { }
  $web = 0
  try { $web = (Invoke-WebRequest "http://localhost:3000" -UseBasicParsing -TimeoutSec 20).StatusCode } catch { }
  Write-Host "api.version=$($api.version) web=$web"
  if ($api -and $api.version -eq "1.0.0-beta.1" -and $web -eq 200) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Comprobacion "A3.3 segunda parada: puertos libres y sin procesos huerfanos" {
  node (Join-Path $raiz "scripts\beta_stop.mjs")
  Start-Sleep -Seconds 3
  $procesos = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match "neuralnews\.main:app|-m\s+neuralnews\.worker") }
  $libres = $true
  foreach ($p in @(3000, 8000)) {
    if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) { $libres = $false }
  }
  Write-Host "procesos_restantes=$($procesos.Count) puertos_libres=$libres"
  if ($procesos.Count -eq 0 -and $libres) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Comprobacion "A3.4 el segundo arranque vuelve a dejar la pila en pie (idempotencia)" {
  node (Join-Path $raiz "scripts\beta_start.mjs")
  $api = $null
  try { $api = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 20 } catch { }
  $web = 0
  try { $web = (Invoke-WebRequest "http://localhost:3000" -UseBasicParsing -TimeoutSec 20).StatusCode } catch { }
  Write-Host "api.version=$($api.version) web=$web"
  if ($api -and $web -eq 200) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Write-Host "== A4: git e integridad =="

Comprobacion "A4.1 el tag v1.0.0-beta.1 es anotado y apunta a 1c63a3a" {
  $tipo = git -C $raiz cat-file -t v1.0.0-beta.1
  $commit = (git -C $raiz rev-list -n1 v1.0.0-beta.1).Trim()
  Write-Host "tipo=$tipo commit=$commit"
  if ($tipo -eq "tag" -and $commit.StartsWith("1c63a3a")) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Comprobacion "A4.2 los commits posteriores al tag no tocan codigo de producto" {
  # Hallazgo de la auditoria: 87b07cc creo scripts/auditar_entrega.mjs (la
  # herramienta de auditoria de la entrega). Es codigo de VERIFICACION, no del
  # producto: apps/, infra/ y packages/ siguen identicos al tag, asi que el tag
  # representa el producto que se entrega. Se informa de ambos.
  $producto = @()
  $herramientas = @()
  foreach ($c in @("7c18c29", "87b07cc", "c02e055")) {
    $ficheros = git -C $raiz show --name-only --pretty=format: $c
    foreach ($f in $ficheros) {
      if (-not $f -or $f -match "^$") { continue }
      if ($f -match "^(apps|infra|packages|tests)/") { $producto += "$c $f" }
      elseif ($f -notmatch "^docs/") { $herramientas += "$c $f" }
    }
  }
  Write-Host "codigo_de_producto=$($producto.Count) [$($producto -join ', ')] herramientas_de_verificacion=$($herramientas.Count) [$($herramientas -join ', ')]"
  if ($producto.Count -eq 0) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Comprobacion "A4.3 git diff --check sin errores (excluidos evidencias y gobernanza)" {
  git -C $raiz diff --check -- . ":(exclude)docs/entrega/evidencias" ":(exclude)docs/gobernanza"
  $codigoDiff = $LASTEXITCODE
  git -C $raiz diff --cached --check -- . ":(exclude)docs/entrega/evidencias" ":(exclude)docs/gobernanza"
  $codigoCached = $LASTEXITCODE
  $estado = git -C $raiz status --porcelain
  Write-Host "cambios_pendientes=$(($estado | Measure-Object).Count) diff_check=$codigoDiff diff_cached_check=$codigoCached"
  $global:codigoComprobacion = $(if ($codigoDiff -ne 0) { $codigoDiff } else { $codigoCached })
}

Comprobacion "A4.4a sin secretos en el arbol versionado ni en el historial (scan_secrets)" {
  python (Join-Path $raiz "tools\scan_secrets.py") $raiz
  $global:codigoComprobacion = $LASTEXITCODE
}

Comprobacion "A4.4b sin secretos en el historial (patrones de clave sobre git log -p)" {
  python (Join-Path $raiz "tools\auditoria\comprobar_secretos_historial.py")
  $global:codigoComprobacion = $LASTEXITCODE
}

Comprobacion "A4.5 .gitignore cubre .env, node_modules, builds y caches; nada de eso en el indice" {
  $ignorado = Get-Content (Join-Path $raiz ".gitignore")
  $faltan = @()
  foreach ($patron in @(".env", "node_modules/", ".next/", "__pycache__/", ".pytest_cache/")) {
    if (-not ($ignorado -contains $patron)) { $faltan += $patron }
  }
  $indice = git -C $raiz ls-files
  $colados = $indice | Where-Object { $_ -match "(^|/)\.env$|node_modules/|/\.next/|__pycache__|\.pytest_cache" }
  Write-Host "faltan_en_gitignore=$($faltan -join ',') en_el_indice=$($colados.Count)"
  if ($faltan.Count -eq 0 -and $colados.Count -eq 0) { $global:codigoComprobacion = 0 } else { $global:codigoComprobacion = 1 }
}

Comprobacion "A4.6 la gobernanza versionada cuadra con su manifiesto SHA-256" {
  python (Join-Path $raiz "tools\auditoria\comprobar_gobernanza.py")
  $global:codigoComprobacion = $LASTEXITCODE
}

# Se deja la pila parada al terminar.
node (Join-Path $raiz "scripts\beta_stop.mjs") | Out-Null

Add-Content -Path $log -Value ("`nResultado: $($global:fallos) comprobacion(es) FALLA") -Encoding utf8
Write-Host ""
Write-Host "Log: $log"
if ($global:fallos -gt 0) { exit 1 }
exit 0
