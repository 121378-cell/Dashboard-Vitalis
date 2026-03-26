@echo off
echo ==========================================
echo    ARRANCANDO VITALIS - Dashboard AI
echo ==========================================
echo.

REM Obtener la ruta del script
set "SCRIPT_DIR=%~dp0"

REM Abrir terminal para Backend (Puerto 8001)
echo [1/2] Iniciando Backend FastAPI en puerto 8001...
start "Vitalis Backend" cmd /k "cd /d "%SCRIPT_DIR%backend" && python -m uvicorn app.main:app --reload --port 8001"

REM Esperar un momento para que el backend empiece
timeout /t 2 /nobreak >nul

REM Abrir terminal para Frontend (Puerto 5173)
echo [2/2] Iniciando Frontend React + Vite...
start "Vitalis Frontend" cmd /k "cd /d "%SCRIPT_DIR%" && npm run dev"

echo.
echo ==========================================
echo    VITALIS ARRANCADO!
echo ==========================================
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:5173
echo.
echo Usa stop_vitalis.bat para cerrar los servicios
echo.
pause
