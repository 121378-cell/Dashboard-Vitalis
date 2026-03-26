# 📊 INFORME DE ANÁLISIS - DASHBOARD VITALIS
**Generado por: VITALIS CODE ANALYZER**  
**Fecha: 2026-03-26**  
**Versión analizada: v2.0**

---

## 1. 🧾 VISIÓN GENERAL

### Propósito de la Aplicación
**Dashboard-Vitalis** es una plataforma de entrenamiento personal con IA (ATLAS AI Coach) que:
- Recoge datos biométricos de wearables (Garmin, etc.)
- Calcula un "Readiness Score" personalizado (0-100)
- Ofrece chat con IA contextualizada para recomendaciones de entrenamiento
- Gestiona documentos PDF (planes, análisis)
- Sincroniza con múltiples fuentes de datos (Garmin, Wger, Hevy)

### Tipo de Sistema
- **Dashboard biométrico en tiempo real**
- **API REST + WebSockets**
- **Aplicación de entrenamiento personal con IA**
- **Sistema de análisis predictivo** (readiness scoring)

### Tecnologías Usadas
| Capa | Tecnología |
|------|------------|
| **Backend** | FastAPI (Python 3.12), SQLAlchemy, SQLite |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **Tiempo Real** | WebSockets nativos (FastAPI) |
| **AI/LLM** | Integración con Groq, OpenAI, Anthropic |
| **Wearables** | Garmin Connect API (via garminconnect) |
| **Estilo** | Material Design 3, Framer Motion |

---

## 2. 🏗️ ARQUITECTURA

### Estructura de Carpetas
```
Dashboard-Vitalis/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/api_v1/        # Endpoints REST
│   │   │   ├── endpoints/     # auth, biometrics, workouts, readiness, ai, sync
│   │   │   └── api.py         # Router aggregation
│   │   ├── core/              # Config + Readiness Engine v1.0 + v2.0
│   │   ├── db/                # SQLAlchemy models + session
│   │   ├── models/            # User, Biometrics, Workout, Token
│   │   ├── services/          # SyncService, AnalyticsService
│   │   └── main.py            # FastAPI app entry
│   └── .env                   # Config local
├── src/                       # React Frontend
│   ├── components/            # BiometricsWidget, Chat, ProfileForm, etc.
│   ├── services/              # aiService.ts, API clients
│   ├── types.ts               # TypeScript interfaces
│   └── App.tsx                # Main app component
├── server.ts                  # Node.js server opcional (desactivado)
├── start_vitalis.bat          # Script de arranque automatizado
└── atlas_v2.db               # Base de datos SQLite (450 días de datos)
```

### Separación de Responsabilidades
✅ **Bien diseñado:**
- Backend: Lógica de negocio en `services/`, API en `endpoints/`, modelos separados
- Frontend: Componentes modulares, servicios de API desacoplados
- Datos: SQLAlchemy ORM con migraciones implícitas

⚠️ **Mejorable:**
- Duplicación de lógica de readiness entre `analytics_service.py` y `readiness_engine.py`
- WebSocket manager en archivo separado pero no integrado completamente

### Flujo de Datos
```
Garmin API → SyncService → SQLite → FastAPI API → React Frontend
                                    ↓
                              WebSocket (realtime updates)
                                    ↓
                              AI Service (Groq/Anthropic)
```

---

## 3. 🔌 BACKEND

### Framework: FastAPI
- **Puerto**: 8001 (configurado en `.env`)
- **Database**: SQLite (`atlas_v2.db`)
- **CORS**: Configurado para permitir `localhost:5173`

### Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/auth/garmin/login` | POST | Autenticación con credenciales Garmin |
| `/api/v1/auth/status` | GET | Estado de conexión Garmin |
| `/api/v1/biometrics/` | GET | Datos biométricos del día (con readiness) |
| `/api/v1/workouts/` | GET | Lista de entrenamientos sincronizados |
| `/api/v1/readiness` | GET | **Readiness Score calculado** |
| `/api/v1/readiness/history` | GET | Historial de scores con tendencias |
| `/api/v1/readiness/calculate` | POST | Calcular score con datos manuales |
| `/api/v1/sync/garmin` | POST | Sincronización manual Garmin |
| `/api/v1/ai/chat` | POST | Chat con IA contextualizada |
| `/api/v1/ws/readiness` | WS | **WebSocket tiempo real** |

