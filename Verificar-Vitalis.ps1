# VITALIS - Verificación Sistema (PowerShell)
# ============================================
# Script para verificar que todo está configurado correctamente

param(
    [switch]$Verbose = $false
)

# Configuración de colores
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor $Cyan
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $Cyan
    Write-Host $Title -ForegroundColor $Cyan
    Write-Host ("=" * 60) -ForegroundColor $Cyan
    Write-Host ""
}

function Test-Python {
    Write-Header "1. Verificando Python"
    
    try {
        $version = python --version 2>&1
        if ($version -match "Python (\d+\.\d+)") {
            $pfVersion = [version]$matches[1]
            if ($pfVersion -ge [version]"3.8") {
                Write-Success "Python $($matches[1]) encontrado"
                return $true
            } else {
                Write-Error "Python $($matches[1]) - Requiere 3.8+"
                return $false
            }
        }
    } catch {
        Write-Error "Python no encontrado en PATH"
        Write-Info "Descarga desde: https://www.python.org/downloads/"
        return $false
    }
}

function Test-Node {
    Write-Header "2. Verificando Node.js/npm"
    
    $nodeOk = $false
    $npmOk = $false
    
    try {
        $nodeVersion = node --version 2>&1
        Write-Info "Node: $nodeVersion"
        $nodeOk = $true
    } catch {
        Write-Error "Node.js no encontrado"
    }
    
    try {
        $npmVersion = npm --version 2>&1
        Write-Info "npm: v$npmVersion"
        $npmOk = $true
    } catch {
        Write-Error "npm no encontrado"
    }
    
    if (-not $nodeOk) {
        Write-Info "Descarga Node.js desde: https://nodejs.org/"
    }
    
    return ($nodeOk -and $npmOk)
}

function Test-EnvFile {
    Write-Header "3. Verificando Credenciales (.env)"
    
    $envPath = "backend\.env"
    
    if (-not (Test-Path $envPath)) {
        Write-Error ".env NO EXISTE"
        Write-Warning "Crea backend\.env con:"
        Write-Host @"
GROQ_API_KEY=tu_clave_groq_aqui
# O
GEMINI_API_KEY=tu_clave_gemini_aqui
# O deja en blanco para Ollama local
"@ -ForegroundColor White
        return $false
    }
    
    $content = Get-Content $envPath
    
    if ($content -match "GROQ_API_KEY=([a-zA-Z0-9_-]{10,})") {
        Write-Success "Groq API Key configurada"
        return $true
    } elseif ($content -match "GEMINI_API_KEY=([a-zA-Z0-9_-]{10,})") {
        Write-Success "Gemini API Key configurada"
        return $true
    } else {
        Write-Warning ".env existe pero sin credenciales válidas"
        Write-Info "Usará fallback a Ollama local"
        return $true
    }
}

function Test-GarminTokens {
    Write-Header "4. Verificando Tokens Garmin (.garth)"
    
    $garthPath = "backend\.garth"
    
    if (-not (Test-Path $garthPath)) {
        Write-Error ".garth NO EXISTE"
        Write-Warning "No podrá sincronizar con Garmin"
        Write-Info "Crea backend\.garth\ y copia:"
        Write-Info "  - oauth1_token.json"
        Write-Info "  - oauth2_token.json"
        return $false
    }
    
    $oauth1 = Join-Path $garthPath "oauth1_token.json"
    $oauth2 = Join-Path $garthPath "oauth2_token.json"
    
    if ((Test-Path $oauth1) -and (Test-Path $oauth2)) {
        Write-Success "Tokens Garmin encontrados"
        return $true
    } else {
        Write-Error "Faltan tokens:"
        if (-not (Test-Path $oauth1)) { Write-Error "  - oauth1_token.json" }
        if (-not (Test-Path $oauth2)) { Write-Error "  - oauth2_token.json" }
        return $false
    }
}

function Test-Database {
    Write-Header "5. Verificando Base de Datos"
    
    $dbPath = "atlas_v2.db"
    
    if (-not (Test-Path $dbPath)) {
        Write-Error "atlas_v2.db NO EXISTE"
        Write-Info "Ejecuta: python backend/init_db_script.py"
        return $false
    }
    
    $fileSize = (Get-Item $dbPath).Length / 1MB
    Write-Success "Base de datos encontrada (${fileSize:.2f} MB)"
    
    # Intentar conectar con sqlite (si sqlite3 está disponible)
    try {
        $result = sqlite3 $dbPath "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';" 2>$null
        if ($result) {
            Write-Success "Base de datos accesible"
            return $true
        }
    } catch {}
    
    return $true
}

