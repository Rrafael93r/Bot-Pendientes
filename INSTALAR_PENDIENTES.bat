@echo off
setlocal

:: Auto-elevar permisos de administrador
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set "BASEDIR=%~dp0"
cd /d "%BASEDIR%"

echo ==========================================
echo  Instalador Bot Pendientes
echo ==========================================
echo.

:: 1) Verificar Python
where python >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [ERROR] Python no esta instalado o no esta en PATH.
    echo Descargalo desde https://www.python.org/downloads/
    echo Marca "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

:: 2) Crear venv + dependencias + Chromium (dentro del venv)
echo [1/2] Configurando entorno virtual y dependencias...
powershell -ExecutionPolicy Bypass -File "%BASEDIR%setup_pendientes.ps1"
if errorlevel 1 (
    echo [ERROR] Fallo la configuracion del entorno.
    pause
    exit /b 1
)

:: 3) Programar tarea diaria 4:00 a.m. (como SYSTEM)
echo.
echo [2/2] Programando tarea diaria a las 4:00 a.m. ...
powershell -ExecutionPolicy Bypass -File "%BASEDIR%programar_pendientes.ps1"
if errorlevel 1 (
    echo [ERROR] No se pudo programar la tarea.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  Instalacion completa.
echo  El bot se ejecutara todos los dias a las 4:00 a.m.
echo ==========================================
echo.
pause
endlocal
