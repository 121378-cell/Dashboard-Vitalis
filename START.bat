@echo off
REM =====================================================
REM VITALIS - INICIO CON UN SOLO CLICK
REM =====================================================
REM Este script inicia TODO automáticamente:
REM - Backend FastAPI (puerto 9000)
REM - Frontend Vite (puerto 5173)
REM - Ngrok (para acceso remoto)
REM =====================================================

setlocal enabledelayedexpansion

title VITALIS Dashboard - Iniciando...

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║           VITALIS DASHBOARD - INICIANDO              ║
echo ║         Todos los servicios en un solo click         ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM ===== STEP 1: Verificar que estamos en la carpeta correcta =====
if not exist "package.json" (
    echo ❌ Error: Este script debe estar en la raíz del proyecto Vitalis
    echo.
    pause
    exit /b 1
)

REM ===== STEP 2: Matar procesos previos =====
echo [1/5] Limpiando procesos previos...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo   ✓ Completado

REM ===== STEP 3: Iniciar Backend =====
echo [2/5] Iniciando Backend FastAPI...
start "" cmd /k "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload"
timeout /t 3 /nobreak >nul
echo   ✓ Backend en puerto 9000

REM ===== STEP 4: Iniciar Frontend =====
echo [3/5] Iniciando Frontend Vite...
start "" cmd /k "npm run dev"
timeout /t 3 /nobreak >nul
echo   ✓ Frontend en puerto 5173

REM ===== STEP 5: Iniciar Ngrok (Acceso Remoto) =====
echo [4/5] Iniciando Ngrok (acceso remoto)...
start "" cmd /k "ngrok start --all"
timeout /t 2 /nobreak >nul
echo   ✓ Ngrok activo

REM ===== STEP 6: Abrir navegador =====
echo [5/5] Abriendo navegador...
timeout /t 2 /nobreak >nul
start http://localhost:5173
echo   ✓ Navegador abierto

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║         ✓ VITALIS ESTÁ FUNCIONANDO                   ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo 🌐 Acceso Local:
echo    Frontend:  http://localhost:5173
echo    Backend:   http://localhost:9000/api/v1
echo    Docs API:  http://localhost:9000/api/v1/docs
echo.
echo 🌍 Acceso Remoto (Ngrok):
echo    Busca la URL en la ventana de Ngrok
echo.
echo 💡 Para detener TODO:
echo    Cierra estas ventanas o presiona Ctrl+C en cada terminal
echo.
echo ⏱  Las ventanas se minimizarán automáticamente
echo.
pause
