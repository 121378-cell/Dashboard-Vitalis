# 📱 Acceso a Vitalis Dashboard desde Dispositivos Móviles

## ✅ Estado Actual
- **Frontend**: http://localhost:5173 (Vite)
- **Backend**: http://localhost:9000 (FastAPI)
- **Túneles Ngrok**: Activos

---

## 🌍 Acceso desde Cualquier Lugar (Remoto)

### URL Pública de Vitalis:
```
https://nonpacifical-jermaine-exigently.ngrok-free.dev
```

### Instrucciones para Dispositivos Móviles:

1. **Abre tu navegador móvil** (Chrome, Safari, Edge, etc.)
2. **Ve a la URL**:
   ```
   https://nonpacifical-jermaine-exigently.ngrok-free.dev
   ```
3. **Verás una advertencia de seguridad** (es normal):
   - Haz clic en **"Continuar"** o **"Visitar sitio"**
   - Ngrok muestra esta advertencia por seguridad
4. **¡Vitalis está listo para usar!**

### Funcionalidades Disponibles desde Móvil:
- ✅ Sincronización con Garmin Connect
- ✅ Visualización de métricas de salud
- ✅ Análisis de entrenamientos
- ✅ Chat con IA (ATLAS)
- ✅ Generación de reportes en PDF

---

## 🏠 Acceso Local (Misma Red/PC)

### Desde tu PC:
```
http://localhost:5173
```

### Desde otro dispositivo en la misma red:
Obtén tu IP local:
```powershell
ipconfig
```
Busca `IPv4 Address` (ej: 192.168.x.x)

Luego accede desde túnel móvil:
```
http://192.168.x.x:5173
```

---

## 🔧 Detalles Técnicos

### Servidores Activos:
| Servicio | Puerto | Status |
|----------|--------|--------|
| Frontend (Vite) | 5173 | ✅ Corriendo |
| Backend (FastAPI) | 9000 | ✅ Corriendo |
| Ngrok Web UI | 4040 | ✅ http://127.0.0.1:4040 |

### Configuración Ngrok:
- **Protocolo**: HTTPS (seguro)
- **Región**: Europa (eu)
- **Latencia**: ~27-30ms
- **Cuenta**: Kmikc (Free Plan)

### Variables de Entorno (.env):
```
VITE_BACKEND_URL=http://localhost:9000/api/v1
FRONTEND_URL=http://localhost:5173
```

---

## 📌 Mantener Ngrok Activo

Para que Vitalis siga siendo accesible públicamente:

### ✅ Verifica que Ngrok esté corriendo:
```powershell
Get-Process ngrok
```

### Para ver estadísticas en tiempo real:
```
http://127.0.0.1:4040
```

### Si necesitas detener (y parar acceso remoto):
```powershell
Get-Process ngrok | Stop-Process -Force
```

---

## 🚀 Automatizar al Arrancar

Para iniciar todo automáticamente:

**Archivo: start_vitalis_complete.bat**
```batch
@echo off
REM Inicia Backend
start cmd /k "cd %cd% && npm run dev:backend"
REM Inicia Frontend
start cmd /k "cd %cd% && npm run dev"
REM Inicia Ngrok (después de 5 segundos)
timeout /t 5 /nobreak
ngrok start --all
```

Guarda esto como `start_vitalis_complete.bat` en la raíz del proyecto.

---

## ⚠️ Notas Importantes

1. **URL Dinámica**: Cada vez que reinicies Ngrok, obtienes una URL nueva
   - Para URL permanente: Suscríbete a Ngrok Pro

2. **Seguridad**: La URL de Ngrok es pública
   - Solo tú puedes controlar acceso desde tu PC
   - Para mayor seguridad, usa autenticación en Vitalis

3. **Tiempo de Sesión**: Sin autentificarse, la sesión puede caducar
   - Verifica que estés logueado en Vitalis

4. **Mejor Rendimiento**: Acceso local > Acceso remoto
   - Local: ~1-2ms
   - Remoto (Ngrok): ~27-30ms

---

## 📞 Solucionar Problemas

### No carga la página:
```
- Verifica que Ngrok esté corriendo
- Recarga el navegador (Ctrl+R o Cmd+R)
- Borra caché del navegador
```

### No conecta al backend:
```
- Verifica: http://localhost:9000/api/v1/docs (Swagger)
- Revisa la consola del browser (F12)
- Mira los logs del backend en terminal
```

### Lento desde remoto:
```
- Es normal (región EU a tu ubicación)
- Usa Ngrok Pro para mejor velocidad
- O accede localmente en tu red
```

---

**¡Vitalis está listo para usar desde cualquier dispositivo! 🎉**
