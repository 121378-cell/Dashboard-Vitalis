#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script de Reinicio Completo de Vitalis
    Reinicia Frontend, Backend y verifica conectividad

.DESCRIPTION
    Este script:
    1. Mata procesos previos (Python, Node)
    2. Inicia Backend FastAPI en puerto 9000
    3. Inicia Frontend Vite en puerto 5173
    4. Verifica que todo esté funcionando
    5. Abre el navegador

.EXAMPLE
    .\restart_vitalis.ps1
#>

param()

function Write-StatusLine {
    param(
        [string]$Message,
        [ValidateSet("Info", "Success", "Error", "Warning")]
        [string]$Type = "Info"
    )
    
    $colors = @{
        "Info"    = "Cyan"
        "Success" = "Green"
        "Error"   = "Red"
        "Warning" = "Yellow"
    }
    
    $symbols = @{
        "Info"    = "ℹ"
        "Success" = "✓"
        "Error"   = "✗"
        "Warning" = "⚠"
    }
    
    Write-Host "$($symbols[$Type]) $Message" -ForegroundColor $colors[$Type]
}

Clear-Host

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Reiniciando Vitalis Completamente    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

# [1] Matar procesos previos
Write-Host "[1/4] Deteniendo procesos previos..." -ForegroundColor White
try {
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-StatusLine "Procesos previos detenidos" "Success"
    Start-Sleep -Seconds 2
} catch {
    Write-StatusLine "No había procesos previos" "Info"
}

# [2] Iniciar Backend
Write-Host "`n[2/4] Iniciando Backend FastAPI..." -ForegroundColor White
try {
    $backendProc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--reload" `
        -WorkingDirectory "backend" -WindowStyle Minimized -PassThru
    
    Write-StatusLine "Backend iniciado (PID: $($backendProc.Id), Puerto: 9000)" "Success"
    
    # Esperar a que el backend esté listo
    Write-Host "   Esperando que el backend esté listo..." -ForegroundColor Gray
    $maxAttempts = 10
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        try {
            $health = curl.exe -s "http://localhost:9000/health" -m 1
            if ($health -like "*ok*") {
                Write-StatusLine "Backend respondiendo correctamente" "Success"
                break
            }
        } catch { }
        $attempt++
        Start-Sleep -Seconds 1
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-StatusLine "Backend tardío en responder (continuando anyway)" "Warning"
    }
} catch {
    Write-StatusLine "Error iniciando backend: $_" "Error"
    exit 1
}

# [3] Iniciar Frontend
Write-Host "`n[3/4] Iniciando Frontend Vite..." -ForegroundColor White
try {
    $frontendProc = Start-Process -FilePath "cmd" -ArgumentList "/c", "npm", "run", "dev" `
        -WorkingDirectory "." -WindowStyle Minimized -PassThru -UseNewEnvironment
    
    Write-StatusLine "Frontend iniciado (PID: $($frontendProc.Id), Puerto: 5173)" "Success"
    Start-Sleep -Seconds 3
} catch {
    Write-StatusLine "Error iniciando frontend: $_" "Error"
    exit 1
}

# [4] Verificar conectividad
Write-Host "`n[4/4] Verificando conectividad..." -ForegroundColor White

$backendOk = $false
$frontendOk = (Get-Process node -ErrorAction SilentlyContinue | Where { $_.CommandLine -like "*vite*" }) -ne $null

try {
    $health = curl.exe -s "http://localhost:9000/health" -m 2
    if ($health -like "*ok*") {
        $backendOk = $true
    }
} catch { }

Write-StatusLine "Backend: $(if ($backendOk) { 'Respondiendo' } else { 'Verificar manualmente' })" $(if ($backendOk) { "Success" } else { "Warning" })
Write-StatusLine "Frontend: $(if ($frontendOk) { 'Activo' } else { 'Verificar manualmente' })" $(if ($frontendOk) { "Success" } else { "Warning" })

# Salida final
Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║      ✓ Vitalis está iniciando        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "Acceso a la Aplicación:" -ForegroundColor Cyan
Write-Host "  🌐 Frontend:     http://localhost:5173" -ForegroundColor White
Write-Host "  📡 Backend:      http://localhost:9000/api/v1" -ForegroundColor White
Write-Host "  📚 API Docs:     http://localhost:9000/api/v1/docs" -ForegroundColor White

Write-Host "`nAbriendo navegador..." -ForegroundColor Gray
Start-Sleep -Seconds 2

try {
    Start-Process "http://localhost:5173"
} catch {
    Write-StatusLine "Abre manualmente: http://localhost:5173" "Info"
}

Write-Host "`n✓ Vitalis está listo" -ForegroundColor Green
Write-Host "  Los procesos seguirán corriendo minimizados" -ForegroundColor Gray
Write-Host "  Cierra las ventanas para detener todo`n"

Read-Host "Presiona Enter para cerrar este script"
