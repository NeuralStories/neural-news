<#
.SYNOPSIS
  Deja neural.news listo para usarse, con **un comando** (NN-114.1).

.DESCRIPTION
 Hace, en orden y parando en el primer fallo:
    1. comprueba Python (>= 3.12) y Node (>= 20);
    2. instala el backend (editable, con extras de desarrollo);
    3. crea `.env` a partir de `.env.example` si no existe;
    4. aplica las migraciones (Alembic, nunca `create_all`);
    5. instala las dependencias de la web;
    6. ejecuta la suite de pruebas.

  NO arranca la pila: eso lo hace `scripts/start.ps1` (o el `webServer` de
  Playwright, que levanta API, worker y web por su cuenta).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
#>
[CmdletBinding()]
param(
  [switch]$SkipTests,
  [switch]$SkipWeb
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Paso([string]$mensaje) { Write-Host "`n== $mensaje" -ForegroundColor Cyan }
function Info([string]$mensaje) { Write-Host "   $mensaje" }

# --- 1. Requisitos ---------------------------------------------------------
Paso "Comprobando requisitos"
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) { throw "No se encuentra Python en el PATH. Instala Python 3.12 o superior." }
$versionPython = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ([version]$versionPython -lt [version]"3.12") {
  throw "Se necesita Python 3.12 o superior (esta máquina tiene $versionPython)."
}
Info "Python $versionPython"

$node = (Get-Command node -ErrorAction SilentlyContinue)
if (-not $node) { throw "No se encuentra Node en el PATH. Instala Node 20 o superior." }
$versionNode = (& node --version).Trim().TrimStart("v")
if ([version]$versionNode -lt [version]"20.0.0") {
  throw "Se necesita Node 20 o superior (esta máquina tiene $versionNode)."
}
Info "Node $versionNode"

# --- 2. Backend ------------------------------------------------------------
Paso "Instalando el backend (apps/api)"
Push-Location "apps\api"
try {
  & python -m pip install --upgrade pip | Out-Null
  & python -m pip install -e ".[dev]"
  if ($LASTEXITCODE -ne 0) { throw "Falló la instalación del backend." }
} finally { Pop-Location }

# --- 3. .env ---------------------------------------------------------------
Paso "Preparando la configuración (.env)"
$envFile = Join-Path $raiz ".env"
if (Test-Path $envFile) {
  Info ".env ya existe: no se toca."
} else {
  Copy-Item (Join-Path $raiz ".env.example") $envFile
  Info ".env creado a partir de .env.example. Revísalo antes de desplegar."
}

# --- 4. Migraciones --------------------------------------------------------
Paso "Aplicando las migraciones (Alembic)"
Push-Location "infra\migrations"
try {
  & python -m alembic upgrade head
  if ($LASTEXITCODE -ne 0) { throw "Falló la aplicación de las migraciones." }
} finally { Pop-Location }

# --- 5. Web ----------------------------------------------------------------
if (-not $SkipWeb) {
  Paso "Instalando la web (apps/web)"
  Push-Location "apps\web"
  try {
    & npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de la web." }
  } finally { Pop-Location }
}

# --- 6. Pruebas ------------------------------------------------------------
if (-not $SkipTests) {
  Paso "Ejecutando la suite de pruebas"
  & python -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw "Las pruebas han fallado." }
}

Write-Host "`nListo." -ForegroundColor Green
Write-Host "  Arrancar la pila:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
Write-Host "  E2E (levanta la pila solo):  cd apps\web; npm run e2e"
Write-Host "  Manual:  python -m uvicorn neuralnews.main:app --port 8000  |  python -m neuralnews.worker  |  npm run start"
