@echo off
REM =====================================================
REM Script de Compilación de ATLAS.exe
REM Compila el proyecto completo a un ejecutable
REM =====================================================

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════╗
echo ║   ATLAS.exe - Compilación Automática   ║
echo ╚════════════════════════════════════════╝
echo.

REM Verificar que PyInstaller esté instalado
echo [1/5] Verificando PyInstaller...
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo   ❌ Error: PyInstaller no está instalado
    echo   Instala con: pip install pyinstaller
    pause
    exit /b 1
)
echo   ✓ PyInstaller encontrado

REM Verificar ATLAS.spec
echo [2/5] Verificando ATLAS.spec...
if not exist "ATLAS.spec" (
    echo   ❌ Error: ATLAS.spec no encontrado
    echo   Asegúrate de estar en la raíz del proyecto
    pause
    exit /b 1
)
echo   ✓ ATLAS.spec encontrado

REM Limpiar compilaciones anteriores
echo [3/5] Limpiando compilaciones anteriores...
if exist "build" (
    rmdir /s /q build >nul 2>&1
    echo   ✓ Directorio build limpiado
)
if exist "dist" (
    rmdir /s /q dist >nul 2>&1
    echo   ✓ Directorio dist limpiado
)

REM Compilar
echo [4/5] Compilando ATLAS.exe...
echo   Esto puede tomar 3-5 minutos...
pyinstaller ATLAS.spec --clean
if errorlevel 1 (
    echo.
    echo   ❌ Error durante la compilación
    echo   Revisa el log para más detalles
    pause
    exit /b 1
)
echo   ✓ Compilación completada

REM Copiar a raíz
echo [5/5] Copiando ATLAS.exe a raíz del proyecto...
if exist "dist\ATLAS\ATLAS.exe" (
    copy "dist\ATLAS\ATLAS.exe" "ATLAS.exe" >nul
    echo   ✓ ATLAS.exe copiado exitosamente
) else (
    echo   ❌ Error: ATLAS.exe no se encontró en dist\ATLAS\
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════╗
echo ║   ✓ Compilación Exitosa               ║
echo ║   Ejecutable: ATLAS.exe                ║
echo ║   Tamaño: ~60 MB                       ║
echo ╚════════════════════════════════════════╝
echo.
echo Próximos pasos:
echo   1. Ejecuta: ATLAS.exe
echo   2. Se abrirá automáticamente en el navegador
echo.

pause
