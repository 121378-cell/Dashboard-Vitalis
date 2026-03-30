# 🎯 ATLAS.exe - Guía de Compilación y Uso

## ✅ Estado Actual
**ATLAS.exe ha sido compilado exitosamente** con todas las dependencias del proyecto incluidas.

---

## 📦 ¿Qué está incluido en ATLAS.exe?

### ✓ Backend (FastAPI)
- ✅ Servidor API en puerto 8001
- ✅ Base de datos SQLite
- ✅ Integración Garmin (conectores)
- ✅ Motor de IA (ATLAS AI)
- ✅ Endpoints de Health Check

### ✓ Frontend (Vite + React)
- ✅ Interfaz de usuario TypeScript/React
- ✅ Componentes Tailwind CSS
- ✅ Servidor de desarrollo Vite en puerto 5173

### ✓ Dependencias Compiladas
- ✅ FastAPI + Uvicorn
- ✅ Pydantic v2
- ✅ SQLAlchemy
- ✅ Requests
- ✅ Google GenAI SDK
- ✅ Python 3.12.10 runtime

---

## 🚀 Cómo Usar ATLAS.exe

### Opción 1: Ejecución Simple
```bash
cd c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis
ATLAS.exe
```

El ejecutable:
1. Verifica Python y Node.js
2. Libera puertos (8001, 5173)
3. Inicia Backend FastAPI
4. Inicia Frontend Vite
5. Abre navegador automáticamente en http://localhost:5173

### Opción 2: Ejecución desde Script Batch
```batch
start_vitalis_complete.bat
```

### Opción 3: Acceso Remoto (con Ngrok)
```bash
# En terminal 1
ATLAS.exe

# En terminal 2 (después de que ATLAS esté listo)
ngrok http 5173 --host-header=localhost
```

---

## ⚙️ Configuración Técnica del ATLAS.spec

### Cambios Realizados:
1. **Rutas Corregidas**: Rutas absolutas ajustadas a tu sistema
2. **Datas Incluidos**: Backend, package.json, .env
3. **Hidden Imports**: 30+ módulos Python requeridos
4. **Optimizaciones**: UPX enabled, console mode
5. **Output**: Directorio Atlas/ en dist/

### Estructura de Compilación:
```
dist/ATLAS/
├── ATLAS.exe (ejecutable principal)
└── _internal/ (librerías y dependencias)
    ├── python312.dll
    ├── uvicorn/
    ├── fastapi/
    ├── pydantic/
    ├── sqlalchemy/
    └── ... más módulos
```

---

## 🔧 Recompilar ATLAS.exe

Si necesitas actualizar el ejecutable después de cambios:

### Método 1: Con Script de Compilación
```bash
cd c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis
.\build_atlas.ps1
```

### Método 2: Directamente con PyInstaller
```bash
cd c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis
pyinstaller ATLAS.spec --clean
```

### Método 3: Compilación Limpia
```bash
# Limpiar compilaciones anteriores
rmdir /s /q build dist

# Recompilar
pyinstaller ATLAS.spec --clean
```

---

## 📊 Información de Compilación

| Aspecto | Valor |
|--------|-------|
| **Ejecutable** | ATLAS.exe |
| **Tamaño** | ~61 MB |
| **Ubicación** | `c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis\` |
| **PyInstaller** | 6.19.0 |
| **Python** | 3.12.10 |
| **Modo** | Directorio (dist/ATLAS/) |
| **Console** | Habilitada (se ve el output) |

---

## 🐛 Solucionar Problemas

### ATLAS.exe no arranca
```
❌ Error: "System cannot find the specified path"
✓ Solución: Ejecuta desde la raíz del proyecto Vitalis
```

### Puerto 8001 en uso
```
❌ Error: "Address already in use"
✓ Solución: ATLAS.exe intenta liberar automáticamente
✓ Si persiste: netstat -ano | findstr :8001 → taskkill /PID xxxx
```

### Falta Python o Node.js
```
❌ Error: "Python not found"
✓ Solución: Instala Python 3.12+ y Node.js v20+
✓ Verifica están en PATH
```

### Frontend no carga
```
❌ Error: "Cannot find module npm"
✓ Solución: npm install (ejecuta en raíz del proyecto)
✓ Verifica: npm --version
```

---

## 💡 Tips Útiles

### 1. Ver Logs de Compilación
```bash
type build.log | more
```

### 2. Monitorear Puertos en Use
```bash
netstat -ano | findstr LISTENING
```

### 3. Actualizar Dependencias Python
```bash
pip install --upgrade -r requirements.txt
```

### 4. Acceso desde Red Local
```
Si ATLAS.exe está en tu PC:
http://<tu-ip-local>:5173
```

### 5. API Documentation (cuando ATLAS está corriendo)
```
http://localhost:8001/docs      (Swagger UI)
http://localhost:8001/redoc     (ReDoc)
```

---

## 📝 Archivo ATLAS.spec Actualizado

La configuración actual incluye:
- ✅ Rutas correctas
- ✅ Todas las dependencias
- ✅ Módulos del proyecto (app/*)
- ✅ Archivos de datos (backend, .env)
- ✅ Exclusiones innecesarias (tkinter, tests)

**Próxima compilación será más rápida** (~2-3 min vs ~5 min la primera).

---

## 🎯 Próximos Pasos

1. **Usa ATLAS.exe** para probar todo funciona
2. **Si hay cambios en el código**, recompila con `pyinstaller ATLAS.spec --clean`
3. **Distribuye ATLAS.exe** (es independiente, no necesita Python ni Node.js)
4. **Para acceso remoto**, usa Ngrok (ver ACCESO_MOVIL.md)

---

## ✨ Resumen

**ATLAS.exe está completamente funcional y listo para usar.** Incluye todo lo necesario:
- Backend FastAPI con IA integrada ✅
- Frontend React + Vite ✅
- Base de datos SQLite ✅
- Todas las dependencias compiladas ✅

**Simplemente ejecuta:** `ATLAS.exe` y ¡que disfrutes! 🚀