### Servicios Internos

#### 1. **SyncService** (`app/services/sync_service.py`)
- Sincroniza datos Garmin (health + actividades)
- Soporta Wger y Hevy
- Manejo de sesiones OAuth2
- **Problema**: Token management con `garth` puede fallar si `token_dir=None`

#### 2. **AnalyticsService** (`app/services/analytics_service.py`)
- Calcula ACWR (Acute:Chronic Workload Ratio)
- Baselines de HRV y RHR
- Readiness score básico
- **Duplicación**: Lógica similar a `readiness_engine.py`

#### 3. **ReadinessEngine** (`app/core/readiness_engine.py`) ⭐
- **Motor principal del sistema**
- Fórmula ponderada:
  - Sueño: 30%
  - Recuperación (HRV): 25%
  - Estrés: 20%
  - Actividad: 15%
  - FC Baseline: 10%
- Baselines personales calculados del histórico
- Recomendaciones accionables

#### 4. **ReadinessAdaptive** (`app/core/readiness_adaptive.py`) ⭐ PRO
- Perfiles de atleta: STRENGTH, ENDURANCE, HYBRID, RECREATIONAL
- Detección de overreaching personalizada
- Predicciones futuras de readiness
- Cálculo de sueño óptimo por usuario

---

## 4. 🎨 FRONTEND

### Framework: React + Vite
- **Puerto**: 5173 (Vite default)
- **Build tool**: Vite con HMR
- **Estilos**: Tailwind CSS con Material Design 3 tokens

### Arquitectura de Componentes

```
App.tsx (Main Container)
├── Sidebar (Vitalis Widget)
│   ├── BiometricsWidget → Métricas + Readiness Score
│   ├── Quick Actions → Prompts predefinidos para IA
│   └── Sync Status → Estado Garmin/Wger/Hevy
├── Main Content (Tab Navigation)
│   ├── Chat → Interface IA con contexto biométrico
│   ├── Profile → Formulario atleta
│   ├── Docs → Upload y análisis PDF
│   └── Setup → Configuración servicios
```

### Consumo de API
- **Cliente**: Axios con base URL desde `VITE_BACKEND_URL`
- **Headers**: `x-user-id: default_user` para identificación
- **Polling**: Auto-sync cada 5 minutos (`setInterval(fetchBiometrics, 5*60*1000)`)
- **No WebSocket consumer implementado aún** en frontend

### Estado Global
- **No Redux/Zustand**: Estado local con `useState`
- **Prop drilling**: Moderado, manejable para escala actual
- **Cache**: Ninguno explícito (podría beneficiarse de React Query)

### Componentes Clave

#### **BiometricsWidget.tsx**
- Visualiza 8 métricas: FC, HRV, Sueño, Estrés, SpO2, Pasos, Calorías, Respiración
- **Readiness Score**: Barra de progreso color-coded (rojo/naranja/verde)
- **Tendencias**: Flechas comparando con baseline personal
- **Alertas**: Badge de sobreentrenamiento si `overtraining=true`
- **Data Source Indicator**: REAL (Garmin) vs CACHÉ vs DEMO

#### **Chat.tsx**
- Interface conversacional con la IA
- System prompt enriquecido con:
  - Perfil del atleta (nombre, objetivo, experiencia)
  - Readiness actual
  - Métricas biométricas (FC, HRV, estado)
  - Últimos 5 entrenamientos
  - Documentos analizados
- Quick Actions predefinidas:
  - "Análisis Hoy"
  - "Riesgo Lesión"
  - "Plan Semanal"
  - "Nutrición"

---

## 5. ⚡ TIEMPO REAL (WebSockets)

### Implementación Backend
**Archivo**: `app/api/api_v1/endpoints/readiness_ws.py`

#### ConnectionManager
- Gestiona múltiples conexiones por usuario
- Cache de último score por usuario
- Broadcast eficiente

