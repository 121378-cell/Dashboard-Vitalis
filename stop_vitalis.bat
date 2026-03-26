@echo off
echo ==========================================
echo    DETENIENDO VITALIS - Dashboard AI
echo ==========================================
echo.

REM Matar procesos de uvicorn en puerto 8001
echo [1/2] Cerrando Backend (Puerto 8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001') do (
    taskkill /PID %%a /F 2>nul
    echo    Proceso Python/uvicorn terminado (PID: %%a)
)

REM Matar procesos de Node/vite en puerto 5173
echo [2/2] Cerrando Frontend (Puerto 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173') do (
    taskkill /PID %%a /F 2>nul
    echo    Proceso Node/vite terminado (PID: %%a)
)

REM Tambien buscar por nombre de proceso como fallback
taskkill /F /IM "uvicorn.exe" 2>nul
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq Vitalis Backend*" 2>nul
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq Vitalis Frontend*" 2>nul

echo.
echo ==========================================
echo    VITALIS DETENIDO
echo ==========================================
pause
