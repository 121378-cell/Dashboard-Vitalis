@echo off
REM ============================================================
REM   VITALIS - Advanced Launcher with Diagnostics
REM   Inicia Backend, Frontend y Auto Sync con verificaciones
REM ============================================================

setlocal enabledelayedexpansion

REM Configuración de colores (usa Title para output de color en CMD)
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "DB_PATH=%SCRIPT_DIR%atlas_v2.db"
set "ENV_FILE=%BACKEND_DIR%\.env"
set "GARTH_DIR=%BACKEND_DIR%\.garth"

echo.
echo ==========================================
echo    VITALIS - Advanced Dashboard AI
echo ==========================================
echo.

REM Función para mostrar mensajes
set "mode=check"

REM ============================================================
REM Verificaciones previas
REM ============================================================

echo [VERIFICANDO] Dependencias del sistema...
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado
    echo        Descarga desde: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python encontrado

REM Verificar Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js no encontrado
    echo        Descarga desde: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js encontrado

REM Verificar npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm no encontrado
    pause
    exit /b 1
)
echo [OK] npm encontrado

REM Verificar base de datos
if not exist "%DB_PATH%" (
    echo [WARNING] Base de datos no encontrada: %DB_PATH%
    echo           Ejecutando inicialización...
    cd "%BACKEND_DIR%"
    python init_db_script.py >nul 2>&1
    cd /d "%SCRIPT_DIR%"
    if not exist "%DB_PATH%" (
        echo [ERROR] No se pudo crear la base de datos
        pause
        exit /b 1
    )
    echo [OK] Base de datos creada
) else (
    echo [OK] Base de datos encontrada
)

REM Verificar .env con credenciales
if not exist "%ENV_FILE%" (
    echo.
    echo [WARNING] Archivo .env NO encontrado
    echo           Creando .env con configuración básica...
    (
        echo # VITALIS Configuration
        echo # Selecciona UNO de los siguientes providers:
        echo.
        echo # Opción 1: Groq (recomendado - rápido,gratis hasta 25 req/min)
        echo GROQ_API_KEY=gsk_XXXXXXXXXXXX
        echo.
        echo # Opción 2: Gemini (Google AI)
        echo # GEMINI_API_KEY=AIzaXXXXXXXXXX
        echo.
        echo # Opción 3: Ollama (local - requiere Ollama instalado)
        echo # OLLAMA_BASE_URL=http://localhost:11434
    ) > "%ENV_FILE%"
    echo            Guardado en %ENV_FILE%
    echo            EDITA el archivo y reemplaza las claves
    echo.
)

REM Verificar Tokens Garmin
if not exist "%GARTH_DIR%" (
    echo.
    echo [WARNING] Tokens Garmin NO encontrados
    echo           Sync con Garmin será deshabilitado
    echo           Copia oauth1_token.json y oauth2_token.json en:
    echo           %GARTH_DIR%\
    echo.
)

REM Verificar node_modules
if not exist "%SCRIPT_DIR%node_modules" (
    echo.
    echo [INFO] Instalando dependencias npm...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Error instalando npm packages
        pause
        exit /b 1
    )
)

REM Verificar dependencias Python
echo [INFO] Verificando dependencias Python...
python -c "import fastapi; import sqlalchemy; import uvicorn; import pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Instalando dependencias Python...
    cd "%BACKEND_DIR%"
    pip install -q fastapi sqlalchemy uvicorn pydantic python-dotenv
    cd /d "%SCRIPT_DIR%"
)

echo.
echo ==========================================
echo    INICIANDO VITALIS
echo ==========================================
echo.

REM Verificar puertos
echo [INFO] Verificando puertos disponibles...

REM Puerto 8001 (Backend)
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8001 " ^| findstr LISTENING') do (
    echo [WARNING] Puerto 8001 ya está en uso (PID: %%a)
    echo           Limpiando...
    taskkill /PID %%a /F >nul 2>&1
)

REM Puerto 5173 (Frontend)
for /f "tokens=5" %%a in ('netstat -ano ^| find ":5173 " ^| findstr LISTENING') do (
    echo [WARNING] Puerto 5173 ya está en uso (PID: %%a)
    echo           Limpiando...
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 1 /nobreak >nul

echo.
echo [1/3] Iniciando Backend FastAPI (puerto 8001)...
start "Vitalis Backend" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn app.main:app --reload --port 8001"

REM Esperar a que backend inicie
echo [*] Esperando a que Backend se inicialice...
timeout /t 3 /nobreak >nul

echo [2/3] Iniciando Frontend React + Vite (puerto 5173)...
start "Vitalis Frontend" cmd /k "cd /d "%SCRIPT_DIR%" && npm run dev"

REM Esperar a que frontend inicie
timeout /t 2 /nobreak >nul

echo [3/3] Sistema iniciado correctamente
echo.
echo ==========================================
echo    VITALIS OPERATIVO
echo ==========================================
echo.
echo Frontend:       http://localhost:5173
echo Backend API:    http://localhost:8001/api/v1
echo API Docs:       http://localhost:8001/docs
echo.
echo [INFO] Servicios ejecutándose en terminales separadas
echo [INFO] Cierra las ventanas o ejecuta stop_vitalis.bat para detener
echo.

REM Opcional: Iniciar Auto Sync en background
echo.
echo ¿Deseas iniciar sincronización automática con Garmin? (S/N)
set /p sync_choice="Opción: "

if /i "%sync_choice%"=="S" (
    echo [INFO] Iniciando Auto Sync...
    start "Vitalis Auto Sync" cmd /k "cd /d "%BACKEND_DIR%" && python auto_sync.py"
)

echo.
echo Presiona Enter para cerrar esta ventana...
pause >nul

endlocal
