# 🔍 VERIFICACIÓN DE VITALIS - Dashboard AI

**Fecha de Verificación:** 30 de Marzo 2026  
**Status:** ⚠️ PARCIALMENTE OPERATIVO - Requiere Configuración

---

## 📋 RESUMEN EJECUTIVO

El archivo `start_vitalis.bat` **iniciará correctamente** los servicios, pero hay **5 problemas críticos** que previenen que el sistema completo funcione:

| Componente | Status | Issue |
|---|---|---|
| Frontend (Vite React) | ✅ Arranca | Puerto 5173 correcto |
| Backend (FastAPI) | ✅ Arranca | Puerto 8001, pero faltan credenciales |
| Chat con IA | ⚠️ Solo local | Sin credenciales de Groq/Gemini |
| Sync Garmin | ❌ Requiere Setup | Falta archivo `.garth/` con tokens |
| Auto Sync | ⚠️ Manual | script `auto_sync.py` existe pero requiere credenciales |

---

## 1️⃣ VERIFICACIÓN: start_vitalis.bat

### ✅ Lo que ESTÁ CORRECTO:

```batch
@echo off
REM ✅ Obtiene ruta correctamente
set "SCRIPT_DIR=%~dp0"

REM ✅ Inicia Backend en puerto 8001
start "Vitalis Backend" cmd /k "cd /d "%SCRIPT_DIR%backend" && python -m uvicorn app.main:app --reload --port 8001"

REM ✅ Espera 2 segundos para estabilidad
timeout /t 2 /nobreak >nul

REM ✅ Inicia Frontend en puerto 5173
start "Vitalis Frontend" cmd /k "cd /d "%SCRIPT_DIR%" && npm run dev"
```

**Resultado:** El BAT creará **2 ventanas nuevas** y arrancará ambos servicios correctamente.

---

## 2️⃣ VERIFICACIÓN: Frontend → Backend Connectivity

### ✅ Configuración correcta:

**Frontend (`src/services/aiService.ts`):**
```typescript
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8001/api/v1";
```

**↓ Conecta a:**

```
POST http://localhost:8001/api/v1/ai/chat
```

**Backend (`backend/app/core/config.py`):**
```python
PORT: int = 8001
```

**⚠️ PROBLEMA 1: No hay archivo `.env`**
- Sin `VITE_BACKEND_URL` en frontend, usa default `http://localhost:8001/api/v1` ✓ (es correcto)
- Sin credenciales en backend, IA fallará

---

## 3️⃣ VERIFICACIÓN: Chat con IA

### 🔴 CRÍTICO: Faltan Credenciales

**Endpoint:** `POST /api/v1/ai/chat`

**Código intenta:**
1. ✅ Groq (modelo `llama-3.1-8b-instant`) - Sin credentials → FALLA
2. ✅ Gemini - Sin credentials → FALLA  
3. ✅ Ollama (local) - Requiere servicio en `http://localhost:11434`

**Para que funcione elegir UNO:**

```bash
# Opción A: Configurar Groq
GROQ_API_KEY=gsk_xxxxxxxxxxxx
# Obtener en: https://console.groq.com

# Opción B: Configurar Gemini  
GEMINI_API_KEY=AIzaxxxxxxxxxxxx
# Obtener en: https://aistudio.google.com/app/apikeys

# Opción C: Ollama Local (más lento pero gratuito)
# 1. Instalar Ollama: https://ollama.ai
# 2. Ejecutar: ollama run llama2
# OLLAMA_BASE_URL=http://localhost:11434
```

---

## 4️⃣ VERIFICACIÓN: Sincronización Garmin

### 🔴 CRÍTICO: Requiere Tokens Guardados

**Flujo esperado:**

```
POST /api/v1/sync/garmin
    ↓
backend/app/api/api_v1/endpoints/sync.py
    ↓
sync_garmin() → SyncService.sync_garmin_health()
    ↓
backend/auto_sync.py → connect_garmin()
    ↓
.garth/ (directorio con tokens OAuth)
```

**Para que funcione:**

```bash
1. Ir a backend/
2. Crear directorio: mkdir .garth
3. Copiar tokens (del navegador o app Garmin Connect):
   - oauth1_token.json
   - oauth2_token.json
   
Archivos necesarios:
backend/
  .garth/
    oauth1_token.json  ← Falta ❌
    oauth2_token.json  ← Falta ❌
```

