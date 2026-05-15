# 🧬 ATLAS VIVO — Roadmap Técnico Detallado

> Convertir ATLAS de sistema reactivo a Director Deportivo digital con iniciativa propia.
> Documento de arquitectura, no de especulación. Cada elemento aquí mapea a código existente o propuesto.

---

## 📐 Arquitectura General

```
SENSORES → PERCEPCIÓN → ESTADO INTERNO → DECISIÓN → ACCIÓN → APRENDIZAJE
  (existe)    (existe)      (🆕 NUEVO)    (🆕 NUEVO)  (parcial)   (🆕 NUEVO)
```

---

## FASE 1 — Pulso y Memoria Operativa

### 1.1 Modelos de Datos (Nuevas Tablas SQLite)

> **Nota de migración:** SQLAlchemy con `Base.metadata.create_all()` crea las tablas automáticamente al arrancar. No se requiere script de migración para tablas nuevas. Si se añaden columnas a tablas existentes, usar `ALTER TABLE` manual en `backend/app/main.py` dentro del lifespan, siguiendo el patrón existente (ver migraciones de `birth_date`, `planned_workouts`, `tokens`).

#### `backend/app/models/athlete_state.py` (🆕 NUEVO)

```python
class AthleteState(Base):
    __tablename__ = "athlete_state_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)

    # Dimensiones del estado
    energy_state = Column(String, default="stable")       # depleted|fragile|stable|rising|peak
    adherence_state = Column(String, default="compliant")  # disconnected|inconsistent|compliant|consistent|locked_in
    momentum_state = Column(String, default="neutral")     # stalled|regressing|neutral|building|compounding
    risk_state = Column(String, default="low")             # low|moderate|high|acute
    motivation_state = Column(String, default="motivated") # motivated|flat|avoidant|frustrated|resilient
    training_phase = Column(String, default="build")       # build|consolidate|deload|recover|re-entry

    # Métricas
    trust_in_plan = Column(Float, default=0.5)
    confidence = Column(Float, default=0.5)

    # Narrativa
    narrative_summary = Column(Text)
    recommended_coaching_style = Column(String, default="firm_supportive")
    # Cálculo: mapeo directo del estado combinado:
    #   risk="high"|risk="acute"                   → clinical_alert
    #   energy="peak" + momentum="compounding"      → celebratory_sharp
    #   adherence="disconnected"|motivation="flat"  → light_humor
    #   momentum="building"                           → strategic_coach
    #   default                                         → firm_supportive

    # Metadatos
    triggers_fired = Column(JSON, default=list)
    dimensions_raw = Column(JSON, default=dict)  # Valores raw de cada dimensión (readiness, hrv, acwr, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### `backend/app/models/atlas_event.py` (🆕 NUEVO)

```python
class AtlasEvent(Base):
    __tablename__ = "atlas_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    # Tipos: biometrics_synced | workout_logged | pain_reported | readiness_computed
    #        daily_loop_completed | plan_adjusted | notification_opened
    #        workout_missed | recovery_mode_activated | check_in_submitted
    payload = Column(JSON, default=dict)
    source = Column(String, default="system")
    correlation_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

