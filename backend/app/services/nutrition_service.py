"""
ATLAS Nutrition Service v1
============================

Calculates daily calorie and macro needs based on:
- BMR: Mifflin-St Jeor equation
- NEAT: Non-Exercise Activity Thermogenesis (Garmin steps)
- EAT: Exercise Activity Thermogenesis (workout calories)
- TDEE: Total Daily Energy Expenditure
- Goal-based adjustments (cut/bulk/recomp)

Macro distribution following Stoppani methodology:
- Protein: 2.2g per kg bodyweight (high protein for muscle preservation)
- Fat: 0.8g per kg bodyweight
- Carbs: remaining calories

Autor: ATLAS Team
Version: 1.0.0
"""

import json
import logging
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.models.nutrition import NutritionSettings, MealLog, DailyNutritionSummary
from app.models.biometrics import Biometrics
from app.models.workout import Workout

logger = logging.getLogger("app.services.nutrition")


@dataclass
class NutritionPlan:
    target_calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    hydration_ml: int
    bmr: float
    neat_calories: float
    eat_calories: float
    tdee: float
    steps_source: str
    steps: int
    workout_calories: int
    goal_type: str
    meals: List[Dict[str, Any]]


@dataclass
class MealTiming:
    name: str
    time: str
    description: str
    carbs_pct: int
    protein_pct: int
    fat_pct: int