function Test-Ports {
    Write-Header "6. Verificando Puertos Disponibles"
    
    $ports = @{
        8001 = "Backend FastAPI"
        5173 = "Frontend Vite"
        11434 = "Ollama (opcional)"
    }
    
    $allOk = $true
    
    foreach ($portInfo in $ports.GetEnumerator()) {
        $port = $portInfo.Key
        $name = $portInfo.Value
        
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $async = $tcp.BeginConnect("127.0.0.1", $port, $null, $null)
            $wait = $async.AsyncWaitHandle.WaitOne(100)
            
            if ($wait) {
                Write-Warning "Puerto $port ($name) YA EN USO"
                $allOk = $false
            } else {
                Write-Success "Puerto $port ($name) disponible"
            }
            
            $tcp.Close()
        } catch {
            Write-Success "Puerto $port ($name) disponible"
        }
    }
    
    return $allOk
}

function Test-NpmPackages {
    Write-Header "7. Verificando Paquetes npm"
    
    if (-not (Test-Path "node_modules")) {
        Write-Error "node_modules NO EXISTE"
        Write-Info "Ejecuta: npm install"
        return $false
    }
    
    $packageJson = Get-Content "package.json" | ConvertFrom-Json
    $depCount = $packageJson.dependencies.PSObject.Properties.Count
    $devDepCount = $packageJson.devDependencies.PSObject.Properties.Count
    
    Write-Success "package.json OK: $depCount deps, $devDepCount devDeps"
    Write-Success "node_modules encontrado"
    
    return $true
}

function Test-FileStructure {
    Write-Header "8. Verificando Estructura de Archivos"
    
    $backendFiles = @(
        "backend\app\main.py"
        "backend\app\core\config.py"
        "backend\auto_sync.py"
        "backend\app\api\api_v1\endpoints\ai.py"
        "backend\app\api\api_v1\endpoints\sync.py"
    )
    
    $frontendFiles = @(
        "src\App.tsx"
        "src\main.tsx"
        "src\components\Chat.tsx"
        "src\services\aiService.ts"
        "vite.config.ts"
    )
    
    $allOk = $true
    
    Write-Info "Backend:"
    foreach ($file in $backendFiles) {
        if (Test-Path $file) {
            Write-Success "  $file"
        } else {
            Write-Error "  $file NO EXISTE"
            $allOk = $false
        }
    }
    
    Write-Info "Frontend:"
    foreach ($file in $frontendFiles) {
        if (Test-Path $file) {
            Write-Success "  $file"
        } else {
            Write-Error "  $file NO EXISTE"
            $allOk = $false
        }
    }
    
    return $allOk
}

function Get-Summary {
    Write-Header "RESUMEN FINAL"
    
    $checks = @(
        ("Python", (Test-Python))
        ("Node.js/npm", (Test-Node))
        ("Credenciales IA", (Test-EnvFile))
        ("Tokens Garmin", (Test-GarminTokens))
        ("Base de Datos", (Test-Database))
        ("Puertos", (Test-Ports))
        ("Paquetes npm", (Test-NpmPackages))
        ("Estructura archivos", (Test-FileStructure))
    )
    
    Write-Host ""
    $passed = 0
    foreach ($check in $checks) {
        $name = $check[0]
        $result = $check[1]
        if ($result) {
            Write-Host "  ✓ $name" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "  ✗ $name" -ForegroundColor Red
        }
    }
    
    $total = $checks.Count
    $percentage = [math]::Round(($passed / $total) * 100, 0)
    
    Write-Host ""
    Write-Host "Resultado: $passed/$total correctos ($percentage%)" -ForegroundColor Cyan
    Write-Host ""
    
    if ($passed -eq $total) {
        Write-Host "🎉 SISTEMA COMPLETAMENTE OPERATIVO!" -ForegroundColor Green
        Write-Host "Puedes ejecutar: start_vitalis.bat" -ForegroundColor Green
        return 0
    } elseif ($passed -ge 6) {
        Write-Host "⚠️  SISTEMA PARCIALMENTE OPERATIVO" -ForegroundColor Yellow
        Write-Host "Revisa los errores arriba para terminar la configuración" -ForegroundColor Yellow
        return 1
    } else {
        Write-Host "❌ SISTEMA NO OPERATIVO" -ForegroundColor Red
        Write-Host "Requiere configuración significativa" -ForegroundColor Red
        return 2
    }
}

# Ejecutar verificación
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      VITALIS - VERIFICACIÓN DE SISTEMA COMPLETO         ║" -ForegroundColor Cyan
Write-Host "║      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$exitCode = Get-Summary
exit $exitCode
