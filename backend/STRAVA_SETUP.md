# 🚴 Configuración de Strava OAuth2 en Atlas

## ✅ Implementación Completada

El backend ahora soporta sincronización automática con **Strava** vía OAuth2.

---

## 📋 Resumen de lo Implementado

| Componente | Estado | Archivo |
|------------|--------|---------|
| Modelo BD (Strava tokens) | ✅ | `app/models/token.py` |
| Endpoints OAuth2 | ✅ | `app/api/api_v1/endpoints/strava.py` |
| Servicio de sync | ✅ | `app/services/strava_service.py` |
| Configuración | ✅ | `app/core/config.py` |
| Migración BD | ✅ | `migrate_strava.py` |

---

## 🚀 Pasos para Activar (5 minutos)

### **PASO 1: Crear App en Strava Developer**

1. Ve a https://www.strava.com/settings/api
2. Clic en **"Create App"**
3. Completa:
   - **Application Name**: `Atlas Dashboard`
   - **Category**: `Training`
   - **Website**: `http://localhost:5173`
   - **Authorization Callback Domain**: `localhost:8001`
   - **Upload Logo** (opcional)

4. Guardar. Verás:
   - **Client ID**: `12345` (copiar)
   - **Client Secret**: `xxxxxxxx...` (copiar)

---

### **PASO 2: Configurar Variables de Entorno**

Añade a tu archivo `backend/.env`:

```env
# Strava OAuth2
STRAVA_CLIENT_ID=tu_client_id_aqui
STRAVA_CLIENT_SECRET=tu_client_secret_aqui
STRAVA_REDIRECT_URI=http://localhost:8001/api/v1/strava/callback
FRONTEND_URL=http://localhost:5173
```

---

### **PASO 3: Migrar Base de Datos**

```powershell
cd backend
python migrate_strava.py
```

**Resultado esperado:**
```
➕ Añadiendo columna: strava_access_token
➕ Añadiendo columna: strava_refresh_token
➕ Añadiendo columna: strava_expires_at
➕ Añadiendo columna: strava_athlete_id
➕ Añadiendo columna: strava_connected
✅ Migración completada
```

---

### **PASO 4: Reiniciar Backend**

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

---

### **PASO 5: Conectar Strava**

1. Abre tu dashboard: http://localhost:5173
2. Ve a **Configuración** → **Servicios**
3. Clic en **"Conectar Strava"**
4. Se abrirá Strava para autorizar
5. Acepta los permisos
6. ¡Listo! Redirigirá de vuelta al dashboard

---

## 🔌 Endpoints Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/strava/auth` | GET | Inicia OAuth2 (redirige a Strava) |
| `/api/v1/strava/callback` | GET | Callback de OAuth2 (interno) |
| `/api/v1/strava/status` | GET | Verifica si Strava está conectado |
| `/api/v1/strava/activities` | GET | Obtiene actividades recientes |
| `/api/v1/strava/sync` | POST | Sincroniza actividades → Workouts |
| `/api/v1/strava/disconnect` | POST | Desconecta Strava |

---

## 🔄 Flujo de Sincronización Automática

```
1. Garmin Connect (app) → Sync automático → Strava
2. Atlas Dashboard → POST /api/v1/strava/sync → Obtiene de Strava
3. Strava Service → Convierte → Guarda en Workouts table
```

**Para sincronizar manualmente:**
```bash
curl -X POST http://localhost:8001/api/v1/strava/sync?days=30
```

---

## 📊 Datos Sincronizados

| Campo Strava | Campo Atlas |
|-------------|-------------|
| `name` | `notes` |
| `type` (Run, Ride, etc.) | `type` (cardio/strength) |
| `moving_time` | `duration` (minutos) |
| `average_heartrate` | En `notes` |
| `distance` | En `notes` |
| `calories` | En `notes` |
| `start_date_local` | `date` |

---

## ⚙️ Configuración Avanzada

### Cambiar puertos (si es necesario):

En `backend/.env`:
```env
STRAVA_REDIRECT_URI=http://localhost:8001/api/v1/strava/callback
FRONTEND_URL=http://localhost:5173
```

**IMPORTANTE:** También actualizar en tu app de Strava Developer:
- Authorization Callback Domain: `localhost:8001`

---

## 🐛 Troubleshooting

### Error: "Strava no conectado"
- Verifica que hiciste clic en "Conectar Strava"
- Revisa que los tokens se guardaron en la BD

### Error: "Token expirado"
- El sistema intenta renovar automáticamente
- Si falla, desconecta y vuelve a conectar

### Error 401/403 de Strava
- Verifica `STRAVA_CLIENT_ID` y `STRAVA_CLIENT_SECRET`
- Asegúrate de que la app de Strava esté activa

---

## 🎯 Próximos Pasos (Opcional)

Para que sea **completamente automático**, puedes:

1. **Añadir botón en Frontend** (si no existe):
   - Ir a `src/pages/Settings.tsx` o similar
   - Añadir: `<a href="/api/v1/strava/auth">Conectar Strava</a>`

2. **Sincronización automática programada**:
   - Crear cron job que llame a `/api/v1/strava/sync` cada hora
   - O usar el auto-sync cuando el usuario abre el dashboard

---

## 📚 Documentación Strava

- [Strava API Docs](https://developers.strava.com/docs/)
- [OAuth2 Guide](https://developers.strava.com/docs/authentication/)
- [Rate Limits](https://developers.strava.com/docs/rate-limits/): 100 requests/15 min, 1000/hr

---

## ✨ ¡Listo!

Tu dashboard ahora puede:
- ✅ Recibir actividades de Garmin (vía Strava)
- ✅ Sin error 429
- ✅ Sin bloqueos
- ✅ Sincronización automática

**Nota:** Recuerda que Garmin debe estar conectado a Strava en tu teléfono para que las actividades aparezcan automáticamente.
