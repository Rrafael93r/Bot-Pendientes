# ==========================================
# Tarea programada Bot Pendientes - diaria 4:00 a.m.
# ==========================================

# Auto-elevar a administrador si es necesario (registrar tareas lo requiere).
$esAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
            ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $esAdmin) {
    Write-Host "Solicitando permisos de administrador..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList @(
        "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    exit
}

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $BaseDir "ejecutar_pendientes.bat"

if (-not (Test-Path $BatPath)) {
    Write-Host "[ERROR] No se encontro: $BatPath" -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatPath`"" `
    -WorkingDirectory $BaseDir

# Disparador: todos los dias a las 4:00 a.m.
$trigger = New-ScheduledTaskTrigger -Daily -At 4:00AM

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 60)

# Ejecutar como SYSTEM: corre aunque nadie haya iniciado sesion (PC desatendido).
$principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Limpiar tarea previa con el mismo nombre
Unregister-ScheduledTask -TaskName "BotPendientes_0400" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BotPendientes_0400" `
    -Action $action `
    -Trigger $trigger `
    -Description "Bot Pendientes - descarga informe Cierre Pendientes y carga a MySQL (diario 4:00 a.m.)" `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Tarea 'BotPendientes_0400' creada (todos los dias 4:00 a.m.)." -ForegroundColor Green
Write-Host "Carpeta: $BaseDir" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan
