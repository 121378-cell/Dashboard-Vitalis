<#
.SYNOPSIS
    Script todo-en-uno de arranque para Dashboard-Vitalis.
.DESCRIPTION
    - Mata procesos Node.js y Python que bloquean puertos críticos.
    - Verifica puertos libres y reinicia servicios si es necesario.
    - Inicia o reinicia Backend FastAPI y Frontend Vite.
    - Renombra server.ts conflictivo a .disabled.
    - Muestra resumen final de URLs y estado.
#>

# -------------------------
# Funciones
# -------------------------

function Stop-NodePythonProcesses {
    Write-Host "[INFO] Comprobando procesos Node.js y Python..." -ForegroundColor Cyan
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue        

    if ($nodeProcesses) {
        $nodeProcesses | Stop-Process -Force
        Write-Host "[✅] Node.js detenido" -ForegroundColor Green
    }

    if ($pythonProcesses) {
        $pythonProcesses | Stop-Process -Force
        Write-Host "[✅] Python detenido" -ForegroundColor Green
    }

    if (-not $nodeProcesses -and -not $pythonProcesses) {
        Write-Host "[INFO] No se encontraron procesos Node.js o Python" -ForegroundColor Yellow
    }
}

function CheckPorts {
    param([int[]]$Ports)
    $portStatus = @{}
    foreach ($port in $Ports) {
        $occupied = netstat -ano | findstr ":$port"
        if ($occupied) {
            Write-Host "[⚠️] Puerto $port ocupado" -ForegroundColor Red
            $portStatus[$port] = $false
        } else {
            Write-Host "[✅] Puerto $port libre" -ForegroundColor Green
            $portStatus[$port] = $true
        }
    }
    return $portStatus
}

function Disable-ServerTS {
    $serverPath = Join-Path -Path (Get-Location) -ChildPath "server.ts"        
    if (Test-Path $serverPath) {
        Rename-Item -Path $serverPath -NewName "server.ts.disabled"
        Write-Host "[✅] server.ts renombrado a server.ts.disabled para evitar conflictos" -ForegroundColor Green
    }
}

function Start-Backend {
    $backendPath = Join-Path -Path (Get-Location) -ChildPath "backend/app/main.py"
    if (-not (Test-Path $backendPath)) {
        Write-Host "[❌] backend/app/main.py no encontrado. Backend FastAPI no se inicia" -ForegroundColor Red
        return
    }

    # Comprobar si ya hay un proceso uvicorn corriendo
    $existing = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $null -ne ($_ | Select-String -Pattern "uvicorn")
    }
    if ($existing) {
        $existing | Stop-Process -Force
        Write-Host "[INFO] Backend FastAPI reiniciado" -ForegroundColor Cyan
    }

    # Cambiar al directorio backend y ejecutar uvicorn desde allí
    $backendDir = Join-Path -Path (Get-Location) -ChildPath "backend"
    Start-Process powershell -ArgumentList "cd `"$backendDir`"; uvicorn app.main:app --reload --port 8001" -NoNewWindow
    Start-Sleep -Seconds 3
    Write-Host "[✅] Backend FastAPI iniciado en http://localhost:8001" -ForegroundColor Green
}

function Start-Frontend {
    # Comprobar si npm está corriendo con Vite
    $existing = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object {
        $null -ne ($_ | Select-String -Pattern "server.ts")
    }
    if ($existing) {
        $existing | Stop-Process -Force
        Write-Host "[INFO] Frontend Vite reiniciado" -ForegroundColor Cyan
    }

    Write-Host "[INFO] Iniciando Frontend Vite en puerto 5173..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "npm run dev" -NoNewWindow
    Start-Sleep -Seconds 3
    Write-Host "[✅] Frontend Vite iniciado en http://localhost:5173" -ForegroundColor Green
}

# -------------------------
# Script Principal
# -------------------------

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   ARRANCANDO DASHBOARD-VITALIS" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Cerrar procesos Node.js y Python
Stop-NodePythonProcesses
Write-Host ""

# 2. Verificar puertos críticos
$criticalPorts = @(3000, 8001, 5173)
Write-Host "[INFO] Verificando puertos..." -ForegroundColor Cyan
$ports = CheckPorts -Ports $criticalPorts
Write-Host ""

# 3. Manejar server.ts conflictivo
Disable-ServerTS
Write-Host ""

# 4. Iniciar o reiniciar servicios
Start-Backend
Start-Frontend
Write-Host ""

# 5. Resumen final
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   DASHBOARD-VITALIS LISTO PARA USAR 🚀" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[INFO] Backend FastAPI:  http://localhost:8001"
Write-Host "[INFO] API Docs:           http://localhost:8001/docs"
Write-Host "[INFO] Frontend Vite:      http://localhost:5173"
Write-Host "[INFO] WebSocket:          ws://localhost:8001/api/v1/ws/readiness"
Write-Host ""