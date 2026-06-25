# Despliegue del Bot Pendientes en un PC nuevo

Bot que descarga el informe **Cierre Pendientes Evento y Capita** del portal Medicar
y lo carga a la tabla MySQL `reporte_pendientes`. Se ejecuta solo, todos los días a las
**4:00 a.m.**, mediante una tarea programada de Windows que corre como **SYSTEM**
(funciona aunque nadie inicie sesión).

## Requisitos del PC nuevo
- **Windows** encendido 24/7.
- **Python 3.10+** instalado, marcando *"Add Python to PATH"* en el instalador.
  (https://www.python.org/downloads/)
- **Red:** el PC debe poder llegar a:
  - el portal `medicar.sis-colombia.com` (internet), y
  - la base de datos MySQL `10.0.1.115:3306` (red interna / VPN).
- **Reloj y zona horaria** correctos (de eso depende que dispare a las 4:00 a.m.).

## Archivos a copiar (a una carpeta, p. ej. C:\BotPendientes)
Copia SOLO estos archivos:
- `bot_pendientes.py`
- `requirements.txt`
- `.env`                      (contiene credenciales y configuración)
- `ejecutar_pendientes.bat`
- `setup_pendientes.ps1`
- `programar_pendientes.ps1`
- `INSTALAR_PENDIENTES.bat`

**NO copies** estas carpetas/archivos (se regeneran solos y son enormes o específicos del PC):
- `venv\`           (se recrea; el de otro PC NO sirve)
- `downloads\`      (archivos temporales)
- `*.log`

## Instalación (un solo paso)
1. Clic derecho en **`INSTALAR_PENDIENTES.bat`** → *Ejecutar como administrador*
   (o doble clic: pedirá permisos de administrador automáticamente).
2. Esto hace todo:
   - crea el `venv` e instala dependencias,
   - instala Chromium **dentro del venv**,
   - registra la tarea `BotPendientes_0400` (diaria, 4:00 a.m., como SYSTEM).

## Verificar que quedó bien
- **Probar la tarea ya mismo** (sin esperar a las 4 a.m.), en CMD/PowerShell como admin:
  ```
  schtasks /run /tn "BotPendientes_0400"
  ```
  Espera ~10-15 min y revisa el archivo `pendientes_actividad.log`: debe terminar en
  `EXITO: NNNNN filas cargadas` y `=== PROCESO FINALIZADO ===`.
- **Ver la tarea:** abre "Programador de tareas" de Windows y busca `BotPendientes_0400`.

## Si algo falla
- Revisa `pendientes_actividad.log` (en la misma carpeta).
- Error 403 / login: ver nota del User-Agent (ya está resuelto en el bot).
- "No se genero la descarga": el servidor tardó demasiado; el timeout es de 35 min.
- Si Chromium no arranca corriendo como SYSTEM (raro), alternativa: en
  `programar_pendientes.ps1` cambiar el `-Principal` para que corra con tu usuario
  marcando "Ejecutar aunque el usuario no haya iniciado sesión".

## Configuración editable (`.env`)
- `PENDIENTES_DIAS_ATRAS=60`  → cuántos días hacia atrás toma el filtro (fecha_final = hoy).
- `MYSQL_*`                   → conexión a la base de datos destino.
- `USUARIO_ID` / `LOGIN` / `PASSWORD` → credenciales del portal Medicar.
