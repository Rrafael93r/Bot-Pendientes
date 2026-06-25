@echo off
setlocal

echo ==========================================
echo Ejecutando Bot Medicar...
echo ==========================================

rem Obtener la ruta del script actual
set "BASEDIR=%~dp0"
cd /d "%BASEDIR%"

rem Verificar si el entorno virtual existe
if not exist "%BASEDIR%venv\Scripts\python.exe" (
    echo [ERROR] No se encuentra el entorno virtual ^(carpeta 'venv'^).
    echo Esto sucede si es la primera vez que corres el bot en este PC.
    echo.
    echo Por favor, ejecuta el script de instalacion:
    echo 1. Click derecho en 'setup_pc.ps1' -^> 'Ejecutar con PowerShell'
    echo.
    pause
    exit /b 1
)

rem Ejecutar el bot usando el python del entorno virtual
echo Iniciando script de Python...
"%BASEDIR%venv\Scripts\python.exe" "%BASEDIR%bot_medicar.py"

if errorlevel 1 (
    echo.
    echo [ERROR] El bot termino con errores.
) else (
    echo.
    echo ==========================================
    echo Proceso finalizado exitosamente.
    echo ==========================================
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
endlocal