class NutritionService:
    DEFAULT_WEIGHT_KG = 80.0
    DEFAULT_HEIGHT_CM = 175.0
    DEFAULT_AGE = 30
    DEFAULT_GENDER = "male"
    ESTIMATED_STEPS = 8000
    KCAL_PER_STEP = 0.04
    ML_WATER_PER_KG = 35
    ML_WATER_PER_STEP = 0.5

    @classmethod
    def get_nutrition_settings(cls, db: Session, user_id: str) -> NutritionSettings:
        settings = db.query(NutritionSettings).filter(
            NutritionSettings.user_id == user_id
        ).first()

        if not settings:
            settings = NutritionSettings(user_id=user_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings

    @classmethod
    def update_nutrition_settings(
        cls, db: Session, user_id: str,
        goal_type: Optional[str] = None,
        weight_kg: Optional[float] = None,
        height_cm: Optional[float] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        activity_multiplier: Optional[float] = None,
        protein_per_kg: Optional[float] = None,
        fat_per_kg: Optional[float] = None,
        calorie_adjustment: Optional[int] = None,
    ) -> NutritionSettings:
        settings = cls.get_nutrition_settings(db, user_id)

        if goal_type is not None:
            settings.goal_type = goal_type
        if weight_kg is not None:
            settings.weight_kg = weight_kg
        if height_cm is not None:
            settings.height_cm = height_cm
        if age is not None:
            settings.age = age
        if gender is not None:
            settings.gender = gender
        if activity_multiplier is not None:
            settings.activity_multiplier = activity_multiplier
        if protein_per_kg is not None:
            settings.protein_per_kg = protein_per_kg
        if fat_per_kg is not None:
            settings.fat_per_kg = fat_per_kg
        if calorie_adjustment is not None:
            settings.calorie_adjustment = calorie_adjustment

        db.commit()
        db.refresh(settings)
        return settings

    @classmethod
    def calculate_bmr(cls, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        if gender == "female":
            return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5

    @classmethod
    def calculate_tdee(
        cls, bmr: float, steps: int, workout_calories: int,
        activity_multiplier: float = 1.55
    ) -> tuple[float, float, float]:
        neat = steps * cls.KCAL_PER_STEP
        eat = float(workout_calories)
        tdee = (bmr * activity_multiplier) + neat + eat
        return round(tdee, 1), round(neat, 1), round(eat, 1)

    @classmethod
    def calculate_daily_needs(
        cls, db: Session, user_id: str,
        target_date: Optional[str] = None
    ) -> NutritionPlan:
        if target_date is None:
            target_date = date.today().isoformat()

        settings = cls.get_nutrition_settings(db, user_id)

        weight_kg = cls._get_weight(db, user_id, settings.weight_kg)
        height_cm = settings.height_cm or cls.DEFAULT_HEIGHT_CM
        age = settings.age or cls.DEFAULT_AGE
        gender = settings.gender or cls.DEFAULT_GENDER

        steps, steps_source = cls._get_steps(db, user_id, target_date)
        workout_calories = cls._get_workout_calories(db, user_id, target_date)

        bmr = cls.calculate_bmr(weight_kg, height_cm, age, gender)
        tdee, neat, eat = cls.calculate_tdee(
            bmr, steps, workout_calories, settings.activity_multiplier
        )

        target_calories = cls._apply_goal_adjustment(tdee, settings.goal_type)
        target_calories += settings.calorie_adjustment

        protein_per_kg = settings.protein_per_kg or 2.2
        fat_per_kg = settings.fat_per_kg or 0.8

        protein_g = round(weight_kg * protein_per_kg)
        fat_g = round(weight_kg * fat_per_kg)

        protein_cal = protein_g * 4
        fat_cal = fat_g * 9
        remaining_cal = target_calories - protein_cal - fat_cal
        carbs_g = max(0, round(remaining_cal / 4))

        hydration_ml = round(weight_kg * cls.ML_WATER_PER_KG + steps * cls.ML_WATER_PER_STEP)

        meals = cls.generate_meal_timing(db, user_id, target_date, target_calories)

        return NutritionPlan(
            target_calories=round(target_calories),
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            hydration_ml=hydration_ml,
            bmr=round(bmr, 1),
            neat_calories=neat,
            eat_calories=eat,
            tdee=round(tdee, 1),
            steps_source=steps_source,
            steps=steps,
            workout_calories=workout_calories,
            goal_type=settings.goal_type,
            meals=meals,
        )

    @staticmethod
    def _get_weight(db: Session, user_id: str, settings_weight: Optional[float]) -> float:
        if settings_weight:
            return settings_weight

        today = date.today()
        cutoff = (date.today() - timedelta(days=7)).isoformat()

        rows = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date >= cutoff
        ).order_by(Biometrics.date.desc()).limit(7).all()

        weights = []
        for row in rows:
            if row.data:
                try:
                    d = json.loads(row.data)
                    w = d.get("weight") or d.get("bodyWeight") or d.get("body_weight")
                    if w and w > 0:
                        weights.append(float(w))
                except Exception:
                    pass

        return weights[0] if weights else NutritionService.DEFAULT_WEIGHT_KG

    @classmethod
    def _get_steps(cls, db: Session, user_id: str, target_date: str) -> tuple[int, str]:
        row = db.query(Biometrics).filter(
            Biometrics.user_id == user_id,
            Biometrics.date == target_date,
            Biometrics.source == "garmin"
        ).first()

        if row and row.data:
            try:
                d = json.loads(row.data)
                steps = d.get("steps", 0)
                if steps and steps > 0:
                    return steps, "real"
            except Exception:
                pass

        return cls.ESTIMATED_STEPS, "estimated"

    @classmethod
    def _get_workout_calories(cls, db: Session, user_id: str, target_date: str) -> int:
        workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date == target_date
        ).all()

        return sum(w.calories or 0 for w in workouts)

    @classmethod
    def _apply_goal_adjustment(cls, tdee: float, goal_type: str) -> int:
        if goal_type == "cut":
            return round(tdee - 400)
        elif goal_type == "bulk":
            return round(tdee + 300)
        return round(tdee)

    @classmethod
    def generate_meal_timing(
        cls, db: Session, user_id: str, target_date: str, target_calories: int
    ) -> List[Dict[str, Any]]:
        workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.date == target_date
        ).order_by(Workout.date.asc()).all()

        workout_time: Optional[datetime] = None
        if workouts and workouts[0].date:
            workout_time = workouts[0].date
            if hasattr(workout_time, 'time'):
                workout_time = datetime.combine(date.today(), workout_time.time())

        meals: List[Dict[str, Any]] = []
        total_cal = target_calories

        if workout_time:
            pre_time = workout_time - timedelta(hours=2)
            meals.append({
                "name": "Pre-Workout",
                "time": pre_time.strftime("%H:%M"),
                "type": "pre_workout",
                "calories": round(total_cal * 0.10),
                "macros": {"carbs_pct": 40, "protein_pct": 30, "fat_pct": 10},
                "description": "2h antes: carbohidratos complejos + proteína moderada. Evita grasas.",
                "examples": "Avena + huevos + plátano / Arroz + pollo + verduras",
            })

            post_time = workout_time + timedelta(minutes=30)
            meals.append({
                "name": "Post-Workout",
                "time": post_time.strftime("%H:%M"),
                "type": "post_workout",
                "calories": round(total_cal * 0.15),
                "macros": {"carbs_pct": 50, "protein_pct": 40, "fat_pct": 5},
                "description": "Ventana anabólica: carbohidratos simples + proteína rápida (whey).",
                "examples": "Whey + arroz + fruta / Batido protéico + pasta",
            })

        breakfast_cal = round(total_cal * 0.25)
        meals.append({
            "name": "Desayuno",
            "time": "08:00",
            "type": "breakfast",
            "calories": breakfast_cal,
            "macros": {"carbs_pct": 35, "protein_pct": 30, "fat_pct": 25},
            "description": "Primera comida del día. Proteína + carbs complejos + grasas saludables.",
            "examples": "Huevos revueltos + avena + aguacate / Greek yogurt + granola + frutos rojos",
        })

        lunch_cal = round(total_cal * 0.30)
        meals.append({
            "name": "Almuerzo",
            "time": "13:00",
            "type": "lunch",
            "calories": lunch_cal,
            "macros": {"carbs_pct": 40, "protein_pct": 35, "fat_pct": 20},
            "description": "Comida principal. Proteína abundante + verduras + carbs.",
            "examples": "Pollo/asado + arroz + ensalada / Salmón + boniato + verduras",
        })

        snack_cal = round(total_cal * 0.10)
        meals.append({
            "name": "Merienda",
            "time": "17:00",
            "type": "snack",
            "calories": snack_cal,
            "macros": {"carbs_pct": 30, "protein_pct": 40, "fat_pct": 20},
            "description": "Snack ligero. Proteína + algo de carbs.",
            "examples": "Yogur griego + frutos secos / Whey + fruta",
        })

        dinner_cal = round(total_cal * 0.10)
        meals.append({
            "name": "Cena",
            "time": "20:00",
            "type": "dinner",
            "calories": dinner_cal,
            "macros": {"carbs_pct": 25, "protein_pct": 40, "fat_pct": 25},
            "description": "Cena ligera. Proteína + verduras. Mínimo carbs.",
            "examples": "Pechuga + ensalada + aguacate / Pescado + verduras",
        })

        return meals

    @classmethod
    def get_daily_consumed(
        cls, db: Session, user_id: str, target_date: str
    ) -> Dict[str, Any]:
        meals = db.query(MealLog).filter(
            MealLog.user_id == user_id,
            MealLog.date == target_date
        ).all()

        consumed_cal = sum(m.calories or 0 for m in meals)
        consumed_protein = sum(m.protein_g or 0 for m in meals)
        consumed_carbs = sum(m.carbs_g or 0 for m in meals)
        consumed_fat = sum(m.fat_g or 0 for m in meals)

        return {
            "calories": consumed_cal,
            "protein_g": round(consumed_protein, 1),
            "carbs_g": round(consumed_carbs, 1),
            "fat_g": round(consumed_fat, 1),
            "meals_logged": len(meals),
            "meal_details": [
                {
                    "id": m.id,
                    "name": m.name,
                    "type": m.meal_type,
                    "calories": m.calories,
                    "protein_g": m.protein_g,
                    "carbs_g": m.carbs_g,
                    "fat_g": m.fat_g,
                }
                for m in meals
            ],
        }

    @classmethod
    def log_meal(
        cls, db: Session, user_id: str,
        meal_type: str, name: str,
        calories: int = 0,
        protein_g: float = 0,
        carbs_g: float = 0,
        fat_g: float = 0,
        description: Optional[str] = None,
        target_date: Optional[str] = None,
    ) -> MealLog:
        if target_date is None:
            target_date = date.today().isoformat()

        meal = MealLog(
            user_id=user_id,
            date=target_date,
            meal_type=meal_type,
            name=name,
            description=description,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
        )
        db.add(meal)
        db.commit()
        db.refresh(meal)
        return meal

    @classmethod
    def delete_meal(cls, db: Session, meal_id: int, user_id: str) -> bool:
        meal = db.query(MealLog).filter(
            MealLog.id == meal_id,
            MealLog.user_id == user_id
        ).first()
        if not meal:
            return False
        db.delete(meal)
        db.commit()
        return True

    @classmethod
    def get_nutrition_history(
        cls, db: Session, user_id: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        summaries = db.query(DailyNutritionSummary).filter(
            DailyNutritionSummary.user_id == user_id,
            DailyNutritionSummary.date >= cutoff
        ).order_by(DailyNutritionSummary.date.desc()).all()

        return [
            {
                "date": s.date,
                "target_calories": s.target_calories,
                "consumed_calories": s.consumed_calories,
                "target_protein_g": s.target_protein_g,
                "consumed_protein_g": s.consumed_protein_g,
                "target_carbs_g": s.target_carbs_g,
                "consumed_carbs_g": s.consumed_carbs_g,
                "target_fat_g": s.target_fat_g,
                "consumed_fat_g": s.consumed_fat_g,
                "steps": s.steps,
                "steps_source": s.steps_source,
                "workout_calories": s.workout_calories,
                "hydration_ml": s.hydration_ml,
                "water_glasses": s.water_glasses,
            }
            for s in summaries
        ]

    @classmethod
    def save_daily_summary(
        cls, db: Session, user_id: str, target_date: Optional[str] = None
    ) -> DailyNutritionSummary:
        if target_date is None:
            target_date = date.today().isoformat()

        existing = db.query(DailyNutritionSummary).filter(
            DailyNutritionSummary.user_id == user_id,
            DailyNutritionSummary.date == target_date
        ).first()

        needs = cls.calculate_daily_needs(db, user_id, target_date)
        consumed = cls.get_daily_consumed(db, user_id, target_date)

        steps, steps_source = cls._get_steps(db, user_id, target_date)
        workout_calories = cls._get_workout_calories(db, user_id, target_date)

        data = {
            "user_id": user_id,
            "date": target_date,
            "target_calories": needs.target_calories,
            "target_protein_g": needs.protein_g,
            "target_carbs_g": needs.carbs_g,
            "target_fat_g": needs.fat_g,
            "consumed_calories": consumed["calories"],
            "consumed_protein_g": consumed["protein_g"],
            "consumed_carbs_g": consumed["carbs_g"],
            "consumed_fat_g": consumed["fat_g"],
            "steps": steps,
            "steps_source": steps_source,
            "workout_calories": workout_calories,
            "neat_calories": needs.neat_calories,
            "eat_calories": needs.eat_calories,
            "bmr": needs.bmr,
            "tdee": needs.tdee,
            "hydration_ml": 0,
            "hydration_target_ml": needs.hydration_ml,
            "water_glasses": 0,
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            summary = existing
        else:
            summary = DailyNutritionSummary(**data)
            db.add(summary)

        db.commit()
        db.refresh(summary)
        return summary

    @classmethod
    def log_water_glass(cls, db: Session, user_id: str, glasses: int = 1) -> int:
        target_date = date.today().isoformat()
        summary = db.query(DailyNutritionSummary).filter(
            DailyNutritionSummary.user_id == user_id,
            DailyNutritionSummary.date == target_date
        ).first()

        if not summary:
            cls.save_daily_summary(db, user_id, target_date)
            summary = db.query(DailyNutritionSummary).filter(
                DailyNutritionSummary.user_id == user_id,
                DailyNutritionSummary.date == target_date
            ).first()

        summary.water_glasses = (summary.water_glasses or 0) + glasses
        summary.hydration_ml = summary.water_glasses * 250
        db.commit()
        db.refresh(summary)
        return summary.water_glasses

    @classmethod
    def get_nutrition_today(cls, db: Session, user_id: str) -> Dict[str, Any]:
        target_date = date.today().isoformat()
        needs = cls.calculate_daily_needs(db, user_id, target_date)
        consumed = cls.get_daily_consumed(db, user_id, target_date)
        steps, steps_source = cls._get_steps(db, user_id, target_date)
        workout_calories = cls._get_workout_calories(db, user_id, target_date)

        return {
            "date": target_date,
            "goal_type": needs.goal_type,
            "target": {
                "calories": needs.target_calories,
                "protein_g": needs.protein_g,
                "carbs_g": needs.carbs_g,
                "fat_g": needs.fat_g,
            },
            "consumed": consumed,
            "remaining": {
                "calories": max(0, needs.target_calories - consumed["calories"]),
                "protein_g": max(0, round(needs.protein_g - consumed["protein_g"], 1)),
                "carbs_g": max(0, round(needs.carbs_g - consumed["carbs_g"], 1)),
                "fat_g": max(0, round(needs.fat_g - consumed["fat_g"], 1)),
            },
            "bmr": needs.bmr,
            "tdee": needs.tdee,
            "neat_calories": needs.neat_calories,
            "eat_calories": needs.eat_calories,
            "steps": steps,
            "steps_source": steps_source,
            "workout_calories": workout_calories,
            "hydration_target_ml": needs.hydration_ml,
            "meals": needs.meals,
        }