# ⚠️  Limpieza: La tabla puede crecer ~500 filas/día.
#     Programar cleanup semanal de eventos >30 días (ver scheduler en 1.4).
```

#### `backend/app/models/atlas_intervention.py` (🆕 NUEVO)

```python
class AtlasIntervention(Base):
    __tablename__ = "atlas_interventions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    intervention_type = Column(String, nullable=False)
    # Tipos: intensity_adjustment | session_reroute | recovery_activation
    #        adherence_nudge | check_in_request | plan_proposal
    #        risk_alert | opportunity_alert | weekly_review

    trigger_source = Column(String)  # daily_loop | injury_prevention | analytics | schedule
    priority = Column(Integer, default=3)   # 1-5 (5 = crítico)
    confidence = Column(Float, default=0.5) # 0.0-1.0

    # Decisión
    autonomy_level = Column(Integer, default=1)  # 1=auto, 2=propuesta, 3=validación
    requires_confirmation = Column(Boolean, default=False)
    action_taken = Column(JSON, default=dict)
    reason = Column(Text)

    # Delivery
    channel = Column(String, default="app")      # app|telegram|system
    message_text = Column(Text)

    # Outcome tracking
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    accepted = Column(Boolean, nullable=True)
    outcome_score = Column(Float, nullable=True)  # 0.0-1.0 qué tan efectiva fue
    # Cálculo de outcome_score:
    #   ponderación de 4 factores:
    #   - accepted (0-1): 0.4 peso — el usuario aceptó la acción
    #   - responded_time (0-1): 0.3 peso — rapidez de respuesta (más rápido = mejor)
    #   - subsequent_action (0-1): 0.2 peso — el usuario ejecutó la acción recomendada
    #   - adherence_impact (0-1): 0.1 peso — la adherencia mejoró tras la intervención (siguientes 48h)
    #   outcome_score = sum(factor * peso) → clamped a [0.0, 1.0]

    outcome_note = Column(String)

    # Control
    cooldown_key = Column(String, index=True)
    cooldown_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
```

---

**🧩 Registro en módulos existentes:**

En `backend/app/db/base.py`, importar los nuevos modelos:
```python
from app.models.athlete_state import AthleteState
from app.models.atlas_event import AtlasEvent
from app.models.atlas_intervention import AtlasIntervention
```

En `backend/app/models/__init__.py`, exportarlos:
```python
from .athlete_state import AthleteState
from .atlas_event import AtlasEvent
from .atlas_intervention import AtlasIntervention
```

---

### 1.2 Servicios Nuevos

#### `backend/app/services/athlete_state_service.py` (🆕 NUEVO)

```python
class AthleteStateService:
    """Sintetiza el estado narrativo del atleta a partir de múltiples fuentes."""

    def compute_state(user_id: str) -> AthleteState:
        """Calcula el estado actual del atleta."""

    def get_state(user_id: str) -> Optional[AthleteState]:
        """Obtiene el último snapshot de estado."""

    def _determine_energy(readiness, hrv, rhr, sleep) -> str:
        """depleted|fragile|stable|rising|peak"""

    def _determine_adherence(recent_workouts, planned_sessions) -> str:
        """disconnected|inconsistent|compliant|consistent|locked_in"""

    def _determine_momentum(recent_trend, progression) -> str:
        """stalled|regressing|neutral|building|compounding"""

    def _determine_risk(acwr, pain, recovery, readiness_trend) -> str:
        """low|moderate|high|acute"""

    def _determine_motivation(engagement, completion_rate, notification_response) -> str:
        """motivated|flat|avoidant|frustrated|resilient"""

    def _generate_narrative(state) -> str:
        """Genera resumen narrativo del estado."""

    def _recommend_coaching_style(state) -> str:
        """firm_supportive|clinical_alert|celebratory_sharp|strategic_coach|light_humor"""
```

#### `backend/app/services/intervention_service.py` (🆕 NUEVO)

```python
class InterventionService:
    """Evalúa señales y decide si ATLAS debe intervenir."""

    def evaluate_triggers(user_id: str, event: AtlasEvent) -> Optional[InterventionDecision]:
        """Procesa un evento y decide si intervenir."""

    def score_intervention(triggers: list, athlete_state: AthleteState) -> InterventionDecision:
        """Puntúa oportunidad de intervención."""

    def execute_intervention(user_id: str, decision: InterventionDecision) -> AtlasIntervention:
        """Ejecuta la intervención (notificar, ajustar plan, etc.)."""

    def get_active_interventions(user_id: str) -> list[AtlasIntervention]:
        """Intervenciones activas/pendientes."""

    def acknowledge_intervention(intervention_id: str, response: str):
        """Usuario responde a intervención."""
```

#### `backend/app/services/event_bus_service.py` (🆕 NUEVO)

```python
class EventBusService:
    """Sistema de eventos interno ligero."""

    def emit(user_id: str, event_type: str, payload: dict, source: str = "system"):
        """Registra un evento en la cola."""

    def process_pending(dry_run: bool = False) -> list[AtlasEvent]:
        """Procesa eventos pendientes."""

    def get_events(user_id: str, event_type: str = None, limit: int = 50) -> list[AtlasEvent]:
        """Historial de eventos."""

    def cleanup_events(older_than_days: int = 30):
        """Limpieza de eventos antiguos."""
