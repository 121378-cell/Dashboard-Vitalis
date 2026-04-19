@echo off
REM ============================================================================
REM   🏋️  VITALIS - ENTRENAR AHORA (ULTRA SIMPLE)
REM   Haz doble clic aquí. Punto.
REM ============================================================================

cd /d "%~dp0"

color 0A
cls
echo.
echo  ╔════════════════════════════════════════════════════════════╗
echo  ║        🏋️  VITALIS - COMPILANDO Y PREPARÁNDOSE...        ║
echo  ╚════════════════════════════════════════════════════════════╝
echo.
echo  Este script:
echo    1. Instala todas las dependencias
echo    2. Compila Angular Dashboard
echo    3. Inicia Backend FastAPI
echo    4. Inicia Frontend Vite
echo    5. Abre el navegador en http://localhost:5173
echo.
echo  ⏱️  Tiempo: ~90 segundos la primera vez, ~30 segundos después
echo.
echo  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Ejecutar PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0VITALIS_ENTRENAR_AHORA.ps1'; Read-Host 'Presiona ENTER para cerrar'"

echo.
echo  Si las ventanas se cierran aquí, revisa:
echo.
echo  1. Node instalado?: node -v
echo  2. Python instalado?: python --version
echo  3. Si hay permisos de PowerShell, ejecuta como admin:
echo     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
echo.
pause
