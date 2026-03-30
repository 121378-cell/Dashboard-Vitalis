# 🔧 GUÍA RÁPIDA: Solución de Problemas VITALIS

## 🚀 Para Iniciar el Sistema Correctamente

### OPCIÓN 1: Script Automático (Recomendado)

```bash
# PowerShell (Windows 10+)
.\Verificar-Vitalis.ps1

# O desde Python
python verificar_vitalis.py
```

Esto verificará TODOS los componentes automáticamente y reportará qué falta.

### OPCIÓN 2: Ejecución Manual

```bash
# 1. Verificar que todo esté instalado
npm install
cd backend && pip install -r requirements.txt
cd ..

# 2. Crear .env con credenciales
cd backend
# Editar .env con una clave de API (Groq, Gemini o Ollama)

# 3. Obtener tokens Garmin (opcional para chat)
# Copiar oauth1_token.json y oauth2_token.json a backend/.garth/

# 4. Crear base de datos
python init_db_script.py

# 5. Iniciar sistema
cd ..
start_vitalis.bat
```

---

## ❌ Errores Comunes y Soluciones

### Error: "Address already in use 8001"

```powershell
# Encontrar y matar el proceso en puerto 8001
netstat -ano | findstr ":8001"
taskkill /PID <PID_NUMBER> /F

# O usar script mejorado que lo hace automáticamente
start_vitalis_v2.bat
```

---

### Error: "Module not found: fastapi"

```bash
cd backend
pip install -r requirements.txt
# O instalar manualmente
pip install fastapi sqlalchemy uvicorn pydantic python-dotenv garminconnect garth
```

---

### Error: "No such file or directory: atlas_v2.db"

```bash
cd backend
python init_db_script.py

# Debe mostrar:
# ✅ Tabla 'user' creada
# ✅ Tabla 'biometrics' creada
# ✅ Tabla 'workout' creada
# ✅ Tabla 'training_session' creada
```

---

### Error: "Groq/Gemini API failed"

```bash
# 1. Verificar que .env existe
ls backend/.env

# 2. Verificar credenciales
type backend/.env

# 3. Si .env NO EXISTE, crearlo:
# backend/.env
# GROQ_API_KEY=gsk_xxxxxxxxxxxx

# 4. Obtener claves en:
# Groq: https://console.groq.com/keys
# Gemini: https://aistudio.google.com/app/apikeys

# 5. Si todo falla, usar Ollama como fallback
#    Instalar: https://ollama.ai
#    Ejecutar: ollama run llama2
```

---

### Error: "Cannot connect to Garmin"

```bash
# Los tokens NO están en .garth/

# Opción 1: Desde navegador (Chrome/Firefox)
# 1. Ir a https://connect.garmin.com
# 2. Abrir DevTools (F12)
# 3. Ir a Network tab
# 4. Buscar en requests por "oauth"
# 5. Encontrar oauth1_token y oauth2_token
# 6. Guardar como JSON en backend/.garth/

# Opción 2: Script de autenticación (si existe)
python backend/tests/test_garmin_connection.py

# Resultado esperado:
# ✅ Conectado como: [Tu Nombre]
```

---

### Error: "Port 5173 already in use"

```powershell
# Encontrar proceso en port 5173
netstat -ano | findstr ":5173"
taskkill /PID <PID> /F

# Luego reiniciar
npm run dev
```

---

### Error: "Frontend no se conecta al Backend"

```json
// Verificar que VITE_BACKEND_URL es correcto
// En src/services/aiService.ts debe ser:
const BACKEND_URL = "http://localhost:8001/api/v1";

// Si tienes VITE_BACKEND_URL en .env frontend:
// El valor debe ser http://localhost:8001/api/v1
```

```bash
# Verificar que backend está respondiendo
curl http://localhost:8001/health
# Debe devolver: {"status":"ok"}
```

---

### Error: "Chat devuelve timeout"

```bash
# Aumentar timeout en backend/app/api/api_v1/endpoints/ai.py
# O cambiar a Groq que es más rápido:

# En backend/.env:
GROQ_API_KEY=gsk_xxxxxxxxxxxx  # Rápido (3-5s)
# En lugar de:
# GEMINI_API_KEY=xxxx           # Lento (10-20s)
```