```

#### `backend/app/services/intervention_outcome_service.py` (🆕 NUEVO)

```python
class InterventionOutcomeService:
    """Mide efectividad de las intervenciones."""

    def record_outcome(intervention_id: str, outcome: dict):
        """Registra el resultado de una intervención."""

    def get_outcome_stats(user_id: str, intervention_type: str = None) -> dict:
        """Estadísticas de efectividad."""

    def get_best_channel(user_id: str, intervention_type: str) -> str:
        """Aprende mejor canal para tipo de intervención."""

    def get_best_timing(user_id: str, intervention_type: str) -> str:
        """Aprende mejor momento del día."""
```

### 1.3 Cambios a Servicios Existentes

#### `backend/app/services/daily_loop_service.py` — Modificar

**Cambios:**
1. Al final de `run_daily_loop()`, **emitir evento** `readiness_computed` con payload completo
2. Al final de `run_daily_loop()`, **invocar** `AthleteStateService.compute_state()`
3. Al detectar anomalía, **emitir evento** con datos relevantes

```python
# Al final de run_daily_loop, añadir:
from app.services.event_bus_service import EventBusService
EventBusService.emit(
    user_id=user_id,
    event_type="daily_loop_completed",
    payload={"readiness": readiness_score, "insights": insights, "date": str(today)}
)
AthleteStateService.compute_state(user_id)
```

#### `backend/app/services/sync_service.py` — Modificar

**Cambios:**
1. Tras sync exitoso de Garmin, **emitir** `biometrics_synced`
2. Tras detectar workout nuevo, **emitir** `workout_logged`

#### `backend/app/services/injury_prevention_service.py` — Modificar

**Cambios:**
1. Al detectar alerta Roja/Naranja, **emitir** `pain_reported` o `risk_alert`
2. Al activar recovery mode, **emitir** `recovery_mode_activated`

#### `backend/app/services/training_plan_service.py` — Modificar

**Cambios:**
1. Al ajustar plan, **emitir** `plan_adjusted`
2. Si el usuario no completa sesión prevista, **emitir** `workout_missed`
3. Al generar plan semanal, **emitir** `plan_generated`

#### `backend/app/services/notification_service.py` — Modificar

**Cambios:**
1. Añadir método `send_intervention(intervention: AtlasIntervention)` con formato específico
2. Tras enviar notificación, **registrar** `delivered_at` en intervención
3. Tras usuario abrir, **registrar** `opened_at`
4. Añadir campo `intervention_id` al payload WebSocket

### 1.4 Nuevos Jobs del Scheduler

En `backend/app/services/scheduler_service.py`, añadir:

```python
# --- INTERVENTION SCANS ---

async def morning_intervention_scan():
    """(06:30 UTC) Escanea oportunidades de intervención matutina."""
    users = session.query(User).all()
    for user in users:
        state = AthleteStateService.get_state(user.id)
        if state and state.risk_state in ("high", "acute"):
            InterventionService.evaluate_triggers(
                user.id, AtlasEvent(event_type="morning_check", payload={})
            )

async def midday_pulse_check():
    """(13:00 UTC) Check de medio día — ventanas de oportunidad."""
    # Verificar sesiones pendientes, ventanas de entrenamiento

async def evening_review_scan():
    """(20:00 UTC) Escaneo de cierre del día."""
    # Evaluar cumplimiento, preparar narrativa de cierre

async def missed_session_detection():
    """(cada 2h, 08-22 UTC) Detecta sesiones no realizadas."""
    # Si había sesión planificada y no se ejecutó en ventana

async def event_processor():
    """(cada 5 min) Procesa eventos pendientes en la cola."""
    EventBusService.process_pending()

async def cooldown_cleanup():
    """(cada 6h) Limpia cooldowns expirados."""
    # Liberar cooldowns vencidos para permitir nuevas intervenciones

