# INFORME DE AUDITORÍA - ATLAS Dashboard

**Fecha**: 2026-05-13  
**Versión del código**: main (d7583bd9...)  
**Alcance**: Frontend, Backend, Seguridad, APIs externas, Tests  

---

## ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Infraestructura y Dependencias](#2-infraestructura-y-dependencias)
3. [Auditoría Frontend](#3-auditoría-frontend)
4. [Auditoría Backend](#4-auditoría-backend)
5. [Seguridad y Autenticación](#5-seguridad-y-autenticación)
6. [Manejo de Errores y Edge Cases](#6-manejo-de-errores-y-edge-cases)
7. [Integraciones de APIs Externas](#7-integraciones-de-apis-externas)
8. [Tests y Cobertura](#8-tests-y-cobertura)
9. [Tabla de Prioridades](#9-tabla-de-prioridades)
10. [Recomendaciones Inmediatas](#10-recomendaciones-inmediatas)

---

## 1. RESUMEN EJECUTIVO

ATLAS es una aplicación full-stack de fitness con un frontend React 19 + TypeScript y un backend Python FastAPI. La auditoría ha revelado **múltiples hallazgos críticos** que requieren atención inmediata, especialmente en seguridad y manejo de datos sensibles.

### Puntuación General por Categoría

| Categoría | Score (1-10) | Estado |
|-----------|-------------|--------|
| Seguridad de datos | 3/10 | CRÍTICO |
| Seguridad API | 4/10 | CRÍTICO |
| Calidad de código | 6/10 | ACEPTABLE |
| Integridad de datos | 5/10 | MEDIO |
| Manejo de errores | 5/10 | MEDIO |
| Escalabilidad | 5/10 | MEDIO |
| Tests | 4/10 | DEFICIENTE |

---

## 2. INFRAESTRUCTURA Y DEPENDENCIAS

### 2.1 Dependencias Problemáticas

**Frontend:**
- `xlsx@0.18.5` - Paquete abandonado con múltiples CVEs conocidos
- `dotenv@^17.3.1` - Versión inexistente (última es 16.4.7)
- `react@19.0.0` - Versión muy nueva, posibles incompatibilidades
- `express`/`cors`/`express-async-handler` en dependencies - Paquetes de backend en frontend

**Backend:**
- No hay congelación de dependencias (`Pipfile.lock`, `poetry.lock`, `requirements-freeze.txt`)
- No hay `pyproject.toml` ni configuración de herramientas de calidad

### 2.2 Archivos Duplicados/Backup

| Archivo | Problemática |
|---------|-------------|
| `vite.config.ts.backup` | Backup antiguo de configuración |
| `src/services/healthConnectService.ts.backup` | Backup de servicio |
| `app_backup_v2/` | Copia entera del backend |
| `backend/atlas.db` (0 bytes) | DB SQLite vacía/orfandad |
| `backend/*.db-shm` / `*.db-wal` | Archivos WAL de SQLite en git |

### 2.3 Scripts de Debug Peligrosos

**Archivos con credenciales hardcodeadas:**
- `backend/tests/debug_sync_today.py` - **Password de Garmin en plaintext** + email real
- `backend/show_password.py` - Script para mostrar contraseñas de tabla tokens
- `backend/update_password_direct.py` - Modifica contraseñas directamente en DB

---

## 3. AUDITORÍA FRONTEND

### 3.1 Hallazgos Críticos

#### Memory Leaks WebSocket
```typescript
// useNotifications.ts, línea 144-146
setTimeout(() => setLatestToast(null), 4000); // Sin identificador, sin limpiar
```
- **Impacto**: Timeout suelto que intenta setState después del desmontaje

#### requestAnimationFrame sin cancelar
```typescript
// ReadinessDashboard.tsx:50-63
function AnimatedCounter({ target, duration = 800 }) {
  // Falta guardar el requestId para cancelar
}
```

#### Inconsistencia fetch vs axios
```typescript
// aiService.ts usa fetch nativo (sin timeout, sin baseURL configured)
// api.ts usa axios con interceptores pero sin retry automático
```

#### Chat key={index} anti-pattern
```typescript
// Chat.tsx:119
chatHistory.map((msg, index) => (
  <MessageBubble key={index} /> // ❌ problema si se editan/eliminan mensajes
))
```

### 3.2 Performance

- **Sin lazy loading**: Todos los componentes de páginas se cargan estáticamente
- **Zustand sin selectores finales**: `const { activeTab } = useAtlasStore()` re-renderiza todo
- **useScreenWidth sin debounce**: Resize causes re-render on every pixel

### 3.3 TypeScript

- 63+ ocurrencias de `any`
- `types.ts` tiene propiedades como `plan_data?: any` - tipado muy laxo
- `api.ts`: `params?: Record<string, any>` - sin contraints de tipos

---

## 4. AUDITORÍA BACKEND

### 4.1 Seguridad de Datos (CRÍTICO)

#### Contraseñas en Texto Plano
```python
# backend/app/models/token.py
class Token(Base):
    garmin_email = Column(String)
    garmin_password = Column(String)  # SIN HASH / CIFRADO
    garmin_session = Column(String)   # JSON de sesión sin cifrar
    wger_api_key = Column(String)   # API key en texto plano
    fcm_token = Column(String)       # FCM token sin cifrar
```

#### Datos PII Hardcodeados
```python
# backend/app/main.py
user = User(id="default_user", 
           email="sergi.marquez.al@gmail.com",  # Email real
           name="Sergi")

# backend/app/services/ai_service.py (múltiples lugares)
athlete_name = "Sergi"
athlete_age = "47"
step_target = "20.000"
# + FALLBACK_SYSTEM_PROMPT contiene datos personales
```

### 4.2 Problemas de Concurrencia

#### Caché sin Thread-Safety
```python
# ai_service.py, líneas 102-104
_prompt_cache = {}  # Dict global sin locks
_coach_context_cache = {}  
_welcome_cache = {}
```
- Riesgo de race condition en lectura/escritura

#### SQLite con FastAPI: Race en escrituras
```python
# db/session.py
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# WAL mode mitiga pero no elimina el problema
```

#### Sync sin Atomicidad
```python
# sync_service.py - commit por cada día
for date in dates:
    # procesa día
    db.commit()  # si falla en día 4, días 1-3 quedan guardados (inconsistencia)
```

### 4.3 Código Dead / Duplicado

| Archivo | Estado |
|---------|--------|
| `core/readiness_engine.py` | ❌ Duplicado: `services/readiness_service.py` implementa lo mismo |
| `services/auth_service.py` | ⚠️ JWT implementado pero NUNCA usado en endpoints |
| `training/domain/models.py` | ⚠️ Schemas complejos pero no se usan en endpoints principales |

### 4.4 TODOs sin Acción

```
backend/app/api/deps.py:            "TODO: Implementar decodificación JWT real"
backend/app/services/memory_service.py: "TODO: Integrate with notification system..."
backend/app/training/api/endpoints.py:  "TODO: Implementar generación de planes completos"
backend/app/api/api_v1/endpoints/readiness_ws.py: "TODO: Validar token JWT para obtener user_id"
```

---

## 5. SEGURIDAD Y AUTENTICACIÓN

### 5.1 Ausencia Total de Autenticación

**Archivo**: `backend/app/api/deps.py`

```python
def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="x-user-id")) -> str:
    if x_user_id:
        return x_user_id  # ✅ Acepta CUALQUIER valor sin validación
    return "default_user"
```

**Vector de ataque**: Algun cambia el header `x-user-id` y accede a datos del atleta
```bash
curl -H "x-user-id: otro_usuario" https://api.example.com/api/v1/biometrics/
```

### 5.2 CORS Problemático

```python
# main.py, líneas 84-107
origins = [
    "https://*.fly.dev",     # ❌ wildcard
    "capacitor://",           # ❌ sin host específico
    "ionic://",               # ❌ sin host específico
    "http://localhost",       # ❌ sin puerto
]
if settings.ALLOW_ALL_ORIGINS:
    origins = ["*"]           # ❌ wildcard + allow_credentials=True = CRÍTICO

app.add_middleware(CORSMiddleware, 
    allow_origins=origins,
    allow_credentials=True,    # ❌ wildcard con credentials
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### 5.3 Endpoints sin Rate Limit

**Solo 3 endpoints tienen rate limiting:**
- `POST /api/v1/ai/chat` (30 req/60s)
- `POST /api/v1/sync/garmin` (10 req/1h)
- `POST /api/v1/auth/garmin/login` (5 req/1h)

**Los ~60+ endpoints restantes están desprotegidos.**

### 5.4 WebSockets sin Autenticación

```python
# readiness_ws.py, notifications_ws.py
# Ambos aceptan cualquier conexión y usan "default_user"
user_id = "default_user"
```

---

## 6. MANEJO DE ERRORES Y EDGE CASES

### 6.1 Patrón except Exception: Genérico

```python
# ai_service.py - 9 bloques de "except Exception" en build_coach_context()
try:
    profile_data = AthleticIntelligenceService.get_full_athletic_profile(db, user_id)
except Exception as e:
    logger.warning(f"build_coach_context: AthleticIntelligence failed: {e}")
    # Silencia errores de programación (NameError, SyntaxError, AttributeError, etc.)
```

### 6.2 Errores Silenciados con `except: pass`

| Archivo | Contexto |
|---------|----------|
| `sync_service.py:91` | Body Battery falla silenciosamente |
| `sync_service.py:103` | Training Readiness falla silenciosamente |
| `ai_service.py:509` | Datos de usuario no disponibles |
| `ai_service.py:522` | Profile Summary no disponible |
| `ai_service.py:625` | Injury context no disponible |

### 6.3 Validaciones Ausentes

#### Datos numéricos sin validar rangos
```python
# readiness_service.py
hrv = data.get("hrv")  # None es válido, pero después en _score_hrv() puede causar errores
stress = data.get("stress")  # ¿-1? ¿150? sin bounds checking
```

#### Fechas sin validación
```python
# training_plan_service.py
week_start: Optional[str] = None  # No se valida formato YYYY-MM-DD
```

#### División potencial por cero
```python
# readiness_service.py
normalized_weights = {k: v / total_weight for k, v in available_weights.items()}
# Si total_weight es 0 después del fallback, ZeroDivisionError
```

---

## 7. INTEGRACIONES DE APIS EXTERNAS

### 7.1 Garmin Integration

**Positivos:**
- Tres niveles de fallback de autenticación
- Retry con backoff exponencial
- Detección de 429 (rate limit)

**Negativos:**
- Password en texto plano en DB (sin hash bcrypt o Fernet)
- No hay modo "mock" para testing
- Token expirado gestionado pero sin circuit breaker

### 7.2 AI Provider Chain (Groq → Gemini → Ollama)

```python
# ai_service.py:713-752
# 1. Groq (10s) → 2. Gemini (10s) → 3. Ollama (10s)
```

**Falta:**
- ❌ Circuit breaker (si fallan 3x seguidas, seguirá intentando)
- ❌ Cost tracking/estimation
- ❌ Token usage metrics
- ❌ Prompt injection middleware
- ❌ Temperature/máx tokens configurables por provider

### 7.3 Telegram Notifications

- ✅ Graceful fallback si no está configurado
- ❌ Sin rate limiting propio (Telegram: ~30 msg/min)
- ❌ Sin cola de mensajes/async queue

---

## 8. TESTS Y COBERTURA

### 8.1 Qué Se Testea

| Componente | Cobertura | Calidad |
|---|---|---|
| `readiness_service` | Null safety, ranges | ✅ Buena |
| `ai_service.detect_conversation_mode` | Keywords | ✅ Muy buena |
| `analytics_service` | Estadísticas | ✅ Buena |
| `rate_limiter` | Bucket algorithm | ✅ Básica |

### 8.2 Tests Rotos

```
ImportError: cannot import name 'AthleteProfile' from 'app.core.readiness_engine'
# test_readiness_engine.py está desincronizado del código productivo
```

### 8.3 Qué NO Se Testea

- `sync_service.py` (Garmin sync)
- Cadena de fallback de IA (Groq→Gemini→Ollama)
- Telegram notifications
- WebSocket handlers
- Scheduler service
- Rate limiter middleware HTTP
- Database migration integrity
- End-to-end integración

---

## 9. TABLA DE PRIORIDADES

### Crítico (Corregir en 24-48h)

| # | Hallazgo | Archivo | Acción |
|---|----------|---------|--------|
| 1 | **Passwords de Garmin en plaintext** | `models/token.py`, `main.py`, `auth.py` | Implementar cifrado con Fernet/cryptography |
| 2 | **Scripts con credenciales hardcodeadas** | `tests/debug_sync_today.py`, `show_password.py` | Eliminar del repo + rotar credentials |
| 3 | **Sin autenticación** - Bypass total por header | `deps.py`, todos los endpoints | Implementar JWT real con validación |
| 4 | **CORS wildcard con credentials** | `main.py` | Restringir orígenes exactos, quitar wildcard |
| 5 | **Exposición de API keys** | `.env.example` (Strava secret), `settings.py` | Eliminar secrets del repo + rotar |
| 6 | **WebSockets sin autenticación** | `readiness_ws.py`, `notifications_ws.py` | Validar JWT en WebSocket handshake |

### Alta (Corregir en 1-2 semanas)

| # | Hallazgo | Acción |
|---|----------|--------|
| 7 | Extender rate limiting a todos los endpoints | Rate limiter middleware |
| 8 | Implementar circuit breaker para AI providers | ai_service.py |
| 9 | Eliminar código dead (readiness_engine duplicado) | Limpiar proyecto |
| 10 | Validar schemas con Pydantic en todos los endpoints | Crear schemas para inputs |
| 11 | Cache thread-safe con locks o TTLCache | ai_service.py |
| 12 | Atomicidad en transacciones de sync | sync_service.py con `db.begin()` |
| 13 | Reemplazar `except: pass` por logging específico | Todo el proyecto |
| 14 | Headers de seguridad (HSTS, CSP, X-Frame-Options) | main.py middleware |

### Media (Corregir en 1 mes)

| # | Hallazgo | Acción |
|---|----------|--------|
| 15 | Reemplazar `xlsx` por alternativa mantenida | npm install exceljs/papaparse |
| 16 | Lazy loading de páginas con React.lazy | App.tsx |
| 17 | Eliminar `any` de TypeScript en APIs críticas | api.ts, hooks |
| 18 | Implementar memory leaks en WebSocket timers | useNotifications.ts, AnimatedCounter |
| 19 | Debounce en useScreenWidth | hooks/ |
| 20 | Añadir cost/usage tracking de IA | ai_service.py |

---

## 10. RECOMENDACIONES INMEDIATAS

### Próximos pasos (orden de prioridad)

**1. Seguridad (hoy/nunca tarde):**
```bash
# Eliminar archivos peligrosos
rm backend/tests/debug_sync_today.py
rm backend/show_password.py
rm backend/update_password_direct.py

# Añadir a .gitignore
echo "*.db" >> .gitignore
echo "*.db-shm" >> .gitignore
echo "*.db-wal" >> .gitignore
echo "backend/tests/debug_*.py" >> .gitignore

# Rotar secrets
# - Revocar y regenerar API keys de Groq, Telegram, Strava
# - Cambiar contraseña de Garmin
```

**2. Implementar autenticación básica:**
```python
# En core/auth.py o deps.py
@require_auth
def get_current_user_id(request: Request):
    # Validar JWT de verdad, no devolver "default_user"
    raise NotImplementedError("JWT required")
```

**3. Cifrado de credenciales Garmin:**
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
cipher = Fernet(key)

# Almacenar
token.garmin_password = cipher.encrypt(password.encode()).decode()

# Recuperar
password = cipher.decrypt(token.garmin_password.encode()).decode()
```

**4. Tests críticos (arreglar test_readiness_engine.py):**
El test importa `AthleteProfile` que no existe. Verificar si debe importar `ReadinessFactors` o `ReadinessStatus`.

### Métricas de Éxito

- ✅ 0 contraseñas en texto plano en DB
- ✅ 0 scripts con credenciales en repositorio
- ✅ Autenticación JWT en todos los endpoints
- ✅ CORS restringido a orígenes específicos
- ✅ Todos los tests pasan (`pytest -x`)
- ✅ Rate limiting activo en endpoints críticos
- ✅ No hay `except: pass` sin logging