#### Eventos WebSocket
| Evento | Descripción | Trigger |
|--------|-------------|---------|
| `initial` | Score actual al conectar | Conexión cliente |
| `readiness_update` | Score recalculado | Cambio >2 puntos o cambio de status |
| `status_change` | Cambio low→medium→high | Transición de estado |
| `pong` | Heartbeat | Ping del cliente |

#### Integración en Sincronización
```python
# Después de sync_garmin_health():
from app.api.api_v1.endpoints.readiness_ws import notify_readiness_update
await notify_readiness_update(user_id, db)
```

### Frontend WebSocket
⚠️ **NO IMPLEMENTADO AÚN** en React
- La API existe y está lista
- Falta componente `useWebSocket` hook
- Falta UI de "Conectado en tiempo real"

---

## 6. 📊 DATOS BIOMÉTRICOS

### Qué Datos Se Manejan

| Métrica | Fuente | Unidad | Frecuencia |
|---------|--------|--------|------------|
| **Heart Rate** | Garmin | bpm | Diaria (reposo) |
| **HRV** | Garmin | ms | Variable (no FR245) |
| **SpO2** | Garmin | % | Nocturna/spot |
| **Stress** | Garmin | 0-100 | Continua |
| **Steps** | Garmin | count | Diaria |
| **Sleep** | Garmin | horas | Diaria |
| **Calories** | Garmin | kcal | Diaria |
| **Respiration** | Garmin | rpm | Nocturna |
| **Workouts** | Garmin/Wger/Hevy | diversos | Por sesión |

### Procesamiento de Datos

#### Normalización
✅ **Bien hecho:**
- Todos los scores se normalizan a 0-100
- Baselines personales vs población (más preciso)
- Z-score implícito en detección de anomalías

⚠️ **Limitaciones:**
- FR245 no mide HRV continuo (limita cálculo de recuperación)
- Sueño: solo duración, no fases de sueño (Garmin lo calcula pero no siempre expuesto)

### Almacenamiento

**Tabla `biometrics`:**
```sql
id | user_id | date | data (JSON) | source | timestamp
```

**Ejemplo de JSON almacenado:**
```json
{
  "heartRate": 48,
  "hrv": null,
  "stress": 36,
  "steps": 17414,
  "sleep": 6.4,
  "spo2": 92,
  "calories": 0,
  "respiration": 14
}
```

---

## 7. 🔗 INTEGRACIONES

### Garmin Connect
**Librería**: `garminconnect` + `garth` para token management

#### Flujo de Autenticación
1. Usuario introduce email/password en frontend
2. Backend usa `Garmin(email, password).login()`
3. Tokens guardados en `~/.garth/` (OAuth1 + OAuth2)
4. Sesión reutilizable hasta expiración

#### Datos Sincronizados
- **Health**: Heart rate, sleep, stress, steps, spo2, respiration, vo2max
- **Activities**: Running, cycling, strength, etc.
- **Métricas avanzadas**: Training status, recovery time, HRV status

#### Frecuencia
- Manual: Botón "Sincronizar Todo"
- Background: Cada 5 minutos (polling en frontend)
- **No hay webhook/push de Garmin** (limitación de API)

### Wger Workout Manager
- API key-based
- Sincroniza biblioteca de ejercicios
- Rutinas de entrenamiento

### Hevy
- Username-based
- Tracking de workouts de fuerza
- Integración parcial (mock data visible en logs)

---

## 8. 🧠 LÓGICA INTELIGENTE

### Algoritmos Detectados

#### 1. **Readiness Score v1.0** (`readiness_engine.py`)
```python
readiness = (
    sleep_score * 0.30 +
    recovery_score * 0.25 +
    strain_score * 0.20 +
    activity_balance * 0.15 +
    hr_baseline * 0.10
)
```

**Lógica por componente:**
- **Sleep**: Interpolación lineal 5h→40, 7h→80, 9h→100
- **Recovery**: Basado en HRV vs baseline (ratio >1.10 = excelente)
- **Strain**: Inverso del nivel de estrés (<25 = bueno)
- **Activity**: Balance de pasos (no sedentario, no sobreentrenamiento)
- **HR Baseline**: Desviación del baseline personal (±5 bpm = perfecto)

