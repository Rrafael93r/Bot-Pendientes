# Configuracion del entorno para el Bot Pendientes en un PC nuevo.
# Recrea el venv, instala dependencias e instala Chromium DENTRO del venv
# (PLAYWRIGHT_BROWSERS_PATH=0) para que la tarea programada pueda correr
# como SYSTEM aunque nadie haya iniciado sesion.

$ErrorActionPreference = "Stop"
Write-Host "--- Configurando entorno del Bot Pendientes ---" -ForegroundColor Cyan

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir

# Instalar Chromium dentro del paquete (venv), no en el perfil del usuario.
$env:PLAYWRIGHT_BROWSERS_PATH = "0"

# 0. Detectar venv invalido (copiado de otro PC con rutas hardcoded)
$venvPython = Join-Path $BaseDir "venv\Scripts\python.exe"
$venvRoto = $false
if (Test-Path $venvPython) {
    try {
        $out = & $venvPython -c "import sys; print(sys.prefix)" 2>&1
        if ($LASTEXITCODE -ne 0 -or $out -notlike "*$BaseDir*") { $venvRoto = $true }
    } catch { $venvRoto = $true }
}
if ($venvRoto) {
    Write-Host "Detectado venv invalido (de otro PC). Eliminando..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force (Join-Path $BaseDir "venv")
}

# 1. Verificar Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "ERROR: Python no esta instalado o no esta en PATH." -ForegroundColor Red
    Write-Host "Instalalo desde https://www.python.org/downloads/ y marca 'Add Python to PATH'." -ForegroundColor Red
    exit 1
}

# 2. Crear venv si no existe
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual (venv)..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: no se pudo crear el venv." -ForegroundColor Red; exit 1 }
}

# 3. pip + dependencias
Write-Host "Actualizando pip e instalando dependencias..."
& "$BaseDir\venv\Scripts\python.exe" -m pip install --upgrade pip
& "$BaseDir\venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: fallo instalando dependencias." -ForegroundColor Red; exit 1 }

# 4. Chromium DENTRO del venv
Write-Host "Instalando Chromium de Playwright dentro del venv..."
& "$BaseDir\venv\Scripts\python.exe" -m playwright install chromium
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: fallo instalando Chromium." -ForegroundColor Red; exit 1 }

Write-Host "--- Entorno configurado correctamente ---" -ForegroundColor Green
