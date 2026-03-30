#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script de Compilación de ATLAS.exe
    Compila el proyecto Vitalis a un ejecutable independiente con PyInstaller

.DESCRIPTION
    Este script:
    1. Verifica PyInstaller está instalado
    2. Verifica ATLAS.spec existe
    3. Limpia compilaciones anteriores
    4. Compila con PyInstaller
    5. Copia ATLAS.exe a la raíz del proyecto

.EXAMPLE
    .\build_atlas.ps1
#>

param()

function Write-Status {
    param(
        [string]$Message,
        [ValidateSet("Info", "Success", "Error", "Warning")]
        [string]$Status = "Info"
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
    
    Write-Host "$($symbols[$Status]) $Message" -ForegroundColor $colors[$Status]
}

Clear-Host

Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ATLAS.exe - Compilación Automática   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Cyan

# [1] Verificar PyInstaller
Write-Host "[1/5] Verificando PyInstaller..." -ForegroundColor White
$pyinstallerVersion = pyinstaller --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Status "PyInstaller $pyinstallerVersion encontrado" "Success"
} else {
    Write-Status "PyInstaller no está instalado" "Error"
    Write-Status "Instala con: pip install pyinstaller" "Warning"
    Read-Host "Presiona Enter para salir"
    exit 1
}

# [2] Verificar ATLAS.spec
Write-Host "`n[2/5] Verificando ATLAS.spec..." -ForegroundColor White
if (-Not (Test-Path "ATLAS.spec")) {
    Write-Status "ATLAS.spec no encontrado" "Error"
    Write-Status "Asegúrate de estar en la raíz del proyecto" "Warning"
    Read-Host "Presiona Enter para salir"
    exit 1
}
Write-Status "ATLAS.spec encontrado" "Success"

# [3] Limpiar compilaciones anteriores
Write-Host "`n[3/5] Limpiando compilaciones anteriores..." -ForegroundColor White
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Status "Directorio build limpiado" "Success"
}
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Status "Directorio dist limpiado" "Success"
}

# [4] Compilar
Write-Host "`n[4/5] Compilando ATLAS.exe..." -ForegroundColor White
Write-Host "   Esto puede tomar 3-5 minutos..." -ForegroundColor Gray

$buildLog = "build.log"
pyinstaller ATLAS.spec --clean | Out-File -FilePath $buildLog -Encoding UTF8

if ($LASTEXITCODE -eq 0) {
    Write-Status "Compilación completada" "Success"
} else {
    Write-Status "Error durante la compilación" "Error"
    Write-Status "Revisa build.log para más detalles" "Warning"
    & notepad $buildLog
    Read-Host "Presiona Enter para salir"
    exit 1
}

# [5] Copiar a raíz
Write-Host "`n[5/5] Copiando ATLAS.exe a raíz del proyecto..." -ForegroundColor White
$sourceExe = "dist\ATLAS\ATLAS.exe"
$destExe = "ATLAS.exe"

if (Test-Path $sourceExe) {
    Copy-Item -Path $sourceExe -Destination $destExe -Force
    $size = (Get-Item $destExe).Length / 1MB
    Write-Status "ATLAS.exe copiado exitosamente ($([Math]::Round($size, 1)) MB)" "Success"
} else {
    Write-Status "ATLAS.exe no se encontró en dist\ATLAS\" "Error"
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Resumen final
Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✓ Compilación Exitosa               ║" -ForegroundColor Green
Write-Host "║   Ejecutable: ATLAS.exe                ║" -ForegroundColor Green
Write-Host "║   Tamaño: ~60 MB                       ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Ejecuta: .\ATLAS.exe" -ForegroundColor White
Write-Host "   2. Se abrirá automáticamente en el navegador" -ForegroundColor White
Write-Host ""

Read-Host "Presiona Enter para cerrar"
