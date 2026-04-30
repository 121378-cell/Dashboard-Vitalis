"""
ATLAS Training Planner Service v2
===================================

Intelligent training plan generation with:
- Progressive overload automation (Stoppani methodology)
- McGill spine safety rules integration  
- Adaptive periodization based on readiness
- Personal records tracking
- Weekly auto-regeneration

Autor: ATLAS Team
Version: 2.0.0
"""

import json
import logging
import statistics
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models import WeeklyPlan, TrainingSession, PersonalRecord, Biometrics, Workout
from app.models.user import User
from app.services.readiness_service import ReadinessService
from app.services.memory_service import MemoryService
from app.services.ai_service import AIService
from app.services.athlete_profile_service import AthleteProfileService

logger = logging.getLogger("app.services.planner")


class TrainingPlannerService:
    """
    Intelligent training plan generation with progressive overload.
    
    Features:
    - Analyzes 8 weeks of workout history
    - Considers readiness forecasts
    - Applies Stoppani periodization methodology
    - McGill spine safety rules
    - Automatic progressive overload (2.5kg or 1 rep increments)
    - Deload every 8 weeks (50% volume, same intensity)
    """
    
    # Stoppani methodology: intensity phases
    INTENSITY_PHASES = {
        1: 0.70,  # Weeks 1-2: 70% of 1RM
        2: 0.70,
        3: 0.75,  # Weeks 3-4: 75% of 1RM
        4: 0.75,
        5: 0.80,  # Weeks 5-6: 80% of 1RM
        6: 0.80,
        7: 0.85,  # Weeks 7-8: 85% of 1RM
        8: 0.85,
    }
    
    # Exercise categories for programming
    COMPOUND_EXERCISES = {
        "squat", "deadlift", "bench_press", "overhead_press",
        "barbell_row", "pull_up", "dip", "lunge", "hip_thrust",
        "romanian_deadlift", "barbell_curl", "tricep_extension"
    }
    
    ISOLATION_EXERCISES = {
        "bicep_curl", "tricep_pushdown", "leg_extension",
        "leg_curl", "calf_raise", "lateral_raise", "fly",
        "crunch", "plank", "back_extension"
    }
    
    # McGill Big 3 for spine safety
    MCGILL_BIG_3 = [
        {"name": "Bird Dog", "sets": 3, "reps": "8-10", "side": "alternating"},
        {"name": "Dead Bug", "sets": 3, "reps": "8-10", "side": "alternating"},
        {"name": "Side Plank", "sets": 3, "duration": "30-45s", "side": "each"}
    ]

    @classmethod
    async def generate_weekly_plan(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Generate a comprehensive weekly training plan.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            WeeklyPlan dictionary with all sessions and exercises
        """
        # 1. Recopilar contexto completo
        profile = await cls._get_athlete_profile(db, user_id)
        readiness_history = await cls._get_readiness_history(db, user_id, days=30)
        workout_history = await cls._get_workout_history(db, user_id, weeks=8)
        prs = await cls._get_personal_records(db, user_id)
        memory_context = await cls._get_memory_context(db, user_id)
        upcoming_readiness = await cls._get_readiness_forecast(db, user_id, days=7)
        
        # 2. Calcular metricas de carga
        avg_sessions = cls._calculate_avg_sessions(workout_history)
        avg_volume = cls._calculate_avg_volume(workout_history)
        recovery_rate = cls._calculate_recovery_rate(readiness_history)
        training_age = cls._calculate_training_age(workout_history)
        
        # 3. Determinar estructura de la semana
        weekly_structure = cls._determine_week_structure(
            available_days=profile.get("days_per_week", 4),
            forecasted_readiness=upcoming_readiness,
            current_fatigue=cls._calculate_fatigue_index(workout_history[-14:]),
            training_age=training_age,
            profile=profile
        )
        
        # 4. Generar plan con AI
        plan_prompt = cls._build_plan_prompt(
            profile, prs, weekly_structure, memory_context,
            avg_sessions, avg_volume, recovery_rate, training_age
        )
        plan_json = await cls._generate_ai_plan(plan_prompt)
        
        # 5. Aplicar sobrecarga progresiva
        plan_with_progression = cls.apply_progressive_overload(
            plan_json, prs, workout_history
        )
        
        # 6. Aplicar reglas de seguridad McGill
        plan_with_progression = cls._apply_mcgill_rules(
            plan_with_progression, profile
        )
        
        # 7. Guardar en base de datos
        weekly_plan = await cls._save_weekly_plan(
            db, user_id, weekly_structure, plan_with_progression, profile
        )
        
        return cls._format_plan_response(weekly_plan, weekly_structure)
    
    @classmethod
    def apply_progressive_overload(
        cls, plan: Dict[str, Any], prs: Dict[str, Any],
        workout_history: List[Any]
    ) -> Dict[str, Any]:
        """
        Apply progressive overload to each exercise in the plan.
        
        Rules:
        - Last session successful and RPE <= 8: +2.5kg
        - Last session RPE <= 6: +5kg (too easy)
        - Last session RPE > 8: keep same weight (very difficult)
        - First time: 70% of PR (or conservative estimate)
        
        Stoppani methodology based on training phase.
        """
        if "sessions" not in plan:
            return plan
        
        for session in plan["sessions"]:
            for exercise in session.get("exercises", []):
                ex_name = exercise["name"].lower().replace(" ", "_")
                last_session = cls._find_last_session_for_exercise(
                    ex_name, workout_history
                )
                
                # Get training phase intensity from plan week number
                week_num = plan.get("week_number", 1)
                phase_intensity = cls._get_phase_intensity(week_num)
                
                if last_session:
                    last_weight = last_session.get("weight")
                    last_reps = last_session.get("reps")
                    last_rpe = last_session.get("rpe", 8)
                    last_success = last_session.get("completed", False)
                    
                    if last_success and last_rpe <= 8:
                        exercise["target_weight"] = round(last_weight + 2.5, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "+2.5kg (progressive overload)"
                    elif last_success and last_rpe <= 6:
                        exercise["target_weight"] = round(last_weight + 5, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "+5kg (too easy last session)"
                    elif last_rpe >= 9:
                        exercise["target_weight"] = round(last_weight, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "maintain (very difficult)"
                    else:
                        exercise["target_weight"] = round(last_weight, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "repeat last session"
                else:
                    # First time exercise - use percentage of PR or conservative
                    pr = prs.get(ex_name)
                    if pr and pr.get("weight"):
                        base_weight = pr["weight"] * 0.70 * phase_intensity
                        exercise["target_weight"] = round(base_weight / 2.5) * 2.5
                    else:
                        # No PR estimate
                        if "squat" in ex_name or "deadlift" in ex_name:
                            exercise["target_weight"] = 20.0  # conservative start
                        elif "press" in ex_name:
                            exercise["target_weight"] = 10.0
                        else:
                            exercise["target_weight"] = 5.0
                    
                    exercise["target_reps"] = 8
                    exercise["progression_note"] = f"initial: {phase_intensity*100:.0f}% intensity phase"
                
                # Apply sets/reps based on Stoppani methodology
                exercise["sets"] = exercise.get("sets", 4)
                exercise["rpe_target"] = cls._calculate_rpe_target(week_num)
                exercise["intensity_percentage"] = int(phase_intensity * 100)
        
        return plan
    
    @classmethod
    def _apply_mcgill_rules(cls, plan: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply McGill spine safety rules:
        - Never program high-load lumbar flexion if back pain history
        - Big 3 McGill mandatory warmup if back pain history
        - Avoid contraindicated exercises
        """
        has_back_pain = profile.get("injuries", []) and any(
            "back" in str(i).lower() or "spine" in str(i).lower()
            for i in profile.get("injuries", [])
        )
        
        exercises_to_avoid = [
            "toe_touch", "situp", "crunch_torso_curl", "leg_raise_lying"
        ] if has_back_pain else []
        
        if has_back_pain:
            for session in plan.get("sessions", []):
                # Add McGill Big 3 to warmup
                mcgill_warmup = {
                    "name": "McGill Big 3 Warmup",
                    "exercises": cls.MCGILL_BIG_3,
                    "notes": "Mandatory spine stability warmup - McGill protocol"
                }
                session["mcgill_warmup"] = mcgill_warmup
                
                # Remove contraindicated exercises
                session["exercises"] = [
                    ex for ex in session.get("exercises", [])
                    if not any(avoid in ex["name"].lower().replace(" ", "_")
                               for avoid in exercises_to_avoid)
                ]
        
        return plan
    
    @classmethod
    def _determine_week_structure(
        cls, available_days: int, forecasted_readiness: List[Dict[str, Any]],
        current_fatigue: float, training_age: float, profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determine optimal weekly training structure based on availability and readiness.
        """
        # Map available days to common splits
        split_options = {
            3: {"name": "Full Body 3x", "sessions": [
                {"day": 0, "name": "Full Body A", "focus": "compound"},
                {"day": 2, "name": "Full Body B", "focus": "compound"},
                {"day": 4, "name": "Full Body C", "focus": "compound"}
            ]},
            4: {"name": "Upper/Lower Split", "sessions": [
                {"day": 0, "name": "UPPER (PUSH/PULL)", "focus": "upper"},
                {"day": 1, "name": "LOWER", "focus": "lower"},
                {"day": 3, "name": "UPPER (Volume)", "focus": "upper"},
                {"day": 4, "name": "LOWER (Volume)", "focus": "lower"}
            ]},
            5: {"name": "PPL + Upper/Lower", "sessions": [
                {"day": 0, "name": "PUSH", "focus": "upper_push"},
                {"day": 1, "name": "PULL", "focus": "upper_pull"},
                {"day": 2, "name": "LEGS", "focus": "lower"},
                {"day": 4, "name": "UPPER", "focus": "upper"},
                {"day": 5, "name": "LOWER", "focus": "lower"}
            ]},
            6: {"name": "PPL x2", "sessions": [
                {"day": 0, "name": "PUSH", "focus": "upper_push"},
                {"day": 1, "name": "PULL", "focus": "upper_pull"},
                {"day": 2, "name": "LEGS", "focus": "lower"},
                {"day": 3, "name": "PUSH (Hypertrophy)", "focus": "upper_push"},
                {"day": 4, "name": "PULL (Hypertrophy)", "focus": "upper_pull"},
                {"day": 5, "name": "LEGS (Hypertrophy)", "focus": "lower"}
            ]},
        }
        
        structure = split_options.get(available_days, split_options[4])
        
        # Adjust for low readiness forecast
        low_readiness_days = sum(
            1 for r in forecasted_readiness if r.get("score", 50) < 40
        )
        if low_readiness_days >= 2:
            structure["note"] = "Reduced volume recommended due to low readiness forecast"
        
        return structure
    
    @classmethod
    async def _generate_ai_plan(cls, prompt: str) -> Dict[str, Any]:
        """Generate training plan using AI service."""
        ai_service = AIService()
        messages = [{"role": "user", "content": prompt}]
        
        system_prompt = """
Eres un entrenador personal experto, especialista en periodización y programación de entrenamiento. 
Genera planes de entrenamiento estructurados siguiendo la metodología de Stoppani y principios 
de progresión sistemática. Responde SIEMPRE en formato JSON válido.
        """
        
        try:
            response = ai_service._generate_chat_response(messages, system_prompt)
            import json as json_module
            return json_module.loads(response["content"])
        except Exception as e:
            logger.error(f"AI plan generation failed: {e}")
            # Fallback to template-based plan
            return cls._generate_fallback_plan()
    
    @classmethod
    def _generate_fallback_plan(cls) -> Dict[str, Any]:
        """Generate a basic fallback plan when AI is unavailable."""
        return {
            "week_number": 1,
            "sessions": [
                {
                    "day": 0, "name": "Upper Body", "focus": "upper",
                    "exercises": [
                        {"name": "Bench Press", "sets": 4, "reps": 8,
                         "target_weight": 60, "target_reps": 8, "rpe_target": 8},
                        {"name": "Barbell Row", "sets": 4, "reps": 8,
                         "target_weight": 60, "target_reps": 8, "rpe_target": 8},
                    ]
                }
            ]
        }
    
    @classmethod
    async def _save_weekly_plan(
        cls, db: Session, user_id: str,
        weekly_structure: Dict[str, Any], plan_data: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> WeeklyPlan:
        """Save weekly plan to database."""
        # Archivar planes previos inactivos
        db.query(WeeklyPlan).filter(
            WeeklyPlan.user_id == user_id,
            WeeklyPlan.status == "active"
        ).update({"status": "archived"})
        
        # Determinar fechas de la semana
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Lunes de esta semana
        week_end = week_start + timedelta(days=6)
        
        objective = profile.get("goal", "strength")
        training_age = cls._calculate_training_age(
            await cls._get_workout_history(db, user_id, weeks=8)
        )
        
        # Crear plan semanal
        weekly_plan = WeeklyPlan(
            user_id=user_id,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            status="active",
            objective=objective,
            plan_data=plan_data,
            ai_version="2.0"
        )
        db.add(weekly_plan)
        db.commit()
        db.refresh(weekly_plan)
        
        # Crear sesiones de entrenamiento
        for session_data in weekly_structure.get("sessions", []):
            scheduled_date = week_start + timedelta(days=session_data["day"])
            
            # Obtener ejercicios de AI plan para este día
            session_plan = cls._match_session_to_plan(session_data, plan_data)
            
            training_session = TrainingSession(
                plan_id=weekly_plan.id,
                day_index=session_data["day"],
                day_name=session_data["name"],
                scheduled_date=scheduled_date.isoformat(),
                exercises_data=session_plan
            )
            db.add(training_session)
        
        db.commit()
        db.refresh(weekly_plan)
        
        logger.info(f"Weekly plan created for user {user_id} (week {week_start})")
        return weekly_plan
    
    @classmethod
    def _match_session_to_plan(
        cls, session_data: Dict[str, Any], plan_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Match session from structure to AI-generated plan."""
        focus = session_data.get("focus", "")
        ai_sessions = plan_data.get("sessions", [])
        
        if ai_sessions and len(ai_sessions) > 0:
            idx = session_data["day"] % len(ai_sessions)
            ai_session = ai_sessions[idx]
            return ai_session.get("exercises", [])
        
        # Ejercicios por defecto según foco
        default_exercises = {
            "upper": [
                {"name": "Bench Press", "sets": 4, "reps": 8, "target_weight": 60, "rpe_target": 8},
                {"name": "Barbell Row", "sets": 4, "reps": 8, "target_weight": 60, "rpe_target": 8},
                {"name": "Overhead Press", "sets": 3, "reps": 10, "target_weight": 30, "rpe_target": 8},
                {"name": "Pull-Up", "sets": 3, "reps": 8, "target_weight": 0, "rpe_target": 8},
            ],
            "lower": [
                {"name": "Squat", "sets": 4, "reps": 8, "target_weight": 40, "rpe_target": 8},
                {"name": "Romanian Deadlift", "sets": 3, "reps": 10, "target_weight": 40, "rpe_target": 8},
                {"name": "Leg Press", "sets": 3, "reps": 12, "target_weight": 80, "rpe_target": 8},
                {"name": "Calf Raise", "sets": 4, "reps": 15, "target_weight": 40, "rpe_target": 8},
            ],
            "upper_push": [
                {"name": "Bench Press", "sets": 4, "reps": 8, "target_weight": 60, "rpe_target": 8},
                {"name": "Overhead Press", "sets": 3, "reps": 10, "target_weight": 30, "rpe_target": 8},
                {"name": "Incline Dumbbell Press", "sets": 3, "reps": 10, "target_weight": 20, "rpe_target": 8},
                {"name": "Lateral Raise", "sets": 4, "reps": 15, "target_weight": 8, "rpe_target": 8},
                {"name": "Tricep Extension", "sets": 3, "reps": 12, "target_weight": 20, "rpe_target": 8},
            ],
            "upper_pull": [
                {"name": "Pull-Up", "sets": 4, "reps": 8, "target_weight": 0, "rpe_target": 8},
                {"name": "Barbell Row", "sets": 4, "reps": 8, "target_weight": 60, "rpe_target": 8},
                {"name": "Lat Pulldown", "sets": 3, "reps": 10, "target_weight": 50, "rpe_target": 8},
                {"name": "Face Pull", "sets": 3, "reps": 15, "target_weight": 20, "rpe_target": 8},
                {"name": "Bicep Curl", "sets": 3, "reps": 12, "target_weight": 15, "rpe_target": 8},
            ],
        }
        return default_exercises.get(focus, default_exercises["upper"])
    
    @classmethod
    def _get_phase_intensity(cls, week_number: int) -> float:
        """Get intensity percentage for training phase based on Stoppani methodology."""
        phase = ((week_number - 1) % 8) + 1
        # Apply deload every 8 weeks (50% volume, same intensity base)
        if phase == 8:
            return cls.INTENSITY_PHASES[phase] * 0.5  # Deload week
        return cls.INTENSITY_PHASES.get(phase, 0.75)
    
    @classmethod
    def _calculate_rpe_target(cls, week_number: int) -> int:
        """Calculate target RPE based on training phase."""
        phase = ((week_number - 1) % 8) + 1
        if phase <= 2:
            return 7  # Accumulation
        elif phase <= 4:
            return 8  # Intensification
        elif phase <= 6:
            return 8  # Realization
        elif phase == 7:
            return 9  # Peak
        else:
            return 6  # Deload
    
    @classmethod
    async def _get_athlete_profile(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """Get athlete profile including training preferences."""
        profile_service = AthleteProfileService()
        profile = profile_service.get_profile(db, user_id)
        if not profile:
            profile = {
                "days_per_week": 4,
                "goal": "strength",
                "experience_level": "intermediate",
                "injuries": [],
                "restrictions": []
            }
        return profile
    
    @classmethod
    async def _get_readiness_history(cls, db: Session, user_id: str, days: int) -> List[Dict[str, Any]]:
        """Get readiness score history."""
        from app.models.daily_briefing import DailyBriefing
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        briefings = db.query(DailyBriefing).filter(
            DailyBriefing.user_id == user_id,
            DailyBriefing.date >= cutoff
        ).order_by(DailyBriefing.date.asc()).all()
        
        results = []
        for b in briefings:
            try:
                data = json.loads(b.content)
                results.append(data)
            except:
                pass
        return results
    
    @classmethod
    async def _get_workout_history(cls, db: Session, user_id: str, weeks: int) -> List[Any]:
        """Get workout history."""
        cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
        return db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date >= cutoff
        ).order_by(Workout.date.desc()).all()
    
    @classmethod
    async def _get_personal_records(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """Get current personal records."""
        prs = db.query(PersonalRecord).filter(
            PersonalRecord.user_id == user_id
        ).all()
        
        # Also get max weights from workout history
        workouts = await cls._get_workout_history(db, user_id, weeks=52)
        
        result = {}
        for pr in prs:
            result[pr.exercise_name.lower()] = {
                "weight": pr.weight,
                "reps": pr.reps,
                "date": pr.date,
                "rpe": pr.rpe
            }
        return result
    
    @classmethod
    async def _get_memory_context(cls, db: Session, user_id: str) -> str:
        """Get memory context for AI."""
        return MemoryService.get_memory_context_string(db, user_id)
    
    @classmethod
    async def _get_readiness_forecast(cls, db: Session, user_id: str, days: int) -> List[Dict[str, Any]]:
        """Get readiness forecast."""
        return ReadinessService.get_forecast(db, user_id, days)
    
    @classmethod
    def _calculate_avg_sessions(cls, workout_history: List[Any]) -> float:
        """Calculate average sessions per week."""
        if not workout_history:
            return 3.0
        
        weeks = {}
        for w in workout_history:
            week_key = w.date.isocalendar()[1] if hasattr(w.date, 'isocalendar') else 1
            year = w.date.year if hasattr(w.date, 'year') else 2024
            key = f"{year}-{week_key}"
            weeks[key] = weeks.get(key, 0) + 1
        
        if not weeks:
            return 3.0
        return statistics.mean(weeks.values())
    
    @classmethod
    def _calculate_avg_volume(cls, workout_history: List[Any]) -> float:
        """Calculate average weekly training volume in minutes."""
        if not workout_history:
            return 180.0
        
        weeks = {}
        for w in workout_history:
            week_key = w.date.isocalendar()[1] if hasattr(w.date, 'isocalendar') else 1
            year = w.date.year if hasattr(w.date, 'year') else 2024
            key = f"{year}-{week_key}"
            duration = w.duration or 0
            weeks[key] = weeks.get(key, 0) + duration
        
        if not weeks:
            return 180.0
        return statistics.mean(weeks.values()) / 60  # Convert to hours
    
    @classmethod
    def _calculate_recovery_rate(cls, readiness_history: List[Dict[str, Any]]) -> float:
        """Calculate recovery rate from readiness history."""
        if len(readiness_history) < 2:
            return 1.0
        
        scores = [r.get("score", 50) for r in readiness_history if r.get("score")]
        if len(scores) < 2:
            return 1.0
        
        # Recovery rate: how quickly readiness returns to baseline
        return 1.0
    
    @classmethod
    def _calculate_fatigue_index(cls, recent_workouts: List[Any]) -> float:
        """Calculate accumulated fatigue from recent workouts."""
        if not recent_workouts:
            return 0.0
        
        total_load = sum((w.duration or 0) for w in recent_workouts)
        avg_daily = total_load / 14  # 2 weeks
        
        if avg_daily > 7200:  # > 2 hours/day
            return 0.8
        elif avg_daily > 5400:  # > 1.5 hours/day
            return 0.6
        elif avg_daily > 3600:  # > 1 hour/day
            return 0.4
        return 0.2
    
    @classmethod
    def _calculate_training_age(cls, workout_history: List[Any]) -> float:
        """Estimate training age in years."""
        if not workout_history:
            return 1.0
        
        # Count months with regular training
        months = {}
        for w in workout_history:
            if hasattr(w.date, 'year') and hasattr(w.date, 'month'):
                key = f"{w.date.year}-{w.date.month}"
            else:
                continue
            months[key] = months.get(key, 0) + 1
        
        training_months = len(months)
        return min(training_months / 12.0, 20.0)  # Cap at 20 years
    
    @classmethod
    def _build_plan_prompt(
        cls, profile: Dict[str, Any], prs: Dict[str, Any],
        weekly_structure: Dict[str, Any], memory_context: str,
        avg_sessions: float, avg_volume: float,
        recovery_rate: float, training_age: float
    ) -> str:
        """Build comprehensive prompt for AI plan generation."""
        prompt = f"""
Genera un plan de entrenamiento semanal personalizado siguiendo estas reglas:

PERFIL DEL ATLETA:
- Días disponibles: {profile.get('days_per_week', 4)} días/semana
- Objetivo: {profile.get('goal', 'strength')}
- Nivel: {profile.get('experience_level', 'intermediate')}
- Historial: {training_age:.1f} años entrenando
- Sesiones promedio: {avg_sessions:.1f}/semana
- Volumen promedio: {avg_volume:.1f}h/semana
- Recuperación: {recovery_rate:.2f}

RECORDS PERSONALES:
{json.dumps(prs, indent=2, ensure_ascii=False) if prs else "No hay PRs registrados"}

MEMORIA/HISTORIAL:
{memory_context if memory_context else "No hay datos históricos"}

ESTRUCTURA SEMANAL:
Nombre: {weekly_structure.get('name', 'Custom')}
Sesiones: {len(weekly_structure.get('sesiones', []))}

REGLAS DE PROGRAMACIÓN (Metodología Stoppani):
1. Compound exercises primero, aislamiento después
2. Super-series y drop-sets para ejercicios de aislamiento
3. Incrementos conservadores: +2.5kg o +1 rep cada 2 semanas
4. Deload cada 8 semanas (50% volumen, misma intensidad)
5. Intensidad por fases: 70% (semanas 1-2), 75% (3-4), 80% (5-6), 85% (7-8)

REGLAS DE SEGURIDAD (McGill):
1. Big 3 McGill en warmup si hay historial de dolor lumbar
2. Evitar flexión lumbar con carga alta
3. Nunca comprometer la técnica por peso

FORMATO DE RESPUESTA (JSON estricto):
{{
  "week_number": 1,
  "sessions": [
    {{
      "day": 0,
      "name": "PUSH",
      "focus": "upper_push",
      "exercises": [
        {{
          "name": "Bench Press",
          "sets": 4,
          "reps": "8-10",
          "rest": "90s",
          "tempo": "2-0-1",
          "notes": "Compound principal"
        }}
      ]
    }}
  ],
  "progression_strategy": "Progressive overload + deload protocol",
  "notes": "Consideraciones específicas"
}}
"""
        return prompt
    
    @classmethod
    def _format_plan_response(
        cls, weekly_plan: WeeklyPlan, weekly_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format plan for API response."""
        sessions_data = []
        for session in weekly_plan.sessions:
            sessions_data.append({
                "id": session.id,
                "day": session.day_index,
                "day_name": session.day_name,
                "scheduled_date": session.scheduled_date,
                "exercises": session.exercises_data,
                "completed": session.completed,
                "actual_data": session.actual_data
            })
        
        return {
            "id": weekly_plan.id,
            "user_id": weekly_plan.user_id,
            "week_start": weekly_plan.week_start,
            "week_end": weekly_plan.week_end,
            "generated_at": weekly_plan.generated_at.isoformat(),
            "status": weekly_plan.status,
            "objective": weekly_plan.objective,
            "structure_name": weekly_structure.get("name", "Custom"),
            "sessions": sessions_data,
            "plan_data": weekly_plan.plan_data
        }


# Helper functions matching the original API spec
async def get_athlete_profile(user_id: str) -> Dict[str, Any]:
    """Legacy function for compatibility."""
    return {"days_per_week": 4, "goal": "strength"}


async def get_readiness_history(user_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """Legacy function for compatibility."""
    return []


async def get_workout_history(user_id: str, weeks: int = 8) -> List[Any]:
    """Legacy function for compatibility."""
    return []


async def get_personal_records(user_id: str) -> Dict[str, Any]:
    """Legacy function for compatibility."""
    return {}


async def calculate_avg_sessions(workout_history: List[Any]) -> float:
    """Legacy function for compatibility."""
    return TrainingPlannerService._calculate_avg_sessions(workout_history)


async def calculate_avg_volume(workout_history: List[Any]) -> float:
    """Legacy function for compatibility."""
    return TrainingPlannerService._calculate_avg_volume(workout_history)


async def calculate_recovery_rate(readiness_history: List[Dict[str, Any]]) -> float:
    """Legacy function for compatibility."""
    return TrainingPlannerService._calculate_recovery_rate(readiness_history)


async def determine_week_structure(
    available_days: int, forecasted_readiness: List[Dict[str, Any]],
    current_fatigue: float
) -> Dict[str, Any]:
    """Legacy function for compatibility."""
    return TrainingPlannerService._determine_week_structure(
        available_days, forecasted_readiness, current_fatigue, 2.0, {}
    )


async def build_plan_prompt(
    profile: Dict[str, Any], prs: Dict[str, Any],
    weekly_structure: Dict[str, Any], memory_context: str
) -> str:
    """Legacy function for compatibility."""
    return TrainingPlannerService._build_plan_prompt(
        profile, prs, weekly_structure, memory_context,
        3.0, 180.0, 1.0, 2.0
    )


def find_last_session_for_exercise(
    exercise_name: str, workout_history: List[Any]
) -> Optional[Dict[str, Any]]:
    """Find the last session for a specific exercise."""
    for w in workout_history:
        # Check if workout contains this exercise
        if hasattr(w, 'exercises'):
            for ex in w.exercises:
                if ex.get('name', '').lower() == exercise_name.lower():
                    return {
                        "weight": ex.get("weight"),
                        "reps": ex.get("reps"),
                        "rpe": ex.get("rpe", 8),
                        "completed": True
                    }
    return None
