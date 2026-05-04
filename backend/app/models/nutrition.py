"""
ATLAS Nutrition Models
=======================

Models for nutrition tracking and calculation:
- NutritionSettings: User nutrition preferences (goal, height, age, gender)
- MealLog: Individual logged meals
- DailyNutritionSummary: Aggregated daily nutrition data

Autor: ATLAS Team
Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.db.session import Base


class NutritionSettings(Base):
    __tablename__ = "nutrition_settings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, index=True)

    goal_type = Column(String, default="recomp")  # cut / bulk / recomp
    weight_kg = Column(Float, nullable=True)        # Override weight from biometrics
    height_cm = Column(Float, nullable=True)       # Height for BMR calculation
    age = Column(Integer, nullable=True)            # Age for BMR calculation
    gender = Column(String, default="male")        # male / female (for BMR formula)
    activity_multiplier = Column(Float, default=1.55)  # sedentary=1.2, light=1.375, moderate=1.55, active=1.725, athlete=1.9
    protein_per_kg = Column(Float, default=2.2)    # g protein per kg bodyweight (Stoppani)
    fat_per_kg = Column(Float, default=0.8)         # g fat per kg bodyweight
    calorie_adjustment = Column(Integer, default=0) # Manual calorie adjustment

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<NutritionSettings {self.user_id}: goal={self.goal_type}>"


class MealLog(Base):
    __tablename__ = "meal_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    date = Column(String)          # YYYY-MM-DD
    meal_type = Column(String)      # breakfast / lunch / dinner / snack / pre_workout / post_workout
    name = Column(String)
    description = Column(Text, nullable=True)
    calories = Column(Integer, default=0)
    protein_g = Column(Float, default=0)
    carbs_g = Column(Float, default=0)
    fat_g = Column(Float, default=0)
    fiber_g = Column(Float, default=0)
    sodium_mg = Column(Float, default=0)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<MealLog {self.user_id} {self.date} {self.meal_type}>"


class DailyNutritionSummary(Base):
    __tablename__ = "daily_nutrition_summaries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    date = Column(String)          # YYYY-MM-DD

    target_calories = Column(Integer)
    target_protein_g = Column(Float)
    target_carbs_g = Column(Float)
    target_fat_g = Column(Float)

    consumed_calories = Column(Integer, default=0)
    consumed_protein_g = Column(Float, default=0)
    consumed_carbs_g = Column(Float, default=0)
    consumed_fat_g = Column(Float, default=0)

    steps = Column(Integer, default=0)
    steps_source = Column(String, default="estimated")  # real / estimated
    workout_calories = Column(Integer, default=0)

    neat_calories = Column(Float, default=0)
    eat_calories = Column(Float, default=0)
    bmr = Column(Float, default=0)
    tdee = Column(Float, default=0)

    hydration_ml = Column(Integer, default=0)
    hydration_target_ml = Column(Integer, default=0)
    water_glasses = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DailyNutritionSummary {self.user_id} {self.date}>"