---

### Error: "Database is locked"

```bash
# SQLite tiene la BD abierta en otro proceso

# 1. Cerrar todas las ventanas de VITALIS
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# 2. Esperar 2 segundos
timeout /t 2

# 3. Reiniciar
start_vitalis.bat
```

---

### Error: "npm: command not found"

```bash
# Node.js no está instalado en PATH

# 1. Descargar Node.js
# https://nodejs.org/

# 2. Instalar y asegurarse de agregar a PATH

# 3. Reiniciar Terminal

# 4. Verificar
node --version   # Debe mostrar: v16.x o superior
npm --version    # Debe mostrar: 8.x o superior
```

---

## ✅ Verificación Rápida de Que Todo Funciona

### 1. Frontend Carga

```javascript
// En navegador: http://localhost:5173
// Debe ver: Logo ATLAS + opciones de menú
// No debe ver errores en consola (F12)
```

### 2. Backend Responde

```bash
curl http://localhost:8001/health
# Resultado: {"status":"ok"}
```

### 3. Chat Funciona

```bash
# Desde navegador (http://localhost:5173)
# 1. Escribir mensaje: "Hola"
# 2. Esperar respuesta
# 3. Debe aparecer en < 30 segundos

# Si falla:
# - Verificar .env tiene credenciales
# - Ver console del backend para errores
```

### 4. Sync Garmin Funciona

```bash
# Desde terminal
curl -X POST http://localhost:8001/api/v1/sync/garmin \
  -H "x-user-id: default_user" \
  -H "Content-Type: application/json"

# Resultado esperado:
# {"success":true,"health":true,"activities":true}

# Si falla ("success":false):
# - Verificar que .garth/ tiene tokens
# - Revisar backend/logs/auto_sync.log
```

---

## 🔍 Logs para Debugging

```bash
# Backend logs (terminal del backend)
# Se ven en tiempo real cuando ejecutas start_vitalis.bat

# Auto Sync logs
cat backend/logs/auto_sync.log

# Frontend console (F12 en navegador)
# Ver Network tab para requests al backend
```

---

## 📊 Checklist de Startup

- [ ] Python instalado (3.8+)
- [ ] Node.js instalado (v16+)
- [ ] npm install ejecutado
- [ ] backend/requirements.txt instalados
- [ ] backend/.env creado con API key
- [ ] atlas_v2.db existe (o script init ejecutado)
- [ ] backend/.garth/ con tokens (opcional pero recomendado)
- [ ] Puertos 5173 y 8001 disponibles
- [ ] Ejecutar: start_vitalis.bat o start_vitalis_v2.bat

---

## 📞 Si Nada Funciona

```bash
# 1. Limpiar todo y reiniciar
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul

# 2. Eliminar directorios de caché
rmdir /s /q backend\__pycache__
rmdir /s /q node_modules

# 3. Reinstalar todo
cd backend && pip install -r requirements.txt
cd .. && npm install

# 4. Recrear base de datos
cd backend && python init_db_script.py
cd ..

# 5. Verificar nuevamente
python verificar_vitalis.py

# 6. Si sigue fallando, compartir output de:
# - python verificar_vitalis.py
# - curl http://localhost:8001/health (si backend corre)
# - Logs del backend (F12 en navegador)
```

---

## 🎯 RESUMEN RÁPIDO

| Problema | Comando | Resultado |
|----------|---------|-----------|
| ¿Está todo bien? | `python verificar_vitalis.py` | Muestra status completo |
| Limpiar puertos | `taskkill /F /IM python.exe` | Cierra backend |
| Instalar deps | `npm install` + `pip install -r requirements.txt` | Todas las dependencias |
| Crear BD | `python backend/init_db_script.py` | Base de datos lista |
| Iniciar | `start_vitalis.bat` | Sistema operativo |
| Probar IA | `curl -X POST http://localhost:8001/api/v1/ai/chat...` | Devuelve respuesta |
| Ver logs | Revisar ventana terminal del backend | Errores en tiempo real |

---

**Última actualización:** 30 de Marzo 2026  
**Versión:** 2.0
