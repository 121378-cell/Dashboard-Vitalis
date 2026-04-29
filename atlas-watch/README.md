# Atlas Watch App - Connect IQ for Garmin Forerunner 245

## Descripción
Aplicación Connect IQ para Garmin Forerunner 245/245m/255 que muestra el estado de Readiness y métricas clave del atleta desde el backend ATLAS AI Personal Trainer.

## Estructura del Proyecto
```
atlas-watch/
├── manifest.xml              # Configuración de la app, permisos, dispositivos
├── monkey.jungle             # Build configuration
├── source/
│   ├── AtlasApp.mc           # Punto de entrada, gestión del ciclo de vida
│   ├── AtlasView.mc          # UI principal (estilo watchface)
│   ├── AtlasDelegate.mc      # Manejo de inputs (incluído en AtlasView.mc)
│   └── DataManager.mc        # Fetch de datos desde el phone/backend
└── resources/
    ├── layouts/
    │   └── layout.xml        # Layout principal
    ├── strings/
    │   └── strings.xml       # Strings localizados (ENG/SPA)
    └── drawables/
        └── launcher_icon.png # Icono de la app (24x24 o 48x48 PNG)
```

## Funcionalidades

### Pantalla Principal
- **Readiness Score** - Score 0-100 con indicador circular semi-circular
- **Estado** - EXCELENTE/BUENO/MODERADO/BAJO/DESCANSO
- **Métricas Clave**:
  - HRV (Variabilidad del ritmo cardíaco) en ms
  - HR (Frecuencia cardíaca en reposo) en bpm
  - SUEÑO (Horas de sueño)
- **Recomendación** - Texto de entrenamiento para hoy
- **Alerta** - ⚠️ Badge de riesgo de sobreentrenamiento cuando readiness < 40 o carga muy alta

### Controles
- **Enter/Select** - Refrescar datos manualmente
- **Swipe Up/Down** - Refrescar datos
- **Back** - Salir de la app

### Comunicación Backend
- GET `https://atlas-vitalis-backend.fly.dev/api/v1/readiness/score`
- Headers: `x-user-id: default_user`, `Content-Type: application/json`
- Timeout: 5 segundos
- Cache persistente: Último dato disponible offline
- Auto-refresh: Cada 30 minutos

## Permisos Requeridos
- **Communications** - Internet vía conexión phone
- **Sensor** - Acceso a sensores del reloj
- **UserProfile** - Datos del usuario

## Dispositivos Soportados
- Forerunner 245 (fr245)
- Forerunner 245 Music (fr245m)
- Forerunner 255 (fr255)

## Diseño UI
- **Colores**: Escala de grises + acento amarillo (#E8FF47)
- **Tipografía**: Texto grande y legible (mínimo 18pt para números)
- **Type**: Widget (no background app - ahorra batería)
- **Gauge**: Indicador semi-circular para score de readiness

## Construcción

### Requisitos
- ConnectIQ SDK 7.x
- Java JDK 8+
- Monkey C compiler

### Build Commands
```bash
# Compilar con el SDK
cd atlas-watch
java -jar $CONNECTIQ_SDK/bin/monkeycf.jar monkey.jungle

# Ejecutar en simulador
java -jar $CONNECTIQ_SDK/bin/simulator.jar -f fr245 -a atlas.ai.trainer
```

### Deploy al Reloj
1. Compilar con ConnectIQ SDK
2. Exportar como .iq file
3. Instalar vía Garmin Connect Mobile o Garmin Express

## Integración con Backend

### API Endpoints Utilizados

#### GET /readiness/score
```json
{
  "score": 85,
  "status": "excellent",
  "recommendation": "Día óptimo para entrenamiento de alta intensidad. Tu cuerpo está en peak.",
  "components": {
    "hrv": 62.5,
    "sleep": 85.0,
    "stress": 90.0,
    "rhr": 78.0,
    "load": 75.0
  },
  "baseline": {
    "hrv_mean": 55.0,
    "hrv_std": 10.0,
    "rhr_mean": 50.0,
    "rhr_std": 5.0,
    "sleep_mean": 7.0,
    "stress_mean": 35.0,
    "days_available": 30
  },
  "overtraining_risk": false,
  "date": "2026-04-28"
}
```

### Formato de Datos
- Todos los scores: 0-100 (mayor = mejor, excepto stress)
- HRV: ms (mayor = mejor recuperación)
- HR: bpm (menor = mejor fitness)
- Sleep: horas
- Status: excellent|good|moderate|poor|rest

## Comportamiento Offline
- Si no hay red, usa último dato cacheado
- Cache persistente en storage del reloj
- Timestamp indica edad de los datos
- Refresca automáticamente cuando hay red

## Battery Optimization
- Tipo widget (no background app)
- Refresco cada 30 min (no continuo)
- Timeout 5s para requests
- Pantalla apagada = 0 consumo

## Notas de Implementación

### Vibración por Sobreentrenamiento
Cuando `overtraining_risk=true`, la app intenta vibrar:
- Pattern: 50ms on, 500ms total
- Alerta crítica para el atleta

### Gestión de Errores
- Network timeout → usar cache
- Invalid JSON → mostrar "SIN DATOS"
- HTTP error → retry con cache

### Colores por Score
- ≥ 85: Verde (#4ADE80) - Excelente
- 70-84: Amarillo (#E8FF47) - Bueno  
- 50-69: Naranja (#FB923C) - Moderado
- < 50: Rojo (#F87171) - Bajo/Descanso

## Testing

### Simulador
```bash
# Ejecutar en simulador FR245
java -jar $SDK/bin/simulator.jar -f fr245 -a atlas.ai.trainer
```

### Pruebas Manuales
1. Conexión exitosa → score mostrado
2. Timeout 5s → cache usado
3. Sin datos → "SIN DATOS"
4. Risk > 40 → badge rojo
5. Swipe/enter → refresh

## Mantenimiento

### Actualizar URL Backend
Modificar en `AtlasApp.mc`:
```monkeyc
var ATLAS_API_URL = "https://tu-backend.com/api/v1/readiness/score";
```

### Cambiar User ID
Modificar en `DataManager.mc`:
```monkeyc
var userId = "nuevo_usuario";
```

### Adjustar Timeout
Modificar en `DataManager.mc`:
```monkeyc
options.timeout = 10000; // 10 segundos
```

## Troubleshooting

### App no aparece en menú
- Verificar manifest.xml tiene productos correctos
- Reconstruir .iq y reinstalar
- Reiniciar reloj

### Datos no se actualizan
- Verificar conexión Bluetooth con phone
- Verificar phone tiene internet
- Checkear logs con `Sys.println()`

### UI cortada
- Verificar dimensiones (360x360 para fr245)
- Ajustar tamaños de fuente
- Revisar coordenadas en drawText

## Licencia
MIT - Atlas AI Personal Trainer

## Autor
ATLAS Team - 2026