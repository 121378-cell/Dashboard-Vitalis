"""
ATLAS Training Planner Service v2
==================================

Intelligent training plan generation with:
- Progressive overload automation (Stoppani methodology)
- McGill spine safety rules integration
- Adaptive periodization based on readiness
- Personal records tracking
- Weekly auto-regeneration
- Supersets and drop sets for isolation exercises
- Automatic deload every 8 weeks

Autor: ATLAS Team
Version: 2.0.0
"""

import json
import logging
import statistics
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.models.training_plan import WeeklyPlan as PlanWeeklyPlan, PlanSession as PlanSessionModel, PersonalRecord as PRModel
from app.models.workout import Workout
from app.services.readiness_service import ReadinessService
from app.services.memory_service import MemoryService
from app.services.ai_service import AIService
from app.services.athlete_profile_service import AthleteProfileService
from app.services.injury_prevention_service import InjuryPreventionService, AlertLevel

logger = logging.getLogger("app.services.planner")


class TrainingPlannerService:
    """
    Intelligent training plan generation with progressive overload.

    Features:
    - Analyzes 8 weeks of workout history
    - Considers readiness forecasts
    - Applies Stoppani periodization methodology
    - McGill spine safety rules
    - Automatic progressive overload (+2.5kg or +1 rep every 2 weeks)
    - Deload every 8 weeks (50% volume, same intensity)
    - Supersets and drop sets for isolation work
    - Readiness-based session reordering
    """

    INTENSITY_PHASES = {
        1: 0.70,
        2: 0.70,
        3: 0.75,
        4: 0.75,
        5: 0.80,
        6: 0.80,
        7: 0.85,
        8: 0.50,
    }

    COMPOUND_KEYWORDS = {
        "squat", "deadlift", "bench_press", "overhead_press", "barbell_row",
        "pull_up", "dip", "lunge", "hip_thrust", "romanian_deadlift",
        "barbell_curl", "tricep_extension", "military_press", "incline_bench",
    }

    ISOLATION_KEYWORDS = {
        "bicep_curl", "tricep_pushdown", "leg_extension", "leg_curl",
        "calf_raise", "lateral_raise", "fly", "crunch", "back_extension",
        "cable_curl", "hammer_curl", "tricep_kickback", "face_pull",
        "rear_delt_fly", "shrug",
    }

    MCGILL_BIG_3 = [
        {"name": "Bird Dog", "sets": 3, "reps": "8-10", "side": "alternating"},
        {"name": "Dead Bug", "sets": 3, "reps": "8-10", "side": "alternating"},
        {"name": "Side Plank", "sets": 3, "duration": "30-45s", "side": "each"},
    ]

    def __init__(self):
        self.ai_service = AIService()

    async def generate_weekly_plan(self, db: Session, user_id: str) -> Dict[str, Any]:
        recovery_status = InjuryPreventionService.get_current_status(db, user_id)
        injury_alert_level = recovery_status.alert_level
        zones_to_avoid = recovery_status.zones_to_avoid
        readiness_penalty = recovery_status.readiness_penalty

        profile = await self._get_athlete_profile(db, user_id)
        readiness_history = await self._get_readiness_history(db, user_id, days=30)
        workout_history = await self._get_workout_history(db, user_id, weeks=8)
        prs = await self._get_personal_records(db, user_id)
        memory_context = await self._get_memory_context(db, user_id)
        upcoming_readiness = await self._get_readiness_forecast(db, user_id, days=7)

        avg_sessions = self._calculate_avg_sessions(workout_history)
        avg_volume = self._calculate_avg_volume(workout_history)
        recovery_rate = self._calculate_recovery_rate(readiness_history)
        training_age = self._calculate_training_age(workout_history)
        current_week_number = self._calculate_current_week_number(db, user_id)

        weekly_structure = self._determine_week_structure(
            available_days=profile.get("days_per_week", 4),
            forecasted_readiness=upcoming_readiness,
            current_fatigue=self._calculate_fatigue_index(workout_history[-14:] if workout_history else []),
            training_age=training_age,
            profile=profile,
        )

        if injury_alert_level in [AlertLevel.ORANGE, AlertLevel.RED]:
            weekly_structure = InjuryPreventionService.apply_recovery_mode(weekly_structure)
        else:
            weekly_structure = self._reorder_sessions_by_readiness(
                weekly_structure, upcoming_readiness
            )

        if zones_to_avoid:
            weekly_structure = self._mark_avoid_exercises(weekly_structure, zones_to_avoid)

        plan_prompt = self._build_plan_prompt(
            profile, prs, weekly_structure, memory_context,
            avg_sessions, avg_volume, recovery_rate, training_age,
            current_week_number,
        )

        plan_json = await self._generate_ai_plan(plan_prompt)

        plan_with_progression = self.apply_progressive_overload(
            plan_json, prs, workout_history, current_week_number
        )

        plan_with_progression = self._apply_mcgill_rules(
            plan_with_progression, profile
        )

        plan_with_progression = self._add_supersets_and_dropsets(
            plan_with_progression, current_week_number
        )

        weekly_plan = await self._save_weekly_plan(
            db, user_id, weekly_structure, plan_with_progression, profile
        )

        return self._format_plan_response(weekly_plan, weekly_structure)

    @staticmethod
    def _reorder_sessions_by_readiness(
        weekly_structure: Dict[str, Any],
        forecast: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if len(forecast) < 3:
            return weekly_structure

        score_map = {f["date"]: f.get("score", 50) for f in forecast}

        sessions = weekly_structure.get("sessions", [])
        day_score_map = {}
        for session in sessions:
            day_offset = session["day"]
            base_date = date.today() - timedelta(days=date.today().weekday())
            session_date = (base_date + timedelta(days=day_offset)).isoformat()
            session["_forecast_score"] = score_map.get(session_date, 50)
            day_score_map[session["day"]] = score_map.get(session_date, 50)

        low_readiness_days = [d for d, s in day_score_map.items() if s < 40]
        if not low_readiness_days:
            return weekly_structure

        high_readiness_days = sorted(
            [d for d, s in day_score_map.items() if s >= 60],
            key=lambda d: day_score_map[d],
            reverse=True,
        )

        reordered = []
        remaining_low = low_readiness_days[:]
        remaining_high = high_readiness_days[:]

        for session in sessions:
            day = session["day"]
            if day in remaining_low and remaining_low:
                reordered.append(session)
                remaining_low.remove(day)
            elif day in remaining_high and remaining_high:
                reordered.append(session)
                remaining_high.remove(day)
            else:
                reordered.append(session)

        weekly_structure["sessions"] = reordered
        weekly_structure["reordered_note"] = (
            "Sesiones reordenadas segun forecast de readiness bajo"
        )
        return weekly_structure

    def apply_progressive_overload(
        self,
        plan: Dict[str, Any],
        prs: Dict[str, Any],
        workout_history: List[Any],
        week_number: int = 1,
    ) -> Dict[str, Any]:
        if "sessions" not in plan:
            return plan

        phase_intensity = self._get_phase_intensity(week_number)
        is_deload = week_number % 8 == 0

        for session in plan["sessions"]:
            for exercise in session.get("exercises", []):
                ex_name = exercise["name"].lower().replace(" ", "_")
                last_session = self._find_last_session_for_exercise(
                    ex_name, workout_history
                )

                if last_session:
                    last_weight = last_session.get("weight")
                    last_reps = last_session.get("reps")
                    last_rpe = last_session.get("rpe", 8)
                    last_success = last_session.get("completed", False)

                    if is_deload:
                        exercise["target_weight"] = round(last_weight * 0.85, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "Deload: -15% peso"
                    elif last_success and last_rpe <= 6:
                        exercise["target_weight"] = round(last_weight + 5, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "+5kg (sesion anterior muy facil)"
                    elif last_success and last_rpe <= 8:
                        exercise["target_weight"] = round(last_weight + 2.5, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "+2.5kg (progressive overload)"
                    elif last_rpe >= 9:
                        exercise["target_weight"] = round(last_weight, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "Mantener (muy dificil)"
                    else:
                        exercise["target_weight"] = round(last_weight, 1)
                        exercise["target_reps"] = last_reps
                        exercise["progression_note"] = "Repetir sesion anterior"
                else:
                    pr = prs.get(ex_name)
                    if pr and pr.get("weight"):
                        base_weight = pr["weight"] * 0.70 * phase_intensity
                        exercise["target_weight"] = round(base_weight / 2.5) * 2.5
                    else:
                        if "squat" in ex_name or "deadlift" in ex_name:
                            exercise["target_weight"] = 20.0
                        elif "press" in ex_name:
                            exercise["target_weight"] = 10.0
                        else:
                            exercise["target_weight"] = 5.0

                    exercise["target_reps"] = 8
                    exercise["progression_note"] = f"Inicial: {phase_intensity * 100:.0f}% intensidad"

                exercise["sets"] = exercise.get("sets", 4)
                exercise["rpe_target"] = self._calculate_rpe_target(week_number)
                exercise["intensity_percentage"] = int(phase_intensity * 100)
                exercise["week_number"] = week_number

        return plan

    @staticmethod
    def _mark_avoid_exercises(plan: Dict[str, Any], zones_to_avoid: List[str]) -> Dict[str, Any]:
        """Mark exercises that target injured zones as 'avoid' in the plan."""
        ZONE_EXERCISE_MAP = {
            "shoulder_left": ["overhead_press", "lateral_raise", "face_pull", "shoulder_press", "bench_press", "push_press", "arnold_press", "y_raises", "external_rotation"],
            "shoulder_right": ["overhead_press", "lateral_raise", "face_pull", "shoulder_press", "bench_press", "push_press", "arnold_press", "y_raises", "external_rotation"],
            "knee_left": ["squat", "leg_extension", "lunge", "leg_press", "bulgarian_split_squat", "hack_squat", "terminal_knee_extension"],
            "knee_right": ["squat", "leg_extension", "lunge", "leg_press", "bulgarian_split_squat", "hack_squat", "terminal_knee_extension"],
            "lower_back": ["deadlift", "romanian_deadlift", "good_morning", "barbell_row", "back_extension", "back_squat"],
            "upper_back": ["barbell_row", "lat_pulldown", "pull_up", "cable_row", "t_bar_row"],
            "elbow_left": ["bicep_curl", "hammer_curl", "chin_up", "wrist_curl", "reverse_curl"],
            "elbow_right": ["bicep_curl", "hammer_curl", "chin_up", "wrist_curl", "reverse_curl"],
            "wrist_left": ["wrist_curl", "reverse_wrist_curl", "grip_squeeze", "farmer_walk"],
            "wrist_right": ["wrist_curl", "reverse_wrist_curl", "grip_squeeze", "farmer_walk"],
            "hip_left": ["hip_thrust", "squat", "lunge", "pigeon_stretch", "adductor", "glute_bridge"],
            "hip_right": ["hip_thrust", "squat", "lunge", "pigeon_stretch", "adductor", "glute_bridge"],
            "ankle_left": ["calf_raise", "jump_rope", "box_jump", "sprint"],
            "ankle_right": ["calf_raise", "jump_rope", "box_jump", "sprint"],
            "chest": ["bench_press", "incline_bench", "dumbbell_fly", "push_up", "cable_crossover", "pec_deck"],
            "core": ["crunch", "plank", "hanging_leg_raise", "ab_wheel", "russian_twist"],
            "neck": ["shrug", "neck_curl", "overhead_press"],
        }

        avoid_exercises = set()
        for zone in zones_to_avoid:
            zone_lower = zone.lower()
            for mapped_zone, exercises in ZONE_EXERCISE_MAP.items():
                if zone_lower == mapped_zone or zone_lower in mapped_zone:
                    avoid_exercises.update(exercises)

        if not avoid_exercises:
            return plan

        for session in plan.get("sessions", []):
            for exercise in session.get("exercises", []):
                ex_name = exercise.get("name", "").lower().replace(" ", "_")
                if any(avoid in ex_name or ex_name in avoid for avoid in avoid_exercises):
                    exercise["avoid"] = True
                    exercise["avoid_reason"] = f"Zona lesionada activa — {', '.join(z.replace('_', ' ') for z in zones_to_avoid)}"
                    exercise["alternative"] = "McGill Big 3 o movilidad"

        return plan

    @staticmethod
    def _add_supersets_and_dropsets(
        plan: Dict[str, Any], week_number: int
    ) -> Dict[str, Any]:
        is_intensity_phase = week_number % 4 >= 2

        for session in plan.get("sessions", []):
            exercises = session.get("exercises", [])
            if len(exercises) < 4:
                continue

            isolation_groups: List[List[Dict]] = []
            current_group: List[Dict] = []

            for ex in exercises:
                ex_name = ex["name"].lower().replace(" ", "_")
                is_isolation = any(kw in ex_name for kw in TrainingPlannerService.ISOLATION_KEYWORDS)

                if is_isolation:
                    current_group.append(ex)
                    if len(current_group) == 2:
                        isolation_groups.append(current_group)
                        current_group = []
                else:
                    if current_group:
                        isolation_groups.append(current_group[:1])
                        current_group = []

            if is_intensity_phase:
                for group in isolation_groups:
                    if len(group) == 2:
                        group[0]["superset_with"] = group[1]["name"]
                        group[1]["superset_with"] = group[0]["name"]
                        group[0]["rest"] = "60s between sets"
                        group[1]["rest"] = "90s after superset"

            if week_number % 8 in (3, 7):
                for group in isolation_groups:
                    if group and len(group[0].get("sets", [])) > 3:
                        group[0]["drop_set"] = True
                        group[0]["drop_set_note"] = "Drop set: -20% peso al llegar a fallo"

        return plan

    @staticmethod
    def _apply_mcgill_rules(plan: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        injuries = profile.get("injuries", [])
        has_back_pain = any(
            "back" in str(i).lower() or "spine" in str(i).lower() or "lumbar" in str(i).lower()
            for i in injuries
        )

        contraindicated = [
            "toe_touch", "situp", "crunch_torso_curl", "leg_raise_lying",
            "good_morning", "standing_calf_raise",
        ] if has_back_pain else []

        if has_back_pain:
            for session in plan.get("sessions", []):
                mcgill_warmup = {
                    "name": "McGill Big 3 Warmup",
                    "exercises": TrainingPlannerService.MCGILL_BIG_3,
                    "notes": "Spine stability warmup - McGill protocol (historial lumbar)",
                }
                session["mcgill_warmup"] = mcgill_warmup

                session["exercises"] = [
                    ex for ex in session.get("exercises", [])
                    if not any(avoid in ex["name"].lower().replace(" ", "_") for avoid in contraindicated)
                ]

        return plan

    @staticmethod
    def _determine_week_structure(
        available_days: int,
        forecasted_readiness: List[Dict[str, Any]],
        current_fatigue: float,
        training_age: float,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        splits = {
            3: {
                "name": "Full Body 3x",
                "sessions": [
                    {"day": 0, "name": "FULL BODY A", "focus": "compound"},
                    {"day": 2, "name": "FULL BODY B", "focus": "compound"},
                    {"day": 4, "name": "FULL BODY C", "focus": "compound"},
                ],
            },
            4: {
                "name": "Upper/Lower Split",
                "sessions": [
                    {"day": 0, "name": "UPPER (Push/Pull)", "focus": "upper"},
                    {"day": 1, "name": "LOWER", "focus": "lower"},
                    {"day": 3, "name": "UPPER (Volume)", "focus": "upper"},
                    {"day": 4, "name": "LOWER (Volume)", "focus": "lower"},
                ],
            },
            5: {
                "name": "Push/Pull/Legs Split",
                "sessions": [
                    {"day": 0, "name": "PUSH", "focus": "upper_push"},
                    {"day": 1, "name": "PULL", "focus": "upper_pull"},
                    {"day": 2, "name": "LEGS", "focus": "lower"},
                    {"day": 4, "name": "UPPER", "focus": "upper"},
                    {"day": 5, "name": "LOWER", "focus": "lower"},
                ],
            },
            6: {
                "name": "Push/Pull/Legs x2",
                "sessions": [
                    {"day": 0, "name": "PUSH", "focus": "upper_push"},
                    {"day": 1, "name": "PULL", "focus": "upper_pull"},
                    {"day": 2, "name": "LEGS", "focus": "lower"},
                    {"day": 3, "name": "PUSH (Hypertrophy)", "focus": "upper_push"},
                    {"day": 4, "name": "PULL (Hypertrophy)", "focus": "upper_pull"},
                    {"day": 5, "name": "LEGS (Hypertrophy)", "focus": "lower"},
                ],
            },
        }

        structure = splits.get(available_days, splits[4])

        low_readiness_days = sum(
            1 for r in forecasted_readiness if r.get("score", 50) < 40
        )
        if low_readiness_days >= 2:
            structure["note"] = "Volumen reducido recomendado (readiness bajo)"

        return structure

    async def _generate_ai_plan(self, prompt: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": prompt}]
        system_prompt = (
            "Eres un entrenador personal experto. Genera planes de entrenamiento "
            "siguiendo metodologia Stoppani. Responde SIEMPRE en JSON valido."
        )

        try:
            response = self.ai_service._generate_chat_response(messages, system_prompt)
            return json.loads(response["content"])
        except Exception as e:
            logger.error(f"AI plan generation failed: {e}")
            return self._generate_fallback_plan()

    @staticmethod
    def _generate_fallback_plan() -> Dict[str, Any]:
        return {
            "week_number": 1,
            "sessions": [
                {
                    "day": 0,
                    "name": "Upper Body",
                    "focus": "upper",
                    "exercises": [
                        {
                            "name": "Bench Press",
                            "sets": 4,
                            "reps": 8,
                            "target_weight": 60,
                            "target_reps": 8,
                            "rpe_target": 8,
                        },
                        {
                            "name": "Barbell Row",
                            "sets": 4,
                            "reps": 8,
                            "target_weight": 60,
                            "target_reps": 8,
                            "rpe_target": 8,
                        },
                    ],
                }
            ],
        }

    async def _save_weekly_plan(
        self,
        db: Session,
        user_id: str,
        weekly_structure: Dict[str, Any],
        plan_data: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> PlanWeeklyPlan:
        db.query(PlanWeeklyPlan).filter(
            PlanWeeklyPlan.user_id == user_id,
            PlanWeeklyPlan.status == "active",
        ).update({"status": "archived"})

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        weekly_plan = PlanWeeklyPlan(
            user_id=user_id,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            status="active",
            objective=profile.get("goal", "strength"),
            plan_data=plan_data,
            ai_version="2.0",
        )
        db.add(weekly_plan)
        db.commit()
        db.refresh(weekly_plan)

        for session_data in weekly_structure.get("sessions", []):
            scheduled_date = week_start + timedelta(days=session_data["day"])
            session_plan = self._match_session_to_plan(session_data, plan_data)

            training_session = PlanSessionModel(
                plan_id=weekly_plan.id,
                day_index=session_data["day"],
                day_name=session_data["name"],
                scheduled_date=scheduled_date.isoformat(),
                exercises_data=session_plan,
            )
            db.add(training_session)

        db.commit()
        db.refresh(weekly_plan)
        logger.info(f"Weekly plan created for user {user_id} (week {week_start})")
        return weekly_plan

    @staticmethod
    def _match_session_to_plan(
        session_data: Dict[str, Any], plan_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        focus = session_data.get("focus", "")
        ai_sessions = plan_data.get("sessions", [])

        if ai_sessions:
            idx = session_data["day"] % len(ai_sessions)
            return ai_sessions[idx].get("exercises", [])

        defaults = {
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
        return defaults.get(focus, defaults["upper"])

    @staticmethod
    def _get_phase_intensity(week_number: int) -> float:
        phase = ((week_number - 1) % 8) + 1
        return TrainingPlannerService.INTENSITY_PHASES.get(phase, 0.75)

    @staticmethod
    def _calculate_rpe_target(week_number: int) -> int:
        phase = ((week_number - 1) % 8) + 1
        if phase <= 2:
            return 7
        elif phase <= 4:
            return 8
        elif phase <= 6:
            return 8
        elif phase == 7:
            return 9
        else:
            return 6

    async def _get_athlete_profile(self, db: Session, user_id: str) -> Dict[str, Any]:
        profile_service = AthleteProfileService()
        profile = profile_service.get_profile_summary(user_id, db)
        if not profile:
            return {
                "days_per_week": 4,
                "goal": "strength",
                "experience_level": "intermediate",
                "injuries": [],
                "restrictions": [],
            }

        parsed = {
            "days_per_week": 4,
            "goal": "strength",
            "experience_level": "intermediate",
            "injuries": [],
            "restrictions": [],
        }

        if "dias" in profile.lower():
            for line in profile.split("\n"):
                if "objetivo" in line.lower():
                    goal = line.lower().split("objetivo")[-1].strip()
                    if "definicion" in goal:
                        parsed["goal"] = "definition"
                    elif "fuerza" in goal:
                        parsed["goal"] = "strength"
                if any(k in line.lower() for k in ["espalda", "lumbar", "rodilla", "hombro"]):
                    parsed["injuries"].append(line.strip())

        return parsed

    async def _get_readiness_history(
        self, db: Session, user_id: str, days: int
    ) -> List[Dict[str, Any]]:
        from app.models.daily_briefing import DailyBriefing
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        briefings = (
            db.query(DailyBriefing)
            .filter(
                DailyBriefing.user_id == user_id,
                DailyBriefing.date >= cutoff,
            )
            .order_by(DailyBriefing.date.asc())
            .all()
        )

        results = []
        for b in briefings:
            try:
                data = json.loads(b.content)
                results.append(data)
            except Exception:
                pass
        return results

    async def _get_workout_history(
        self, db: Session, user_id: str, weeks: int
    ) -> List[Workout]:
        cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
        return (
            db.query(Workout)
            .filter(Workout.user_id == user_id, Workout.date >= cutoff)
            .order_by(Workout.date.desc())
            .all()
        )

    async def _get_personal_records(self, db: Session, user_id: str) -> Dict[str, Any]:
        prs = db.query(PRModel).filter(
            PRModel.user_id == user_id
        ).all()

        result = {}
        for pr in prs:
            result[pr.exercise_name.lower()] = {
                "weight": pr.weight,
                "reps": pr.reps,
                "date": pr.date,
                "rpe": pr.rpe,
            }
        return result

    async def _get_memory_context(self, db: Session, user_id: str) -> str:
        return MemoryService.get_memory_context_string(db, user_id)

    async def _get_readiness_forecast(
        self, db: Session, user_id: str, days: int
    ) -> List[Dict[str, Any]]:
        return ReadinessService.get_forecast(db, user_id, days)

    @staticmethod
    def _calculate_current_week_number(db: Session, user_id: str) -> int:
        first_plan = (
            db.query(PlanWeeklyPlan)
            .filter(PlanWeeklyPlan.user_id == user_id)
            .order_by(PlanWeeklyPlan.generated_at.asc())
            .first()
        )

        if not first_plan:
            return 1

        days_since_start = (date.today() - first_plan.generated_at.date()).days
        return max(1, (days_since_start // 7) + 1)

    @staticmethod
    def _calculate_avg_sessions(workout_history: List[Any]) -> float:
        if not workout_history:
            return 3.0

        weeks: Dict[str, int] = {}
        for w in workout_history:
            if hasattr(w.date, "isocalendar"):
                year, week_num = w.date.isocalendar()[0], w.date.isocalendar()[1]
            else:
                year, week_num = 2024, 1
            key = f"{year}-{week_num}"
            weeks[key] = weeks.get(key, 0) + 1

        return statistics.mean(weeks.values()) if weeks else 3.0

    @staticmethod
    def _calculate_avg_volume(workout_history: List[Any]) -> float:
        if not workout_history:
            return 180.0

        weeks: Dict[str, float] = {}
        for w in workout_history:
            if hasattr(w.date, "isocalendar"):
                year, week_num = w.date.isocalendar()[0], w.date.isocalendar()[1]
            else:
                year, week_num = 2024, 1
            key = f"{year}-{week_num}"
            weeks[key] = weeks.get(key, 0) + (w.duration or 0)

        if not weeks:
            return 180.0
        return statistics.mean(weeks.values()) / 3600

    @staticmethod
    def _calculate_recovery_rate(readiness_history: List[Dict[str, Any]]) -> float:
        if len(readiness_history) < 2:
            return 1.0
        return 1.0

    @staticmethod
    def _calculate_fatigue_index(recent_workouts: List[Any]) -> float:
        if not recent_workouts:
            return 0.0

        total_load = sum((w.duration or 0) for w in recent_workouts)
        avg_daily = total_load / 14

        if avg_daily > 7200:
            return 0.8
        elif avg_daily > 5400:
            return 0.6
        elif avg_daily > 3600:
            return 0.4
        return 0.2

    @staticmethod
    def _calculate_training_age(workout_history: List[Any]) -> float:
        if not workout_history:
            return 1.0

        months: Dict[str, int] = {}
        for w in workout_history:
            if hasattr(w.date, "year") and hasattr(w.date, "month"):
                key = f"{w.date.year}-{w.date.month}"
            else:
                continue
            months[key] = months.get(key, 0) + 1

        return min(len(months) / 12.0, 20.0)

    def _build_plan_prompt(
        self,
        profile: Dict[str, Any],
        prs: Dict[str, Any],
        weekly_structure: Dict[str, Any],
        memory_context: str,
        avg_sessions: float,
        avg_volume: float,
        recovery_rate: float,
        training_age: float,
        current_week_number: int,
    ) -> str:
        phase = ((current_week_number - 1) % 8) + 1
        intensity_pct = int(self._get_phase_intensity(current_week_number) * 100)
        is_deload = phase == 8

        prompt = f"""
Genera un plan de entrenamiento semanal personalizado siguiendo estas reglas:

PERFIL DEL ATLETA:
- Dias disponibles: {profile.get('days_per_week', 4)} dias/semana
- Objetivo: {profile.get('goal', 'strength')}
- Nivel: {profile.get('experience_level', 'intermediate')}
- Historial: {training_age:.1f} anos entrenando
- Sesiones promedio: {avg_sessions:.1f}/semana
- Volumen promedio: {avg_volume:.1f}h/semana

SEMANA {current_week_number} - FASE {phase} ({intensity_pct}% 1RM):
- {'Deload: 50% volumen' if is_deload else 'Entrenamiento normal'}
- Intensidad: {intensity_pct}% 1RM

RECORDS PERSONALES:
{json.dumps(prs, indent=2, ensure_ascii=False) if prs else "No hay PRs registrados"}

MEMORIA/HISTORIAL:
{memory_context if memory_context else "No hay datos historicos"}

ESTRUCTURA SEMANAL: {weekly_structure.get('name', 'Custom')}

REGLAS DE PROGRAMACION (Metodologia Stoppani):
1. Compound primero, aislamiento despues
2. {'Supersets para ejercicios de aislamiento' if phase >= 3 else 'Drop sets en fase de hipertrofia'}
3. Deload automatico cada 8 semanas (semana 8: 50% volumen, misma intensidad)
4. Intensidad por fases: 70% (1-2), 75% (3-4), 80% (5-6), 85% (7), 50% (8 deload)

REGLAS DE SEGURIDAD (McGill):
1. Big 3 McGill en warmup si hay historial de dolor lumbar
2. Evitar flexon lumbar con carga alta
3. Never compromise technique for weight

FORMATO DE RESPUESTA (JSON estricto):
{{
  "week_number": {current_week_number},
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
  ]
}}
"""
        return prompt

    @staticmethod
    def _find_last_session_for_exercise(
        exercise_name: str, workout_history: List[Any]
    ) -> Optional[Dict[str, Any]]:
        normalized = exercise_name.lower().replace("_", " ")
        for w in workout_history:
            if hasattr(w, "description") and w.description:
                try:
                    desc = json.loads(w.description) if isinstance(w.description, str) else w.description
                    for ex in desc.get("exercises", []):
                        ex_name = str(ex.get("name", "")).lower()
                        if (normalized in ex_name or ex_name in normalized) and ex.get("weight"):
                            return {
                                "weight": ex.get("weight"),
                                "reps": ex.get("reps"),
                                "rpe": ex.get("rpe", 8),
                                "completed": True,
                            }
                except Exception:
                    pass
        return None

    @staticmethod
    def _format_plan_response(
        weekly_plan: PlanWeeklyPlan, weekly_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        sessions_data = []
        for session in weekly_plan.sessions:
            sessions_data.append({
                "id": session.id,
                "day": session.day_index,
                "day_name": session.day_name,
                "scheduled_date": session.scheduled_date,
                "exercises": session.exercises_data,
                "completed": session.completed,
                "actual_data": session.actual_data,
                "skipped": session.skipped,
                "notes": session.notes,
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
            "plan_data": weekly_plan.plan_data,
            "week_number": weekly_plan.plan_data.get("week_number", 1) if weekly_plan.plan_data else 1,
        }