#### 2. **Readiness Score v2.0 Adaptive** (`readiness_adaptive.py`)
**Mejoras PRO:**
- Perfiles de atleta con pesos ajustables
- Cálculo de baselines del histórico (90 días)
- Detección de patrón de recuperación (fast/normal/slow)
- Cálculo de sueño óptimo personalizado
- Detección de overreaching (>2 señales de 4)
- Predicciones futuras de readiness

#### 3. **ACWR** (Acute:Chronic Workload Ratio)
```
ratio = acute_load (7d) / chronic_load (28d/4)
```
- <0.8: Desentrenamiento
- 0.8-1.3: Óptimo
- >1.3: Sobreesfuerzo
- >1.5: Peligro de lesión

#### 4. **AI Context Builder** (`App.tsx:242-265`)
System prompt dinámico que incluye:
- Perfil del atleta
- Readiness actual
- Métricas biométricas
- Últimos entrenamientos
- Documentos analizados

### Nivel de Sofisticación
⭐⭐⭐☆☆ **Intermedio-Avanzado**
- ✅ Fórmulas científicamente fundamentadas
- ✅ Personalización por baseline
- ✅ Múltiples fuentes de datos
- ⚠️ No hay ML/entrenamiento de modelos (aún)
- ⚠️ No hay detección automática de patrones complejos

---

## 9. ⚠️ PROBLEMAS DETECTADOS

### 🔴 Críticos

#### 1. **Duplicación de Código**
- `analytics_service.py` tiene `get_readiness_score()` básico
- `readiness_engine.py` tiene implementación completa v1.0
- `readiness_adaptive.py` tiene v2.0 PRO
- **Impacto**: Mantenimiento difícil, inconsistencias potenciales
- **Fix**: Consolidar en `readiness_engine.py`, eliminar duplicados

#### 2. **No hay WebSocket Consumer en Frontend**
- Backend implementado y funcional
- Frontend no se conecta vía WS
- **Impacto**: Polling innecesario cada 5 minutos
- **Fix**: Implementar `useWebSocket()` hook en React

#### 3. **Autenticación Simulada**
- `get_current_user_id()` retorna `"default_user"` hardcodeado
- Sin JWT real, sin autorización por usuario
- **Impacto**: No es multi-tenant, cualquiera ve datos de "default_user"
- **Fix**: Implementar OAuth2/JWT flow completo

### 🟡 Medios

#### 4. **Gestión de Tokens Garmin Frágil**
- `token_dir=None` causa TypeError (ya parcialmente fixeado)
- Sesiones expiran sin manejo de refresh
- **Impacto**: Reconexión manual frecuente
- **Fix**: Implementar refresh automático + reintentos exponenciales

#### 5. **CORS Configurado Demasiado Permisivo**
```python
allow_origins=["*"]  # En producción esto es peligroso
```
- **Impacto**: Seguridad comprometida en producción
- **Fix**: Especificar orígenes exactos: `["http://localhost:5173"]`

#### 6. **Sin Manejo de Errores de Red en Frontend**
- Si backend cae, frontend no muestra error claro
- Retries automáticos no implementados
- **Impacto**: UX pobre en fallos de red
- **Fix**: Implementar axios interceptors con retry

### 🟢 Leves

#### 7. **Valores Hardcodeados**
- Umbral de pasos (8000) para día de descanso
- Pesos del readiness score fijos (no adaptativos aún en v1.0)
- **Impacto**: Menos preciso para usuarios atípicos

#### 8. **No hay Rate Limiting**
- Endpoints expuestos sin limitación
- **Impacto**: Vulnerable a DoS
- **Fix**: Implementar slowapi o similar

---

## 10. 🚀 MEJORAS PRIORITARIAS

### Prioridad 1: CRÍTICA (Hacer HOY)

1. **Unificar Readiness Score**
   - Eliminar `analytics_service.py::get_readiness_score()`
   - Usar solo `readiness_engine.py`
   - Archivos: 2 modificados
   - Impacto: Consistencia de datos

2. **Implementar WebSocket Frontend**
   - Crear `useWebSocket.ts` hook
   - Conectar a `/api/v1/ws/readiness`
   - Eliminar polling de 5 minutos
   - Archivos: 1 nuevo, 1 modificado
   - Impacto: Tiempo real verdadero, menos carga en servidor

