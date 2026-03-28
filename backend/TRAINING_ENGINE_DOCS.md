# VITALIS Training Engine - Documentación de Arquitectura

## Visión General

El **VITALIS Training Engine** es un sistema modular de generación y adaptación de entrenamientos deportivos basado en principios de ciencia del deporte e inteligencia artificial (reglas + heurísticas).

## Arquitectura Clean/Hexagonal

```
backend/app/training/
├── domain/           # Modelos de dominio puros (reglas de negocio)
├── schemas/          # DTOs Pydantic (validación API)
├── use_cases/        # Casos de uso (lógica de orquestación)
├── api/              # Endpoints FastAPI (capa de presentación)
└── adapters/         # Integraciones externas (wger, Hevy, etc.)
```

## Modelo de Datos

### Jerarquía de Entrenamiento

```
WorkoutPlan (Plan de entrenamiento)
├── user_id, name, description
├── type: STRENGTH | CARDIO | HYBRID
├── periodization: Type
├── blocks: List[ExerciseBlock]
│   ├── exercise_id, exercise_name
│   ├── sets: List[Set]
│   │   ├── reps, weight, rpe_target, rpe_actual
│   │   ├── rest_seconds, tempo, status
│   │   └── feedback: timestamp, notes
│   └── block_order
├── created_at, updated_at, version
└── metadata: JSON (adaptive_params, progression_rules)
```

### Entidades Principales

| Entidad | Descripción | Campos Clave |
|---------|-------------|--------------|
| `WorkoutPlan` | Rutina completa | blocks[], type, periodization |
| `ExerciseBlock` | Bloque de ejercicio | exercise_id, sets[], order |
| `Set` | Serie individual | reps, weight, rpe_target, rpe_actual, status |
| `Exercise` | Catálogo de ejercicios | name, muscle_groups, equipment, difficulty |
| `WorkoutFeedback` | Feedback post-entreno | plan_id, difficulty_rating, energy_rating, notes |

## Principios de Ciencia del Deporte Implementados

### 1. RPE (Rate of Perceived Exertion)

**Escala 1-10:**
- 1-2: Muy fácil (recuperación activa)
- 3-4: Fácil (aeróbico base)
- 5-6: Moderado (umbral aeróbico)
- 7-8: Difícil (umbral anaeróbico)
- 9-10: Máximo esfuerzo

**Implementación:**
```python
class Set:
    rpe_target: float  # RPE planificado
    rpe_actual: Optional[float]  # RPE real reportado
    
    def calculate_rir(self) -> float:
        """Reps in Reserve - estimación basada en RPE"""
        return 10 - self.rpe_actual
```

### 2. Progresión Adaptativa

**Reglas de Ajuste:**

| Desviación RPE | Acción | Ajuste |
|---------------|--------|--------|
| rpe_actual > rpe_target + 1.5 | Reducir intensidad | -5% peso o -1 serie |
| rpe_actual < rpe_target - 1.0 | Aumentar intensidad | +2.5% peso o +1 rep |
| rpe_actual ≈ rpe_target ± 0.5 | Mantener | Sin cambios |

### 3. Fatiga Acumulada (ACWR)

**Ratio Aguda/Crónica:**
- Acute Load: Últimos 7 días
- Chronic Load: Últimos 28 días (promedio semanal × 4)
- Zona óptima: 0.8 - 1.3
- Zona de riesgo: > 1.5

### 4. Periodización

**Tipos Soportados:**
- **LINEAR**: Volumen decreciente, intensidad creciente
- **UNDULATING**: Variación diaria/semanal de carga
- **BLOCK**: Bloques de 3-6 semanas enfocados
- **POLARIZED**: 80% baja intensidad / 20% alta intensidad

## Flujo de Generación de Entrenamiento

```
┌─────────────────────────────────────────────────────────┐
│  INPUT: user_id, readiness_score, preferences, history  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  CONTEXT BUILDER: Recolectar datos del atleta            │
│  - Readiness últimos 7 días                              │
│  - Historial de entrenamiento (últimas 4 semanas)      │
│  - Biométricos (FC reposo, HRV, sueño)                   │
│  - Preferencias de usuario                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  ADAPTIVE ENGINE: Calcular parámetros adaptativos        │
│  - Si readiness < 60: Reducir volumen 20%                │
│  - Si HRV < baseline -10%: Reducir intensidad            │
│  - Si ACWR > 1.3: Ajustar progresión                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  WORKOUT GENERATOR: Crear estructura del plan            │
│  - Seleccionar ejercicios según objetivo                 │
│  - Distribuir volumen según periodización                  │
│  - Asignar sets/reps/pesos basados en 1RM estimado        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  OUTPUT: WorkoutPlan con blocks[] y sets[]               │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints

### Generación y Gestión

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/training/workouts/generate` | Generar nueva rutina |
| POST | `/api/v1/training/workouts/adapt` | Adaptar rutina existente |
| GET | `/api/v1/training/workouts/{id}` | Obtener plan específico |
| GET | `/api/v1/training/workouts` | Listar planes del usuario |
| DELETE | `/api/v1/training/workouts/{id}` | Eliminar plan |

### Feedback y Adaptación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/training/sets/{set_id}/feedback` | Registrar RPE real de una serie |
| POST | `/api/v1/training/workouts/{id}/complete` | Completar entrenamiento |
| POST | `/api/v1/training/feedback` | Feedback general post-entreno |

### Integraciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/training/integration/wger` | Importar desde wger.de |
| POST | `/api/v1/training/integration/hevy` | Sincronizar con Hevy |
| POST | `/api/v1/training/integration/garmin` | Exportar a Garmin |

## Adaptador de Integraciones

### Patrón Adapter

```python
class WorkoutExporter(ABC):
    @abstractmethod
    def export(self, workout: WorkoutPlan) -> ExportedWorkout:
        pass

class GarminExporter(WorkoutExporter):
    def export(self, workout: WorkoutPlan) -> GarminWorkout:
        # Transformar a formato Garmin Connect
        pass

class HevyExporter(WorkoutExporter):
    def export(self, workout: WorkoutPlan) -> HevyRoutine:
        # Transformar a formato Hevy
        pass
```

## Sistema de Feedback Loop

### Comparación Plan vs Real

```python
def analyze_workout_completion(plan: WorkoutPlan, feedback: WorkoutFeedback):
    deviations = []
    
    for block in plan.blocks:
        for set in block.sets:
            if set.rpe_actual:
                deviation = set.rpe_actual - set.rpe_target
                if abs(deviation) > 1.0:
                    deviations.append({
                        'exercise': block.exercise_name,
                        'set': set.order,
                        'deviation': deviation,
                        'action': calculate_adjustment(deviation)
                    })
    
    return deviations
```

### Aprendizaje del Sistema

El motor adaptativo utiliza el feedback para ajustar:

1. **Pesos estimados**: Si el usuario reporta RPE 6 en un peso planificado para RPE 8, el sistema subestima su capacidad y ajusta el 1RM estimado.

2. **Recuperación individual**: Se mide el tiempo entre sesiones del mismo grupo muscular y se ajustan los descansos.

3. **Preferencias implícitas**: Si el usuario consistentemente omite ciertos ejercicios, el sistema reduce su prioridad en futuras generaciones.

## Implementación de Reglas de Negocio

### Claves de Decisión

```python
class AdaptiveRules:
    """Reglas heurísticas para adaptación de entrenamientos"""
    
    @staticmethod
    def should_reduce_volume(readiness: float, acwr: float) -> bool:
        return readiness < 60 or acwr > 1.3
    
    @staticmethod
    def should_reduce_intensity(hrv: float, hrv_baseline: float) -> bool:
        return hrv < (hrv_baseline * 0.9)
    
    @staticmethod
    def calculate_progression_rate(
        completed_workouts: int,
        success_rate: float
    ) -> float:
        """
        Tasa de progresión: 2.5% conservador, 5% agresivo
        """
        if completed_workouts < 4:
            return 0.0  # Fase de aprendizaje
        elif success_rate > 0.8:
            return 0.05  # Progresión agresiva
        elif success_rate > 0.6:
            return 0.025  # Progresión conservadora
        else:
            return -0.05  # Regresión por fatiga
```

## Base de Datos

### Tablas Principales

```sql
-- Planes de entrenamiento
CREATE TABLE workout_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,  -- STRENGTH, CARDIO, HYBRID
    periodization TEXT,  -- LINEAR, UNDULATING, BLOCK, POLARIZED
    blocks JSON NOT NULL,  -- Array de ExerciseBlock
    status TEXT DEFAULT 'active',  -- active, completed, archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    metadata JSON  -- adaptive_params, progression_rules
);

-- Ejercicios base
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    muscle_groups JSON NOT NULL,  -- Array de MuscleGroup
    equipment TEXT,
    difficulty TEXT,  -- beginner, intermediate, advanced
    exercise_type TEXT,  -- compound, isolation
    description TEXT,
    video_url TEXT
);

-- Feedback de entrenamientos
CREATE TABLE workout_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_plan_id INTEGER REFERENCES workout_plans(id),
    user_id TEXT NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    difficulty_rating INTEGER,  -- 1-10
    energy_rating INTEGER,  -- 1-10
    overall_rpe INTEGER,  -- 1-10
    notes TEXT,
    soreness_muscles JSON,  -- Array de grupos musculares con dolor
    sleep_quality INTEGER,  -- 1-5
    stress_level INTEGER  -- 1-10
);
```

## Seguridad y Validaciones

### Validaciones de Datos

- **RPE**: 1.0 - 10.0
- **Reps**: 1 - 100
- **Peso**: > 0
- **Rest**: 0 - 600 segundos
- **Tempo**: Formato "X-X-X" (eccentric-isometric-concentric)

### Reglas de Negocio

- Máximo 20 sets por ejercicio
- Máximo 10 ejercicios por sesión
- Mínimo 48h de descanso entre sesiones del mismo grupo muscular
- Máximo 5 sesiones de fuerza por semana

## Próximos Pasos / Roadmap

### Fase 2 (Próxima)
- [ ] Implementar algoritmos ML para predicción de 1RM
- [ ] Sistema de periodización automática
- [ ] Integración con Garmin Connect IQ
- [ ] Exportación a TrainingPeaks

### Fase 3 (Futuro)
- [ ] Recomendaciones nutricionales basadas en carga
- [ ] Detección de overreaching con HRV
- [ ] Planes de rehabilitación post-lesión
- [ ] Comunidad y competiciones

---

## Autor
Dashboard-Vitalis Team

## Versión
1.0.0 - Fase 1 (MVP)
