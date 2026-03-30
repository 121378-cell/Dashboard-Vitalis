@echo off
REM Script para iniciar Vitalis completo con Ngrok
REM Asegúrate de tener Node.js, Python y Ngrok instalados

echo.
echo ========================================
echo   Iniciando Vitalis Dashboard Completo
echo ========================================
echo.

REM Verificar que estamos en la carpeta correcta
if not exist "package.json" (
    echo Error: Este script debe ejecutarse desde la raiz del proyecto Vitalis
    pause
    exit /b 1
)

echo [1/3] Iniciando Backend FastAPI (Puerto 9000)...
start /B cmd /k "title Vitalis Backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload --app-dir backend"

echo [2/3] Iniciando Frontend Vite (Puerto 5173)...
timeout /t 2 /nobreak
start /B cmd /k "title Vitalis Frontend && npm run dev"

echo [3/3] Iniciando Ngrok (exponiendo públicamente)...
timeout /t 3 /nobreak
start /B cmd /k "title Ngrok Tunnel && ngrok start --all"

echo.
echo ========================================
echo   ✓ Vitalis está iniciando
echo ========================================
echo.
echo Acceso Local:
echo   - Frontend: http://localhost:5173
echo   - Backend Docs: http://localhost:9000/api/v1/docs
echo.
echo Acceso Remoto (después de 10s):
echo   - Abre http://127.0.0.1:4040 para ver URLs de Ngrok
echo.
echo Presiona cualquier tecla para cerrar este mensaje...
pause