### Prioridad 2: ALTA (Esta semana)

3. **Sistema de Autenticación Real**
   - JWT tokens
   - Login/logout flow
   - Protección de endpoints
   - Archivos: 4+ modificados
   - Impacto: Multi-usuario seguro

4. **Testing Automatizado**
   - Tests unitarios para ReadinessEngine
   - Tests de integración para endpoints
   - Archivos: Nuevos directorios `tests/`
   - Impacto: Estabilidad, regresiones detectadas

5. **Caché de Readiness Score**
   - Cachear resultado 15 minutos si datos no cambian
   - Redis (escala) o memoria (simple)
   - Archivos: 1-2 modificados
   - Impacto: Reducir cálculos repetidos 80%

### Prioridad 3: MEDIA (Este mes)

6. **Dashboard de Analytics**
   - Gráficos de tendencias (recharts o similar)
   - Comparativa semanal/mensual
   - Predicciones de readiness

7. **Alertas Push**
   - Notificaciones cuando readiness baja <50
   - Alertas de overreaching detectado

8. **ML Básico**
   - Regresión lineal para predicción de readiness
   - Clustering de tipos de recuperación

---

## 11. 📈 ESTADO DEL PROYECTO

### 🟡 **En desarrollo (Casi estable)**

**Justificación:**
- ✅ Core funcional: Sincronización Garmin, Readiness Score, Chat IA
- ✅ Datos reales: 450 días de Sergi funcionando
- ✅ Arquitectura limpia: Separación backend/frontend
- ⚠️ Bugs conocidos: Duplicación código, WS no conectado
- ⚠️ Falta testing: Sin cobertura de tests
- ⚠️ No es production-ready: Sin auth real, CORS permisivo

**Puntos fuertes:**
- Lógica biométrica sólida y científicamente fundamentada
- Integración Garmin estable
- Frontend moderno y responsive
- Código relativamente limpio y mantenible

**Puntos débiles:**
- Deuda técnica acumulada (duplicación)
- Falta de testing
- No multi-usuario aún

---

## 12. 🧩 FALTANTE PARA PRODUCCIÓN

### Seguridad
- [ ] Autenticación JWT completa
- [ ] Autorización por roles (admin/user)
- [ ] CORS restringido a dominios específicos
- [ ] Rate limiting en endpoints
- [ ] Validación de inputs con Pydantic estricto
- [ ] Sanitización de datos de usuario
- [ ] HTTPS forzado

### Escalabilidad
- [ ] PostgreSQL en lugar de SQLite
- [ ] Redis para caché y WebSocket pub/sub
- [ ] Background workers (Celery/RQ) para sync
- [ ] Load balancing (si múltiples instancias)

### Testing
- [ ] Tests unitarios (pytest) - cobertura >80%
- [ ] Tests de integración
- [ ] Tests E2E (Playwright/Cypress)
- [ ] CI/CD pipeline (GitHub Actions)

### Deploy
- [ ] Docker containers
- [ ] docker-compose para desarrollo
- [ ] Kubernetes manifests (escala)
- [ ] CD a VPS/cloud (Render/Railway/AWS)
- [ ] Monitoring (Sentry para errores)

### UX/UI
- [ ] Dark mode completo
- [ ] Mobile app (React Native o PWA)
- [ ] Offline mode (PWA con service workers)
- [ ] Notificaciones push nativas

---

## 📌 RESUMEN EJECUTIVO

**Dashboard-Vitalis** es un sistema de entrenamiento personal con IA que:
1. ✅ **Funciona**: Sincroniza Garmin, calcula readiness, ofrece chat IA contextualizado
2. ⚠️ **Tiene deuda técnica**: Código duplicado, WebSocket no conectado en frontend
3. 🚀 **Está cerca de producción**: Con 2-3 semanas de trabajo en auth + testing + WS

**Próximo paso recomendado:**
> Implementar WebSocket consumer en frontend para eliminar polling y consolidar lógica de readiness en un solo engine.

---

**Fin del informe**  
*Generado por VITALIS CODE ANALYZER v1.0*
