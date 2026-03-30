@echo off
REM =====================================================
REM Script de Reinicio Completo de Vitalis
REM =====================================================

echo.
echo ╔════════════════════════════════════════╗
echo ║  Reiniciando Vitalis Completamente    ║
echo ╚════════════════════════════════════════╝
echo.

REM Matar todos los procesos previos
echo [1/3] Matando procesos previos...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak

REM Iniciar Backend
echo [2/3] Iniciando Backend FastAPI (puerto 9000)...
cd backend
start cmd /k "title Backend FastAPI && python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload"
cd ..
timeout /t 3 /nobreak

REM Iniciar Frontend
echo [3/3] Iniciando Frontend Vite (puerto 5173)...
start cmd /k "title Frontend Vitalis && npm run dev"

echo.
echo ╔════════════════════════════════════════╗
echo ║      ✓ Vitalis está iniciando         ║
echo ╚════════════════════════════════════════╝
echo.
echo Acceso:
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:9000/api/v1
echo   Docs API:  http://localhost:9000/api/v1/docs
echo.
echo Esperando a que inicie...
timeout /t 5 /nobreak

REM Abrir navegador
start http://localhost:5173

echo ✓ Listo