async def cleanup_old_events():
    """(semanal, domingo 03:00 UTC) Limpia eventos e intervenciones antiguas."""
    EventBusService.cleanup_events(older_than_days=30)
    # También archivar intervenciones completadas >60 días
```

En `start_scheduler()`, añadir:

```python
scheduler.add_job(
    morning_intervention_scan, "cron", hour=6, minute=30,
    id="morning_intervention_scan", **BASE_OPTS
)
scheduler.add_job(
    midday_pulse_check, "cron", hour=13, minute=0,
    id="midday_pulse_check", **BASE_OPTS
)
scheduler.add_job(
    evening_review_scan, "cron", hour=20, minute=0,
    id="evening_review_scan", **BASE_OPTS
)
scheduler.add_job(
    event_processor, "interval", minutes=5,
    id="event_processor", **BASE_OPTS
)
scheduler.add_job(
    missed_session_detection, "interval", hours=2,
    id="missed_session_detection", **BASE_OPTS
)
scheduler.add_job(
    cooldown_cleanup, "interval", hours=6,
    id="cooldown_cleanup", **BASE_OPTS
)
scheduler.add_job(
    cleanup_old_events, "cron", day_of_week="sun", hour=3, minute=0,
    id="cleanup_old_events", **BASE_OPTS
)
```

### 1.5 Nuevos Endpoints API

En `backend/app/api/api_v1/endpoints/`, añadir:

#### `backend/app/api/api_v1/endpoints/athlete_state.py` (🆕 NUEVO)

```
GET  /athlete-state          → Obtener estado actual del atleta
GET  /athlete-state/history  → Historial de estados (query: days=30)
POST /athlete-state/refresh  → Forzar recálculo del estado
```

#### `backend/app/api/api_v1/endpoints/interventions.py` (🆕 NUEVO)

```
GET  /interventions              → Intervenciones activas/pendientes
GET  /interventions/history      → Historial de intervenciones
POST /interventions/{id}/ack     → Usuario responde a intervención
GET  /interventions/stats        → Estadísticas de efectividad
```

#### `backend/app/api/api_v1/endpoints/events.py` (🆕 NUEVO)

```
GET  /events              → Historial de eventos (query: type, limit)
POST /events/process      → Forzar procesamiento de eventos pendientes
```

Registrar en `backend/app/api/api_v1/api.py`:

```python
from .endpoints import athlete_state, interventions, events

