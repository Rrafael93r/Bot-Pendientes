@echo off
setlocal
set "BASEDIR=%~dp0"
cd /d "%BASEDIR%"

rem Buscar Chromium de Playwright dentro del venv (clave para correr como SYSTEM)
set "PLAYWRIGHT_BROWSERS_PATH=0"

if not exist "%BASEDIR%venv\Scripts\python.exe" (
    echo [%date% %time%] ERROR: No existe venv. Ejecuta INSTALAR_PENDIENTES.bat primero. >> "%BASEDIR%pendientes_actividad.log"
    exit /b 1
)

"%BASEDIR%venv\Scripts\python.exe" "%BASEDIR%bot_pendientes.py"
endlocal
