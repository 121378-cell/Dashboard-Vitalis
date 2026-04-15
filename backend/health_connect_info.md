# Health Connect - Información de Implementación

## ¿Qué es Health Connect?

Health Connect es un **SDK de Android** desarrollado por Google que actúa como un hub central de datos de salud en el dispositivo.

### Arquitectura:
```
┌─────────────────────────────────────────────────────────────┐
│                     DISPOSITIVO ANDROID                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Garmin  │  │  Fitbit  │  │  Strava  │  │  Samsung     │  │
│  │  Connect │  │   App    │  │   App    │  │   Health     │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │             │             │               │         │
│       └─────────────┴──────┬──────┴───────────────┘         │
│                            ▼                                │
│                   ┌─────────────────┐                       │
│                   │  HEALTH CONNECT │  ← Hub central         │
│                   │     (Android)   │    en el teléfono    │
│                   └────────┬────────┘                       │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │ TU APP ANDROID  │  ← Companion app      │
│                   │   (SDK Kotlin)  │    lee datos        │
│                   └────────┬────────┘                       │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  TU BACKEND     │  ← API Python
                    │   (FastAPI)     │    recibe datos
                    └─────────────────┘
```

## Requisitos

### 1. App Android Companion
Necesitas crear una **aplicación Android** que:
- Use el SDK de Health Connect (`androidx.health.connect:connect-client`)
- Se ejecute en el mismo dispositivo que Garmin Connect
- Envíe datos a tu backend FastAPI

### 2. Permisos en Android
El usuario debe:
- Tener Android 8+ (API 26+)
- Instalar la app "Health Connect" de Google Play
- Dar permisos explícitos a tu app para leer datos
- Conectar Garmin Connect a Health Connect (en configuración de Garmin)

### 3. Datos Disponibles desde Garmin → Health Connect

| Dato | Disponible | Notas |
|------|-----------|-------|
| Pasos | ✅ Sí | Diario |
| Distancia | ✅ Sí | Caminata/carrera |
| Calorías | ✅ Sí | Activas y totales |
| Ritmo cardíaco | ✅ Sí | Puntos en tiempo real |
| Sueño | ✅ Sí | Etapas y duración |
| SpO2 | ✅ Sí | Saturación oxígeno |
| HRV | ✅ Sí | Variabilidad cardíaca |
| Actividades | ✅ Sí | Correr, ciclismo, natación |
| GPS/Ruta | ❌ No | Solo métricas, no coordenadas |
| Potencia | ❌ No | No disponible vía Health Connect |

### 4. Limitaciones Importantes

```yaml
Limitaciones de Health Connect:
  - Historial: Solo últimos 30 días por defecto
  - Permiso especial: Necesita PERMISSION_READ_HEALTH_DATA_HISTORY para +30 días
  - Disponibilidad: Solo Android (no iOS, no web)
  - Requiere app: Necesitas publicar app en Play Store
  - Aprobación Google: Requiere declarar uso de permisos sensibles
  - Frecuencia de sync: Depende de cuándo el usuario abre tu app Android
```

## Implementación Técnica

### Parte 1: App Android (Kotlin)

```kotlin
// build.gradle dependencies
implementation "androidx.health.connect:connect-client:1.1.0"

// Solicitar permisos
val permissions = setOf(
    HealthPermission.getReadPermission(StepsRecord::class),
    HealthPermission.getReadPermission(HeartRateRecord::class),
    HealthPermission.getReadPermission(SleepSessionRecord::class),
    HealthPermission.getReadPermission(DistanceRecord::class),
)

// Leer datos
coroutineScope.launch {
    val timeRangeFilter = TimeRangeFilter.between(startTime, endTime)
    
    val steps = healthConnectClient.readRecords(
        StepsRecord::class,
        ReadRecordsRequestUsingFilters(timeRangeFilter)
    )
    
    val heartRate = healthConnectClient.readRecords(
        HeartRateRecord::class,
        ReadRecordsRequestUsingFilters(timeRangeFilter)
    )
    
    // Enviar a tu backend
    sendToBackend(steps, heartRate)
}
```

### Parte 2: Backend (Python - Tu Dashboard)

```python
# Nuevo endpoint para recibir datos de Health Connect
@router.post("/health-connect/sync")
async def sync_health_connect(
    data: HealthConnectData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recibe datos de la app Android companion
    """
    # Procesar pasos
    for step_record in data.steps:
        save_steps_to_db(db, user_id=current_user.id, steps=step_record)
    
    # Procesar FC
    for hr_record in data.heart_rate:
        save_heart_rate_to_db(db, user_id=current_user.id, hr=hr_record)
    
    # Procesar sueño
    for sleep in data.sleep_sessions:
        save_sleep_to_db(db, user_id=current_user.id, sleep=sleep)
    
    return {"message": f"Synced {len(data.steps)} records"}
```

## Comparativa: Health Connect vs Opciones Anteriores

| Aspecto | Health Connect | Strava OAuth2 | Garmin API |
|---------|---------------|---------------|------------|
| **Espera de aprobación** | Sí (Google Play) | No | Sí (Garmin) |
| **Complejidad** | Alta (Android + Backend) | Media | Alta |
| **Datos de salud** | ✅ Completo | ❌ Solo actividades | ✅ Completo |
| **Tiempo de desarrollo** | 2-3 semanas | 3-5 días | 1-2 meses |
| **Usuarios soportados** | Solo Android | Web + Apps | Web + Apps |
| **Costo** | Gratis (Play Store $25 una vez) | Gratis | Gratis |

## Mi Recomendación

**Para tu caso específico:**

1. **Si tienes tiempo y quieres datos completos de salud** → Implementar Health Connect
2. **Si quieres algo rápido y funcional hoy** → Strava OAuth2
3. **Si prefieres esperar** → Dejar Garmin como está y usar wger/entradas manuales

Health Connect es la **mejor solución a largo plazo** para usuarios Android porque:
- No depende de que Garmin no bloquee APIs
- Datos en tiempo real desde el dispositivo
- Agrega múltiples fuentes (Garmin + otros wearables)

**¿Quieres que implemente Health Connect?** Requiere crear una app Android companion.