api_router.include_router(athlete_state.router, prefix="/athlete-state", tags=["athlete-state"])
api_router.include_router(interventions.router, prefix="/interventions", tags=["interventions"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
```

### 1.6 Cambios al Frontend

#### `src/store/atlasStore.ts` — Extender

Añadir al estado:

```typescript
interface AtlasState {
  // ... existente ...

  // 🆕 Living ATLAS
  athleteState: AthleteState | null;
  activeInterventions: Intervention[];
  pendingApprovals: Intervention[];
  dailyCadence: {
    morningChecked: boolean;
    middayChecked: boolean;
    eveningChecked: boolean;
  };
}
```

#### `src/hooks/useAthleteState.ts` (🆕 NUEVO)

Hook personalizado para:
- Fetch periódico del estado del atleta
- Suscripción WebSocket a `state_update`
- Refresco manual

#### `src/hooks/useInterventions.ts` (🆕 NUEVO)

Hook para:
- Listar intervenciones activas
- Ack/responder intervenciones
- Stats de efectividad

#### `src/components/atlas-live/` (🕐 NUEVO directorio)

Componentes de UI:

| Archivo | Función |
|---------|---------|
| `AtlasLivePanel.tsx` | Panel principal "ATLAS Live" |
| `AthleteStateCard.tsx` | Estado del día: energía, adherencia, momentum, riesgo |
| `DailyCadenceIndicator.tsx` | Indicador de ciclo diario (mañana/mediodía/tarde) |
| `InterventionTimeline.tsx` | Timeline de intervenciones del día |
| `DecisionApprovalBanner.tsx` | Bandeja de propuestas pendientes |
| `CoachMessage.tsx` | Mensaje de intervención con estilo según tono |

#### WebSocket — Extender

En el WebSocket de notificaciones existente, añadir tipos de mensaje:

```typescript
type WsMessageType =
  | "notification"
  | "state_update"       // 🆕 Nuevo estado del atleta disponible
  | "intervention"       // 🆕 Nueva intervención
  | "coach_prompt"       // 🆕 ATLAS inicia conversación
  | "plan_adjusted"      // 🆕 Plan modificado autónomamente
  | "briefing_ready";    // (existente)
```

#### `src/services/api.ts` — Extender

Añadir métodos:

```typescript
// Living ATLAS API
getAthleteState: () => getData<AthleteState>("/athlete-state"),
getAthleteStateHistory: (days = 30) => getData(`/athlete-state/history?days=${days}`),
refreshAthleteState: () => postData("/athlete-state/refresh"),
getInterventions: () => getData<Intervention[]>("/interventions"),
getInterventionsHistory: () => getData("/interventions/history"),
acknowledgeIntervention: (id: string, response: string) => postData(`/interventions/${id}/ack`, { response }),
getInterventionStats: () => getData("/interventions/stats"),
```

### 1.7 Policy: Autonomía
#### `backend/app/core/autonomy_policy.py` (🆕 NUEVO)

```python
class AutonomyLevel(IntEnum):
    AUTONOMOUS = 1    # Sin consulta
    PROPOSAL = 2      # Propuesta con confirmación ligera
    VALIDATION = 3    # Requiere validación explícita
    FORBIDDEN = 4     # Prohibido

class InterventionType(str, Enum):
    INTENSITY_ADJUST = "intensity_adjustment"
    SESSION_REROUTE = "session_reroute"
    RECOVERY_ACTIVATE = "recovery_activation"
    ADHERENCE_NUDGE = "adherence_nudge"
    CHECK_IN_REQUEST = "check_in_request"
    PLAN_PROPOSAL = "plan_proposal"
    RISK_ALERT = "risk_alert"
    OPPORTUNITY = "opportunity_alert"
    WEEKLY_REVIEW = "weekly_review"

AUTONOMY_MATRIX = {
    InterventionType.INTENSITY_ADJUST: AutonomyLevel.AUTONOMOUS,  # Bajo riesgo, reversible
    InterventionType.SESSION_REROUTE: AutonomyLevel.PROPOSAL,     # Medio impacto
    InterventionType.RECOVERY_ACTIVATE: AutonomyLevel.AUTONOMOUS, # Protege salud
    InterventionType.ADHERENCE_NUDGE: AutonomyLevel.AUTONOMOUS,   # Bajo riesgo
    InterventionType.CHECK_IN_REQUEST: AutonomyLevel.AUTONOMOUS,  # Informativo
    InterventionType.PLAN_PROPOSAL: AutonomyLevel.VALIDATION,     # Estratégico
    InterventionType.RISK_ALERT: AutonomyLevel.AUTONOMOUS,        # Urgente
    InterventionType.OPPORTUNITY: AutonomyLevel.PROPOSAL,         # Oportunidad
    InterventionType.WEEKLY_REVIEW: AutonomyLevel.PROPOSAL,       # Informativo+táctico
}

class CooldownPolicy:
    COOLDOWNS = {
        InterventionType.INTENSITY_ADJUST: timedelta(hours=12),
        InterventionType.ADHERENCE_NUDGE: timedelta(hours=24),
        InterventionType.RISK_ALERT: timedelta(hours=6),
        InterventionType.CHECK_IN_REQUEST: timedelta(hours=8),
    }
    MAX_DAILY_INTERVENTIONS = {
        "low_risk": 3,
        "medium_risk": 2,
        "high_risk": 5,  # Alertas de salud
    }

class EscalationPolicy:
    """Define thresholds para escalar nivel de autonomía."""
    # Si una intervención en nivel PROPOSAL no recibe respuesta en N intentos,
    # se escala a AUTONOMOUS (actuar sin esperar)
    AUTO_ESCALATE_AFTER_MISSED = 2

    # Si el usuario rechaza el mismo tipo de intervención N veces seguidas,
    # se baja a FORBIDDEN (no volver a proponer)
    AUTO_DISABLE_AFTER_REJECTIONS = 3

    # Thresholds para escalation por gravedad
    ESCALATION_THRESHOLDS = {
        "risk_state": {
            "high": AutonomyLevel.AUTONOMOUS,   # Riesgo alto → actuar
            "acute": AutonomyLevel.AUTONOMOUS,   # Riesgo agudo → actuar
        },
        "adherence_state": {
            "disconnected": AutonomyLevel.VALIDATION,  # Desconectado → preguntar
        },
        "energy_state": {
            "depleted": AutonomyLevel.PROPOSAL,  # Agotado → proponer con cuidado
        }
    }
```

---

## FASE 2 — Autonomía Táctica

### 2.1 Decisiones Autónomas en Daily Loop

En `backend/app/services/daily_loop_service.py`, añadir:

```python
def _evaluate_autonomous_adjustments(user_id: str, readiness: dict, athlete_state: AthleteState):
    """Evalúa si el sistema debe ajustar el plan autónomamente."""
    adjustments = []

    # Si readiness baja -> bajar intensidad
    if readiness["score"] < 45 and athlete_state.energy_state in ("depleted", "fragile"):
        adjustments.append({
            "type": "intensity_adjustment",
            "action": "lower_intensity",
            "reason": f"Readiness {readiness['score']} con energía {athlete_state.energy_state}"
        })

    # Si streak alta + fatiga acumulada
    if athlete_state.momentum_state == "stalled" and athlete_state.risk_state == "high":
        adjustments.append({
            "type": "recovery_activation",
            "action": "activate_recovery_mode",
            "reason": "Fatiga acumulada con riesgo alto"
        })

    return adjustments
```

### 2.2 Bandeja de Decisiones (Frontend)

Componente `DecisionApprovalBanner.tsx`:
- Muestra propuestas activas de ATLAS
- Botones: "Aplicar" | "Solo hoy" | "No ahora" | "No preguntar más"
- Leve, no obstructivo (banner colapsable)

### 2.3 Timeline de Acciones

Componente `InterventionTimeline.tsx`:
- Línea temporal de intervenciones del día
- Cada item: hora, tipo, autonomous|proposal|manual
- Icono: ⚡autónomo, 💬propuesta, 👤manual
- Expandible para ver motivo

---

## FASE 3 — Voz y Aprendizaje

### 3.1 Communication Style Engine

#### `backend/app/services/communication_style_service.py` (🆕 NUEVO)

```python
class CoachingStyle(str, Enum):
    FIRM_SUPPORTIVE = "firm_supportive"
    CLINICAL_ALERT = "clinical_alert"
    CELEBRATORY_SHARP = "celebratory_sharp"
    STRATEGIC_COACH = "strategic_coach"
    LIGHT_HUMOR = "light_humor"

class CommunicationStyleService:
    """Modula voz, tono, longitud y canal según contexto."""

    def decide_style(athlete_state: AthleteState, intervention_type: str) -> CoachingStyle:
        """Elige estilo según estado y tipo de intervención."""

    def apply_style(message: str, style: CoachingStyle) -> str:
        """Transforma mensaje raw al tono elegido usando IA."""

    def get_user_preference(user_id: str) -> dict:
        """Preferencias aprendidas: tono, longitud, canal, timing."""

    def update_preference(user_id: str, intervention_id: str, outcome: dict):
        """Actualiza preferencia basada en respuesta del usuario."""
```

### 3.2 Preferencias de Interacción

**Enfoque simplificado para v1:** Usar `AtlasMemory` con tipo `interaction_preference` — evita crear tabla nueva:

```python
# Almacenar como memory type=preference
{
    "type": "interaction_preference",
    "content": json.dumps({
        "preferred_style": "firm_supportive",
        "preferred_channel": "app",
        "preferred_timing": "morning",
        "responds_to_challenges": True,
        "humor_tolerance": 0.3,
        "message_fatigue_score": 0.0
    }),
    "tags": ["living_atlas", "interaction_style"],
    "importance": 8
}
```

**Futuro (v2+):** Si el perfil se vuelve complejo, migrar a tabla dedicada:

```python
class UserInteractionProfile(Base):
    __tablename__ = "user_interaction_profiles"

    user_id = Column(String, primary_key=True)
    preferred_style = Column(String, default="firm_supportive")
    preferred_channel = Column(String, default="app")
    preferred_timing = Column(String, default="morning")  # morning|afternoon|evening
    preferred_length = Column(String, default="medium")   # short|medium|long
    responds_to_challenges = Column(Boolean, default=True)
    responds_to_metrics = Column(Boolean, default=True)
    humor_tolerance = Column(Float, default=0.3)  # 0.0-1.0
    message_fatigue_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
```

---

## FASE 4 — Estratega Persistente

### 4.1 Revisiones Mensuales

Nuevo job en scheduler:
```python
async def monthly_narrative_review():
    """(Cada 4 semanas) Revisión narrativa de bloque."""
```

Endpoint nuevo:
```
GET /athlete-state/monthly-review → Revisión mensual narrativa
```

### 4.2 Inferencia de Meseta

En `backend/app/services/analytics_service.py`, extender `detect_plateau()` para que también infiera:
- Meseta de rendimiento
- Meseta de adherencia
- Meseta de motivación

### 4.3 Ajuste de Estrategia de Bloque

En `backend/app/services/athlete_state_service.py`, añadir:
```python
def recommend_next_block(state_history: list[AthleteState]) -> str:
    """Recomienda siguiente bloque: build|consolidate|deload|recover|re-acceleration"""
```

---

## 📦 Resumen de Archivos

### Nuevos Archivos (Backend)

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `backend/app/models/athlete_state.py` | Modelo | Snapshot de estado del atleta |
| `backend/app/models/atlas_event.py` | Modelo | Eventos internos del sistema |
| `backend/app/models/atlas_intervention.py` | Modelo | Registro de intervenciones |
| `backend/app/services/athlete_state_service.py` | Servicio | Cálculo de estado narrativo |
| `backend/app/services/intervention_service.py` | Servicio | Evaluación de triggers y decisión |
| `backend/app/services/event_bus_service.py` | Servicio | Sistema de eventos interno |
| `backend/app/services/intervention_outcome_service.py` | Servicio | Medición de efectividad |
| `backend/app/services/communication_style_service.py` | Servicio | Modulación de voz y tono |
| `backend/app/core/autonomy_policy.py` | Core | Matriz de autonomía y cooldowns |
| `backend/app/api/api_v1/endpoints/athlete_state.py` | Endpoint | API de estado del atleta |
| `backend/app/api/api_v1/endpoints/interventions.py` | Endpoint | API de intervenciones |
| `backend/app/api/api_v1/endpoints/events.py` | Endpoint | API de eventos |

### Archivos Modificados (Backend)

| Archivo | Cambio |
|---------|--------|
| `backend/app/db/base.py` | Importar nuevos modelos |
| `backend/app/models/__init__.py` | Exportar nuevos modelos |
| `backend/app/services/daily_loop_service.py` | Emitir eventos al final del loop, invocar AthleteStateService |
| `backend/app/services/scheduler_service.py` | 6 nuevos jobs de intervención + event processor |
| `backend/app/services/sync_service.py` | Emitir eventos post-sync |
| `backend/app/services/injury_prevention_service.py` | Emitir eventos en alertas |
| `backend/app/services/training_plan_service.py` | Emitir eventos en ajustes |
| `backend/app/services/notification_service.py` | Método `send_intervention()`, tracking de delivery |
| `backend/app/api/api_v1/api.py` | Registrar 3 nuevos routers |

### Nuevos Archivos (Frontend)

| Archivo | Propósito |
|---------|-----------|
| `src/hooks/useAthleteState.ts` | Hook de estado del atleta |
| `src/hooks/useInterventions.ts` | Hook de intervenciones |
| `src/components/atlas-live/AtlasLivePanel.tsx` | Panel principal |
| `src/components/atlas-live/AthleteStateCard.tsx` | Tarjeta de estado |
| `src/components/atlas-live/DailyCadenceIndicator.tsx` | Indicador de ciclo |
| `src/components/atlas-live/InterventionTimeline.tsx` | Timeline de intervenciones |
| `src/components/atlas-live/DecisionApprovalBanner.tsx` | Bandeja de propuestas |
| `src/components/atlas-live/CoachMessage.tsx` | Mensaje con estilo |

### Archivos Modificados (Frontend)

| Archivo | Cambio |
|---------|--------|
| `src/store/atlasStore.ts` | Nuevo estado: athleteState, interventions, dailyCadence |
| `src/services/api.ts` | 6 nuevos métodos de API |
| `src/hooks/useNotifications.ts` | Nuevos tipos WS: state_update, intervention, coach_prompt |

---

## 🗺️ Orden de Implementación Recomendado

### Semana 1 — Fundación
1. `backend/app/core/autonomy_policy.py` — Matriz
2. `backend/app/models/atlas_event.py` — Eventos
3. `backend/app/services/event_bus_service.py` — Bus
4. `backend/app/models/athlete_state.py` — Estado
5. `backend/app/services/athlete_state_service.py` — Cálculo

### Semana 2 — Intervenciones
6. `backend/app/models/atlas_intervention.py` — Intervenciones
7. `backend/app/services/intervention_service.py` — Trigger engine
8. `backend/app/services/intervention_outcome_service.py` — Tracking
9. Endpoints de intervención y estado
10. Modificar servicios existentes para emitir eventos

### Semana 3 — Scheduler + Backend completo
11. Jobs de intervention scan en scheduler
12. Event processor job + cleanup job semanal
13. Modificar daily_loop_service
14. Modificar notification_service

### Semana 4 — Frontend
15. Extender Zustand store
16. Hooks useAthleteState + useInterventions
17. Componentes atlas-live
18. Extender WebSocket y API service
19. Probar ciclo completo

### Semana 5 — Voz + refinamiento
20. CommunicationStyleService (usando AtlasMemory para preferencias)
21. Perfiles de interacción (vía AtlasMemory type=interaction_preference)
22. Ajuste fino de cooldowns y thresholds
23. Testing de integración

---

## 🧪 Estrategia de Testing

### Tests Unitarios Nuevos

```
backend/tests/test_athlete_state_service.py
  - test_compute_state_from_readiness()
  - test_determine_energy_depleted()
  - test_generate_narrative()

backend/tests/test_intervention_service.py
  - test_evaluate_triggers_high_risk()
  - test_score_intervention_low_confidence()
  - test_execute_intervention()

backend/tests/test_autonomy_policy.py
  - test_intensity_adjust_is_autonomous()
  - test_plan_proposal_requires_validation()

backend/tests/test_event_bus.py
  - test_emit_and_process()
```

### Tests de Integración

```
backend/tests/test_living_atlas_integration.py
  - test_daily_loop_triggers_event()
  - test_intervention_leads_to_notification()
  - test_full_cadence_morning_to_evening()
```

---

## ⚙️ Configuración (nuevas vars en Settings)

```python
# En backend/app/core/config.py
LIVING_ATLAS_ENABLED: bool = True
MAX_DAILY_INTERVENTIONS_LOW: int = 3
MAX_DAILY_INTERVENTIONS_MEDIUM: int = 2
MAX_DAILY_INTERVENTIONS_HIGH: int = 5
INTERVENTION_COOLDOWN_HOURS: int = 6
ATHLETE_STATE_REFRESH_CRON: str = "05:30"  # Tras daily loop
MORNING_SCAN_CRON: str = "06:30"
MIDDAY_SCAN_CRON: str = "13:00"
EVENING_SCAN_CRON: str = "20:00"
```

---

## 📊 KPIs para medir éxito de Fase 1

1. **% intervenciones con outcome positivo** — objetivo: >60%
2. **Reducción de sesiones fallidas** — comparar baseline pre/post
3. **Tasa de aceptación de propuestas** — objetivo: >50%
4. **Ratio ruido/utilidad** — <20% de intervenciones ignoradas
5. **Mejora de adherencia semanal** — +5% respecto a baseline
6. **Tiempo hasta re-engagement tras caída** — reducción del 30%

---

> **Documento vivo** — actualizar tras cada fase completada.
> Creado: 2025-03-14
