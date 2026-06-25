# Script de configuracion para el Bot Medicar en Windows

$ErrorActionPreference = "Stop"
Write-Host "--- Iniciando configuracion del entorno local ---" -ForegroundColor Cyan

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir

# 0. Detectar venv invalido (copiado de otro PC con rutas hardcoded)
$venvPython = Join-Path $BaseDir "venv\Scripts\python.exe"
$venvRoto = $false
if (Test-Path $venvPython) {
    try {
        $out = & $venvPython -c "import sys; print(sys.prefix)" 2>&1
        if ($LASTEXITCODE -ne 0 -or $out -notlike "*$BaseDir*") {
            $venvRoto = $true
        }
    } catch {
        $venvRoto = $true
    }
}

if ($venvRoto) {
    Write-Host "Detectado venv invalido (rutas de otro PC). Eliminando..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force (Join-Path $BaseDir "venv")
}

# 1. Crear entorno virtual si no existe
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual (venv)..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: No se pudo crear el venv. Verifica que Python este instalado." -ForegroundColor Red
        exit 1
    }
}

# 2. Actualizar pip
Write-Host "Actualizando pip..."
& "$BaseDir\venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo actualizando pip." -ForegroundColor Red
    exit 1
}

# 3. Instalar dependencias
Write-Host "Instalando dependencias desde requirements.txt..."
& "$BaseDir\venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo instalando dependencias." -ForegroundColor Red
    exit 1
}

# 4. Instalar navegadores de Playwright
Write-Host "Instalando navegadores de Playwright (Chromium)..."
& "$BaseDir\venv\Scripts\python.exe" -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fallo instalando Chromium de Playwright." -ForegroundColor Red
    exit 1
}

Write-Host "--- Configuracion completada con exito ---" -ForegroundColor Green
