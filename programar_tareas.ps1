# ==========================================
# Tarea programada Bot Medicar - cada 30 min
# ==========================================

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $BaseDir "ejecutar_bot_silencioso.bat"

if (-not (Test-Path $BatPath)) {
    Write-Host "[ERROR] No se encontro: $BatPath" -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatPath`"" `
    -WorkingDirectory $BaseDir

# Disparador: cada 30 minutos, indefinidamente, comenzando hoy
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 25)

# Limpiar tareas viejas y la actual
Unregister-ScheduledTask -TaskName "BotMedicar_0500" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "BotMedicar_1630" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "BotMedicar_30min" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName "BotMedicar_30min" `
    -Action $action `
    -Trigger $trigger `
    -Description "Bot Medicar - ejecucion automatica cada 30 minutos" `
    -Settings $settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "Tarea 'BotMedicar_30min' creada (cada 30 minutos)." -ForegroundColor Green
Write-Host "Carpeta: $BaseDir" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan
