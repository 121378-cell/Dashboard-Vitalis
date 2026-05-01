"""
ATLAS Nutrition API Endpoints
==============================

Rutas:
- GET  /nutrition/daily         → Necesidades calóricas del día (TDEE + macros)
- GET  /nutrition/meal-plan     → Distribución de comidas con timing
- POST /nutrition/log            → Registrar comida consumida
- DELETE /nutrition/log/{id}     → Eliminar comida registrada
- GET  /nutrition/history       → Historial nutricional (últimos N días)
- GET  /nutrition/today          → Resumen completo del día (necesidades + consumido)
- PUT  /nutrition/settings       → Actualizar configuración nutricional
- POST /nutrition/water          → Registrar vaso de agua

Autor: ATLAS Team
Version: 1.0.0
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id
from app.services.nutrition_service import NutritionService

router = APIRouter()


class LogMealRequest(BaseModel):
    meal_type: str = Field(..., description="breakfast / lunch / dinner / snack / pre_workout / post_workout")
    name: str
    calories: int = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    description: Optional[str] = None


class UpdateSettingsRequest(BaseModel):
    goal_type: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_multiplier: Optional[float] = None
    protein_per_kg: Optional[float] = None
    fat_per_kg: Optional[float] = None
    calorie_adjustment: Optional[int] = None


class WaterGlassRequest(BaseModel):
    glasses: int = Field(default=1, ge=1, le=10)


@router.get("/daily", summary="Necesidades nutricionales del día")
async def get_daily_needs(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Calcula las necesidades calóricas y macros del día basándose en:
    - BMR (Mifflin-St Jeor): peso, altura, edad, género
    - NEAT: pasos Garmin (o estimado 8000 si no hay datos)
    - EAT: calorías de entrenamientos del día
    - Objetivo: cut (-400kcal), bulk (+300kcal), recomp (TDEE)
    """
    result = NutritionService.calculate_daily_needs(db, user_id, target_date)
    return {
        "status": "success",
        "data": asdict(result),
    }