**Sin estos archivos:**
```
❌ Error: "No se encontraron tokens en .garth/"
```

---

## 5️⃣ VERIFICACIÓN: Auto Sync Diario

### ⚠️ FUNCIONA pero REQUIERE

**Script:** `backend/auto_sync.py`

**Ejecución manual:**
```bash
cd backend
python auto_sync.py
```

**Genera logs en:** `backend/logs/auto_sync.log`

**Funcionalidad:**
- ✅ Sincroniza últimos 2 días (hoy + ayer)
- ✅ Actualiza perfil de atleta
- ✅ Guarda en `atlas_v2.db`

**PERO requiere:**
- `.garth/` con tokens (ver sección 4)
- Base de datos existente

---

## 🛠️ PLAN DE REPARACIÓN

### PASO 1: Crear archivo `.env` (5 min)

```bash
# backend/.env
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxx
OLLAMA_BASE_URL=http://localhost:11434
```

O usar **solo uno** (el que tengas disponible).

### PASO 2: Obtener Tokens Garmin (10-15 min)

**Opción A: Desde navegador**
1. Ir a https://connect.garmin.com
2. Abrir DevTools (F12) → Network
3. Filtrar por `oauth`
4. Buscar tokens en requests
5. Guardar como JSON en `backend/.garth/`

**Opción B: Script de autenticación** (si existe)
```bash
python backend/tests/test_garmin_connection.py
```

### PASO 3: Verificar Base de Datos

```bash
cd backend
python check_db.py
# Debe mostrar tablas: users, biometrics, workouts, training_sessions
```

### PASO 4: Ejecutar start_vitalis.bat

```bash
start_vitalis.bat
```

**Debería ver:**
```
[1/2] Iniciando Backend FastAPI en puerto 8001...
[2/2] Iniciando Frontend React + Vite...

Backend:  http://localhost:8001
Frontend: http://localhost:5173
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

Cuando todo esté configurado, verificar:

### Frontend
- [ ] Acceso a http://localhost:5173
- [ ] UI carga sin errores
- [ ] Botones de "Cargar datos" funcionan

### Chat IA
- [ ] Enviar mensaje: "¿Cuáles son mis datos?"
- [ ] Respuesta en < 30s
- [ ] Detecta solicitudes de entreno

### Sync Garmin
```bash
curl -X POST http://localhost:8001/api/v1/sync/garmin \
  -H "x-user-id: default_user" \
  -H "Content-Type: application/json"
```
- [ ] Response: `{"success": true, "health": true, "activities": true}`

### Auto Sync
```bash
cd backend && python auto_sync.py
```
- [ ] Ver logs: `backend/logs/auto_sync.log`
- [ ] Mensaje final: "✅ Sincronización completada"

---

## 📊 MATRIZ DE RESPONSABILIDADES

| Sistema | Requiere | Crítico | Solución |
|---------|----------|---------|----------|
| start_vitalis.bat | Nada | ❌ No | Ejecutar como está |
| Frontend + Backend | Python/Node | ✅ Sí | Instalar dependencias |
| Chat IA | API Key (cualquiera) | ✅ Sí | Configurar .env |
| Sync Garmin | .garth tokens | ✅ Sí | Obtener del navegador |
| Auto Sync | Garmin tokens | ⚠️ Sí | Ejecutar desde backend/ |

---

## 🚨 POTENCIALES ERRORES Y SOLUCIONES

### Error: "Address already in use 8001"
```bash
# Liberar puerto
netstat -ano | findstr 8001
taskkill /PID <PID> /F
```

### Error: "Module not found"
```bash
cd backend && pip install -r requirements.txt
cd .. && npm install
```

### Error: "Cannot find athlete profile"
```bash
# Ejecutar setup
cd backend && python init_db_script.py
```

### Error: "Groq/Gemini failed"
- Verificar credenciales en `.env`
- Usar Ollama como fallback

---

## 📝 CONCLUSIÓN

**El archivo `start_vitalis.bat`:**
- ✅ **Arranca correctamente**
- ✅ **Los puertos son correctos**
- ⚠️ **PERO el sistema completo necesita:**
  1. Credenciales de IA (`.env`)
  2. Tokens de Garmin (`.garth/`)
  3. Base de datos existente

**Recomendación:** Seguir el PLAN DE REPARACIÓN en orden para tener el sistema 100% operativo.
