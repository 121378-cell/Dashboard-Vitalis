# 🔧 Solución: Errores de Conexión en Frontend

## ✅ Estado Actual

| Servicio | Puerto | Status | URL |
|----------|--------|--------|-----|
| **Backend FastAPI** | 9000 | ✅ Corriendo | http://localhost:9000/api/v1 |
| **Frontend Vite** | 5173 | ✅ Corriendo | http://localhost:5173 |
| **Ngrok Tunnel** | - | ✅ Activo | https://nonpacifical-jermaine-exigently.ngrok-free.dev |

---

## 🔍 Problema Identificado

### Errores que veías:
```
Failed to load resource: net::ERR_CONNECTION_REFUSED
:9000/api/v1/auth/status
:9000/api/v1/settings/services
:9000/api/v1/workouts
```

### ¿Por qué ocurría?
1. Backend FastAPI **no estaba respondiendo** cuando el frontend intentaba conectar
2. Vite necesitaba **reiniciarse** para cargar las variables de ambiente (.env)
3. El frontend usaba `VITE_BACKEND_URL=http://localhost:9000/api/v1` pero Vite no lo había cargado

---

## ✅ Solución Aplicada

### 1. Configuración de Variables de Ambiente
**Archivo: `.env`**
```
VITE_BACKEND_URL=http://localhost:9000/api/v1
FRONTEND_URL=http://localhost:5173
```

### 2. Backend FastAPI
**Verifica que está escuchando:**
```bash
curl http://localhost:9000/health
# Respuesta esperada: {"status":"ok"}
```

### 3. Frontend Vite Reiniciado
Vite se reinició para cargar las variables de `.env`

---

## 🚀 Cómo Reiniciar La Aplicación Completa

### Opción 1: Script Batch (Recomendado)
```bash
.\restart_vitalis.bat
```

Esto:
1. Mata procesos previos
2. Inicia Backend en puerto 9000
3. Inicia Frontend en puerto 5173
4. Abre navegador automáticamente

### Opción 2: Manual (PowerShell)
```powershell
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# Terminal 2: Frontend
npm run dev
```

### Opción 3: Con Ngrok (Acceso Remoto)
```bash
# Terminal 1
.\restart_vitalis.bat

# Terminal 2 (después de que los servidores inicien)
ngrok start --all

# O manuel:
ngrok http 5173 --host-header=localhost
```

---

## 🧪 Verificar Que Todo Funciona

### 1. Backend Health Check
```
GET http://localhost:9000/health
Response: {"status":"ok"}
```

### 2. API Documentation
```
http://localhost:9000/api/v1/docs
```

### 3. Frontend Sin Errores
```
http://localhost:5173
```
- ✅ No debe ver errores de `ERR_CONNECTION_REFUSED`
- ✅ La interfaz debe cargar
- ✅ Los componentes deben funcionar

### 4. Monitorear Puertos
```bash
netstat -ano | findstr LISTENING | findstr ":5173\|:9000"
```

---

## 📊 Puertos Utilizados

```
5173  → Frontend Vite (React)
9000  → Backend FastAPI (Python)
4040  → Ngrok Web UI (si está activo)
```

---

## 🐛 Si Aún Hay Errores

### Error: "ERR_CONNECTION_REFUSED"
```bash
# 1. Verifica que backend está activo
curl http://localhost:9000/health

# 2. Verifica que frontend está activo
# Abre http://localhost:5173 en el navegador

# 3. Si no funciona, reinicia todo
.\restart_vitalis.bat
```

### Error: "Port already in use"
```bash
# Mata procesos que uso los puertos
taskkill /F /IM python.exe
taskkill /F /IM node.exe
Start-Sleep -Seconds 2
.\restart_vitalis.bat
```

### Error: "Cannot find module"
```bash
# Reinstala dependencias
npm install
.\restart_vitalis.bat
```

---

## 📝 Archivos Clave

- **`.env`** - Variables de ambiente (VITE_BACKEND_URL)
- **`src/App.tsx`** - Frontend principal que lee BACKEND_URL
- **`backend/app/main.py`** - Backend FastAPI
- **`restart_vitalis.bat`** - Script de reinicio rápido

---

## 🎯 Próximos Pasos

1. **Ejecuta:** `.\restart_vitalis.bat`
2. **Reabre la página** en el navegador (Ctrl+R o Cmd+R)
3. **Debería ver:** Vitalis Dashboard sin errores ✅

---

## 💡 Tips

- **Siempre reinicia Vite** después de cambiar `.env` o variables de ambiente
- **Verifica los logs** de la terminal para troubleshooting
- **Usa ATLAS.exe** si prefieres un ejecutable de una sola ventana
- **Usa Ngrok** para acceso remoto desde dispositivos móviles

---

**¿Problema resuelto? ¡Disfruta de Vitalis! 🎉**
