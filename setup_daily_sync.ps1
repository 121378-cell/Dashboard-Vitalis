#Requires -Version 5.1
<#
.SYNOPSIS
    Configura la tarea programada de sincronización diaria de Garmin para ATLAS.

.DESCRIPTION
    Crea una tarea programada de Windows que ejecuta auto_sync.py cada día.
    - Días de entreno (Lunes, Miércoles, Viernes): 4:00 AM
    - Días de descanso (Martes, Jueves, Sábado, Domingo): 7:00 AM

.EXAMPLE
    .\setup_daily_sync.ps1
    # Crea la tarea programada con la configuración predeterminada

.NOTES
    - Debe ejecutarse como Administrador
    - Idempotente: puede ejecutarse múltiples veces
    - Requiere Python instalado y accesible en PATH

.Author: Dashboard-Vitalis Team
.Version: 1.0.0
#>

[CmdletBinding()]
param()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

$TaskName = "ATLAS-GarminDailySync"
$ScriptName = "auto_sync.py"

# ============================================================================
# DETECCIÓN DE RUTAS
# ============================================================================

Write-Host "Detectando configuración del sistema..." -ForegroundColor Cyan

# Detectar Python
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    $PythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}

if (-not $PythonPath) {
    # Intentar where.exe
    $PythonExe = (where.exe python 2>$null | Select-Object -First 1)
    if ($PythonExe) {
        $PythonPath = $PythonExe
    }
}

if (-not $PythonPath) {
    Write-Error "❌ Python no encontrado. Por favor instala Python y asegúrate de que esté en PATH."
    exit 1
}

Write-Host "✅ Python encontrado: $PythonPath" -ForegroundColor Green

# Detectar directorio del proyecto
$PSScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $PSScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$ScriptPath = Join-Path $BackendDir $ScriptName

Write-Host "📁 Proyecto: $ProjectRoot" -ForegroundColor Green
Write-Host "📁 Backend: $BackendDir" -ForegroundColor Green
Write-Host "📜 Script: $ScriptPath" -ForegroundColor Green

# Verificar que el script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Error "❌ No se encontró $ScriptName en $BackendDir"
    exit 1
}

Write-Host "✅ Script encontrado: $ScriptPath" -ForegroundColor Green

# ============================================================================
# CREAR TAREA PROGRAMADA
# ============================================================================

Write-Host "`nCreando tarea programada '$TaskName'..." -ForegroundColor Cyan

# Eliminar tarea existente si existe (idempotente)
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "⚠️  Tarea existente encontrada. Eliminando..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✅ Tarea anterior eliminada" -ForegroundColor Green
}

# Crear los triggers
# Días de entreno (Lunes, Miércoles, Viernes) a las 4:00 AM
$TrainingDays = @("Monday", "Wednesday", "Friday")
$TrainingTriggers = $TrainingDays | ForEach-Object {
    New-ScheduledTaskTrigger -Weekly -At "04:00" -DaysOfWeek $_
}

# Días de descanso (Martes, Jueves, Sábado, Domingo) a las 7:00 AM
$RestDays = @("Tuesday", "Thursday", "Saturday", "Sunday")
$RestTriggers = $RestDays | ForEach-Object {
    New-ScheduledTaskTrigger -Weekly -At "07:00" -DaysOfWeek $_
}

# Combinar todos los triggers
$AllTriggers = $TrainingTriggers + $RestTriggers

# Crear la acción
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ScriptName `
    -WorkingDirectory $BackendDir

# Configuración de la tarea
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -WakeToRun:$false

# Registrar la tarea
# Usar el usuario actual sin contraseña (solo cuando está logueado)
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $AllTriggers `
        -Settings $Settings `
        -User $CurrentUser `
        -RunLevel Limited `
        -Description "Sincronización diaria de datos Garmin para Dashboard-Vitalis ATLAS. Entrenos 4AM, Descanso 7AM." `
        -ErrorAction Stop

    Write-Host "`n✅ Tarea programada creada exitosamente!" -ForegroundColor Green
    Write-Host "`n📅 Horario:" -ForegroundColor Cyan
    Write-Host "   • Lunes, Miércoles, Viernes (ENTRENO): 04:00 AM" -ForegroundColor White
    Write-Host "   • Martes, Jueves, Sábado, Domingo (DESCANSO): 07:00 AM" -ForegroundColor White
    Write-Host "`n🔧 Detalles de la tarea:" -ForegroundColor Cyan
    Write-Host "   • Nombre: $TaskName" -ForegroundColor White
    Write-Host "   • Usuario: $CurrentUser" -ForegroundColor White
    Write-Host "   • Python: $PythonPath" -ForegroundColor White
    Write-Host "   • Directorio: $BackendDir" -ForegroundColor White
    Write-Host "   • Script: $ScriptName" -ForegroundColor White

} catch {
    Write-Error "❌ Error creando la tarea: $_"
    Write-Host "`n💡 Si el error persiste, intenta ejecutar PowerShell como Administrador." -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# VERIFICACIÓN
# ============================================================================

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
Write-Host "VERIFICACIÓN" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

# Verificar que la tarea existe
$NewTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($NewTask) {
    Write-Host "✅ Tarea '$TaskName' verificada en el Programador de tareas" -ForegroundColor Green
    
    # Mostrar próximas ejecuciones
    $NextRunTimes = ($NewTask.Triggers | ForEach-Object { 
        $_.Repetition.Interval | Out-Null
        $_.StartBoundary 
    } | Select-Object -First 5)
    
    Write-Host "`n📋 Comandos para gestionar la tarea:" -ForegroundColor Cyan
    Write-Host "   • Ver tarea:     Get-ScheduledTask -TaskName '$TaskName' | Format-List" -ForegroundColor White
    Write-Host "   • Ejecutar ahora: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "   • Detener:       Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "   • Eliminar:      Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor White
    Write-Host "   • Ver logs:      Get-Content '$BackendDir\logs\auto_sync.log' -Tail 20" -ForegroundColor White
    
    Write-Host "`n🎉 Configuración completada!" -ForegroundColor Green
    exit 0
} else {
    Write-Error "❌ No se pudo verificar la tarea creada"
    exit 1
}
