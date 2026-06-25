@echo off
setlocal
set "BASEDIR=%~dp0"
cd /d "%BASEDIR%"

if not exist "%BASEDIR%venv\Scripts\python.exe" (
    echo [%date% %time%] ERROR: No existe venv. Ejecuta INSTALAR.bat primero. >> "%BASEDIR%reporte_actividad.log"
    exit /b 1
)

"%BASEDIR%venv\Scripts\python.exe" "%BASEDIR%bot_medicar.py"
endlocal