@router.get("/today", summary="Resumen nutricional completo del día")
async def get_nutrition_today(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve el resumen completo del día:
    - Necesidades (target) + macros
    - Lo consumido hasta ahora + detalle por comida
    - Lo que falta (remaining)
    - Pasos, workout calories, NEAT, EAT
    - Plan de comidas del día
    """
    result = NutritionService.get_nutrition_today(db, user_id)
    return {
        "status": "success",
        "data": result,
    }


@router.get("/meal-plan", summary="Plan de comidas del día")
async def get_meal_plan(
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Genera un plan de comidas inteligente basado en:
    - Hora del entrenamiento principal (si hay)
    - Pre-workout: 2h antes (carbohidratos complejos + proteína)
    - Post-workout: 30min después (carbohidratos simples + proteína rápida)
    - Distribución: desayuno, almuerzo, merienda, cena
    """
    if target_date is None:
        target_date = date.today().isoformat()

    needs = NutritionService.calculate_daily_needs(db, user_id, target_date)
    return {
        "status": "success",
        "data": {
            "date": target_date,
            "goal_type": needs.goal_type,
            "target_calories": needs.target_calories,
            "meals": needs.meals,
        },
    }


@router.post("/log", summary="Registrar comida consumida")
async def log_meal(
    request: LogMealRequest,
    target_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Registra una comida consumida.
   积分可以累积，后续用于 análisis de adherencia.
    """
    meal = NutritionService.log_meal(
        db=db,
        user_id=user_id,
        meal_type=request.meal_type,
        name=request.name,
        calories=request.calories,
        protein_g=request.protein_g,
        carbs_g=request.carbs_g,
        fat_g=request.fat_g,
        description=request.description,
        target_date=target_date,
    )
    return {
        "status": "success",
        "data": {
            "id": meal.id,
            "date": meal.date,
            "meal_type": meal.meal_type,
            "name": meal.name,
            "calories": meal.calories,
            "protein_g": meal.protein_g,
            "carbs_g": meal.carbs_g,
            "fat_g": meal.fat_g,
        },
        "message": "Comida registrada correctamente",
    }


@router.delete("/log/{meal_id}", summary="Eliminar comida registrada")
async def delete_meal(
    meal_id: int,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    deleted = NutritionService.delete_meal(db, meal_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comida no encontrada",
        )
    return {
        "status": "success",
        "message": "Comida eliminada",
    }


@router.get("/history", summary="Historial nutricional")
async def get_nutrition_history(
    days: int = Query(default=7, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve el historial nutricional de los últimos N días.
    Incluye objetivos vs consumido para cada día.
    """
    history = NutritionService.get_nutrition_history(db, user_id, days)
    return {
        "status": "success",
        "data": {
            "history": history,
            "days_requested": days,
            "days_returned": len(history),
        },
    }


@router.get("/settings", summary="Obtener configuración nutricional")
async def get_settings(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    settings = NutritionService.get_nutrition_settings(db, user_id)
    return {
        "status": "success",
        "data": {
            "goal_type": settings.goal_type,
            "weight_kg": settings.weight_kg,
            "height_cm": settings.height_cm,
            "age": settings.age,
            "gender": settings.gender,
            "activity_multiplier": settings.activity_multiplier,
            "protein_per_kg": settings.protein_per_kg,
            "fat_per_kg": settings.fat_per_kg,
            "calorie_adjustment": settings.calorie_adjustment,
        },
    }


@router.put("/settings", summary="Actualizar configuración nutricional")
async def update_settings(
    request: UpdateSettingsRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    settings = NutritionService.update_nutrition_settings(
        db=db,
        user_id=user_id,
        goal_type=request.goal_type,
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        age=request.age,
        gender=request.gender,
        activity_multiplier=request.activity_multiplier,
        protein_per_kg=request.protein_per_kg,
        fat_per_kg=request.fat_per_kg,
        calorie_adjustment=request.calorie_adjustment,
    )
    return {
        "status": "success",
        "data": {
            "goal_type": settings.goal_type,
            "weight_kg": settings.weight_kg,
            "height_cm": settings.height_cm,
            "age": settings.age,
            "gender": settings.gender,
            "activity_multiplier": settings.activity_multiplier,
            "protein_per_kg": settings.protein_per_kg,
            "fat_per_kg": settings.fat_per_kg,
            "calorie_adjustment": settings.calorie_adjustment,
        },
        "message": "Configuración actualizada",
    }


@router.post("/water", summary="Registrar vaso de agua")
async def log_water(
    request: WaterGlassRequest = WaterGlassRequest(),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    glasses = NutritionService.log_water_glass(db, user_id, request.glasses)
    settings = NutritionService.get_nutrition_settings(db, user_id)
    summary = NutritionService.save_daily_summary(db, user_id)
    return {
        "status": "success",
        "data": {
            "glasses_logged": glasses,
            "hydration_ml": glasses * 250,
            "hydration_target_ml": summary.hydration_target_ml,
            "progress_pct": min(100, round(glasses * 250 / summary.hydration_target_ml * 100, 1)),
        },
        "message": f"{glasses} vaso(s) de agua registrado(s)",
    }


@router.get("/hydration-status", summary="Estado de hidratación del día")
async def get_hydration_status(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    target_date = date.today().isoformat()
    summary = NutritionService.save_daily_summary(db, user_id, target_date)
    return {
        "status": "success",
        "data": {
            "water_glasses": summary.water_glasses or 0,
            "hydration_ml": summary.hydration_ml or 0,
            "target_ml": summary.hydration_target_ml or 0,
            "progress_pct": min(100, round((summary.hydration_ml or 0) / max(1, summary.hydration_target_ml or 1) * 100, 1)),
            "glasses_remaining": max(0, round((summary.hydration_target_ml or 0) / 250) - (summary.water_glasses or 0)),
        },
    }


from dataclasses import asdict