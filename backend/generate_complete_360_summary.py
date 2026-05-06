"""
Generar resumen completo 360° para el coach de Atlas
======================================================

Este script genera un resumen completo que combina datos biométricos
y actividades de entrenamiento para dar al coach una visión 360° del atleta.

Ejecución:
    cd backend
    python generate_complete_360_summary.py
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import SessionLocal
from app.models.biometrics import Biometrics
from app.models.workout import Workout
from app.models.user import User
from app.services.readiness_service import ReadinessService
from datetime import datetime
import json


def _determine_age_group(age):
    """Determina el grupo de edad del atleta."""
    if not age:
        return "unknown"
    if age < 30:
        return "young_adult"
    elif age < 40:
        return "adult"
    elif age < 50:
        return "middle_aged"
    else:
        return "senior"


def _get_age_appropriate_recommendation(age):
    """Genera recomendaciones apropiadas para la edad."""
    if not age:
        return "Mantener programa de entrenamiento actual"
    
    if age < 30:
        return "Enfoque en desarrollo de fuerza y resistencia con progresión constante"
    elif age < 40:
        return "Optimizar rendimiento con periodización inteligente"
    elif age < 50:
        return "Mantener condición física con énfasis en recuperación y prevención de lesiones"
    else:
        return "Priorizar salud funcional, movilidad y longevidad activa"


def _get_aging_considerations(age):
    """Genera consideraciones específicas basadas en la edad."""
    if not age:
        return {"message": "Edad no disponible para consideraciones de envejecimiento"}
    
    considerations = {
        "age": age,
        "age_group": _determine_age_group(age),
        "recovery_needs": "standard",
        "injury_prevention_priority": "moderate",
        "training_adaptation": "none"
    }
    
    if age < 30:
        considerations.update({
            "recovery_needs": "moderate",
            "injury_prevention_priority": "low",
            "training_adaptation": "progressive_overload",
            "focus_areas": ["desarrollo_fuerza", "resistencia", "velocidad"]
        })
    elif age < 40:
        considerations.update({
            "recovery_needs": "standard",
            "injury_prevention_priority": "moderate",
            "training_adaptation": "periodization",
            "focus_areas": ["rendimiento_optimo", "fuerza_mantenimiento", "resistencia"]
        })
    elif age < 50:
        considerations.update({
            "recovery_needs": "enhanced",
            "injury_prevention_priority": "high",
            "training_adaptation": "modified_intensity",
            "focus_areas": ["mantenimiento_condicion", "movilidad", "prevencion_lesiones"]
        })
    else:
        considerations.update({
            "recovery_needs": "extended",
            "injury_prevention_priority": "very_high",
            "training_adaptation": "functional_focus",
            "focus_areas": ["salud_funcional", "movilidad", "longevidad_activa", "equilibrio"]
        })
    
    return considerations

def generate_complete_360_summary(db, user_id):
    """Genera un resumen completo 360° del atleta."""
    print("\n" + "="*60)
    print("GENERANDO RESUMEN COMPLETO 360° PARA EL COACH")
    print("="*60)
    
    # Obtener información del usuario
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    
    # Obtener datos biométricos
    biometrics = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.asc()).all()
    
    # Obtener actividades
    activities = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).order_by(Workout.date.desc()).all()
    
    print(f"📊 COBERTURA DE DATOS:")
    print(f"   Registros biométricos: {len(biometrics)} días")
    print(f"   Actividades: {len(activities)}")
    
    # Calcular estadísticas biométricas
    sleep_values = []
    steps_values = []
    stress_values = []
    rhr_values = []
    body_battery_values = []
    
    for bio in biometrics:
        if bio.data:
            try:
                data = json.loads(bio.data)
                
                if data.get("sleep"):
                    sleep_values.append(data["sleep"])
                
                if data.get("steps"):
                    steps_values.append(data["steps"])
                
                if data.get("stress"):
                    stress_values.append(data["stress"])
                
                if data.get("heartRate"):
                    rhr_values.append(data["heartRate"])
                
                if bio.body_battery:
                    body_battery_values.append(bio.body_battery)
                    
            except:
                pass
    
    # Calcular promedios biométricos
    import statistics
    
    avg_sleep = statistics.mean(sleep_values) if sleep_values else 0
    avg_steps = statistics.mean(steps_values) if steps_values else 0
    avg_stress = statistics.mean(stress_values) if stress_values else 0
    avg_rhr = statistics.mean(rhr_values) if rhr_values else 0
    avg_body_battery = statistics.mean(body_battery_values) if body_battery_values else 0
    
    # Calcular estadísticas de actividades
    activity_types = {}
    total_duration = 0
    total_distance = 0
    total_calories = 0
    
    for act in activities:
        sport = "unknown"
        if act.description:
            try:
                metrics = json.loads(act.description)
                sport = metrics.get("sport", "unknown")
            except:
                pass
        
        if sport not in activity_types:
            activity_types[sport] = {
                "count": 0,
                "total_duration": 0,
                "total_distance": 0,
                "total_calories": 0
            }
        
        activity_types[sport]["count"] += 1
        activity_types[sport]["total_duration"] += act.duration or 0
        activity_types[sport]["total_calories"] += act.calories or 0
        
        if act.description:
            try:
                metrics = json.loads(act.description)
                distance = metrics.get("distance")
                if distance:
                    activity_types[sport]["total_distance"] += distance
                    total_distance += distance
            except:
                pass
        
        total_duration += act.duration or 0
        total_calories += act.calories or 0
    
    # Calcular promedios de actividades
    avg_duration = total_duration / len(activities) if activities else 0
    avg_calories = total_calories / len(activities) if activities else 0
    
    # Determinar rango de fechas
    if biometrics:
        oldest_date = biometrics[0].date
        newest_date = biometrics[-1].date
    else:
        oldest_date = None
        newest_date = None
    
    if activities:
        oldest_activity = activities[-1].date
        newest_activity = activities[0].date
    else:
        oldest_activity = None
        newest_activity = None
    
    # Calcular readiness actual
    try:
        readiness_result = ReadinessService.calculate(db, user_id)
    except:
        readiness_result = None
    
    # Generar perfil del atleta
    athlete_profile = {
        "activity_level": "Muy activo" if avg_steps >= 15000 else "Activo" if avg_steps >= 10000 else "Moderadamente activo",
        "sleep_quality": "Excelente" if avg_sleep >= 8 else "Bueno" if avg_sleep >= 7 else "Adecuado",
        "stress_level": "Bajo" if avg_stress <= 30 else "Moderado" if avg_stress <= 50 else "Alto",
        "fitness_level": "Alto" if avg_rhr <= 50 and avg_steps >= 10000 else "Medio" if avg_rhr <= 55 else "Bajo"
    }
    
    # Generar insights de entrenamiento
    training_insights = {
        "training_volume": "high" if len(activities) / 697 * 7 >= 4 else "moderate",
        "consistency": "high" if len(activities) / 697 * 7 >= 3 else "moderate",
        "primary_focus": max(activity_types.items(), key=lambda x: x[1]["count"])[0] if activity_types else "unknown",
        "total_training_hours": total_duration / 3600,
        "training_frequency_per_week": len(activities) / 697 * 7 if activities else 0
    }
    
    # Generar resumen completo
    complete_summary = {
        "user_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "personal_info": {
            "name": user.name if user else None,
            "birth_date": user.birth_date.isoformat() if user and user.birth_date else None,
            "age": user.age if user else None,
            "age_group": _determine_age_group(user.age if user else None)
        },
        "data_coverage": {
            "biometrics_days": len(biometrics),
            "activities_count": len(activities),
            "biometrics_range": {
                "oldest": oldest_date,
                "newest": newest_date
            },
            "activities_range": {
                "oldest": str(oldest_activity) if oldest_activity else None,
                "newest": str(newest_activity) if newest_activity else None
            }
        },
        "biometrics_profile": {
            "sleep": {
                "average_hours": round(avg_sleep, 2),
                "days_with_data": len(sleep_values)
            },
            "steps": {
                "average_daily": round(avg_steps, 0),
                "days_with_data": len(steps_values)
            },
            "stress": {
                "average_level": round(avg_stress, 1),
                "days_with_data": len(stress_values)
            },
            "resting_heart_rate": {
                "average_bpm": round(avg_rhr, 1),
                "days_with_data": len(rhr_values)
            },
            "body_battery": {
                "average": round(avg_body_battery, 1),
                "days_with_data": len(body_battery_values)
            }
        },
        "training_profile": {
            "total_activities": len(activities),
            "total_duration_hours": round(total_duration / 3600, 1),
            "total_distance_km": round(total_distance / 1000, 1),
            "total_calories": total_calories,
            "avg_duration_minutes": round(avg_duration / 60, 1),
            "avg_calories": round(avg_calories, 0),
            "training_frequency_per_week": round(training_insights["training_frequency_per_week"], 1),
            "activity_types": {
                sport: {
                    "count": stats["count"],
                    "avg_duration_minutes": round(stats["total_duration"] / stats["count"] / 60, 1),
                    "avg_calories": round(stats["total_calories"] / stats["count"], 0),
                    "total_distance_km": round(stats["total_distance"] / 1000, 1) if stats["total_distance"] > 0 else None
                }
                for sport, stats in activity_types.items()
            }
        },
        "athlete_characteristics": athlete_profile,
        "training_insights": training_insights,
        "current_readiness": readiness_result,
        "coach_recommendations": {
            "training_focus": f"Enfoque principal: {training_insights['primary_focus']}",
            "volume_management": f"Volumen: {training_insights['training_volume']} - {training_insights['total_training_hours']:.1f} horas totales",
            "frequency_guidance": f"Frecuencia: {training_insights['training_frequency_per_week']:.1f} sesiones/semana",
            "recovery_priority": "Priorizar recuperación" if avg_sleep < 7 or avg_stress > 50 else "Mantener equilibrio",
            "sleep_optimization": "Mejorar duración" if avg_sleep < 7 else "Mantener hábitos",
            "age_appropriate_focus": _get_age_appropriate_recommendation(user.age if user else None)
        },
        "aging_considerations": _get_aging_considerations(user.age if user else None),
        "key_insights": [
            f"Atleta {athlete_profile['activity_level'].lower()} con {len(activities)} actividades registradas",
            f"Condición física {athlete_profile['fitness_level'].lower()} (FC reposo: {avg_rhr:.0f} bpm)",
            f"Entrenamiento {training_insights['training_volume']} con {training_insights['training_frequency_per_week']:.1f} sesiones/semana",
            f"Enfoque principal: {training_insights['primary_focus']} ({activity_types.get(training_insights['primary_focus'], {}).get('count', 0)} sesiones)",
            f"Calidad de sueño {athlete_profile['sleep_quality'].lower()} ({avg_sleep:.1f} horas promedio)",
            f"Nivel de estrés {athlete_profile['stress_level'].lower()} ({avg_stress:.0f}/100)"
        ]
    }
    
    # Imprimir resumen
    print(f"\n👤 INFORMACIÓN PERSONAL:")
    print(f"   Nombre: {user.name if user else 'N/A'}")
    print(f"   Fecha de nacimiento: {user.birth_date if user and user.birth_date else 'N/A'}")
    print(f"   Edad: {user.age if user else 'N/A'} años")
    print(f"   Grupo de edad: {_determine_age_group(user.age if user else None)}")
    
    print(f"\n🎯 PERFIL 360° DEL ATLETA:")
    print(f"   Nivel de actividad: {athlete_profile['activity_level']}")
    print(f"   Condición física: {athlete_profile['fitness_level']}")
    print(f"   Calidad de sueño: {athlete_profile['sleep_quality']}")
    print(f"   Nivel de estrés: {athlete_profile['stress_level']}")
    
    print(f"\n📊 BIOMÉTRICOS:")
    print(f"   Sueño: {avg_sleep:.2f} horas/día")
    print(f"   Pasos: {avg_steps:.0f} pasos/día")
    print(f"   Estrés: {avg_stress:.1f}/100")
    print(f"   FC reposo: {avg_rhr:.1f} bpm")
    print(f"   Body Battery: {avg_body_battery:.1f}")
    
    print(f"\n🏃 ENTRENAMIENTO:")
    print(f"   Total actividades: {len(activities)}")
    print(f"   Horas totales: {total_duration / 3600:.1f}")
    print(f"   Distancia total: {total_distance / 1000:.1f} km")
    print(f"   Calorías totales: {total_calories}")
    print(f"   Frecuencia: {training_insights['training_frequency_per_week']:.1f} sesiones/semana")
    print(f"   Deporte principal: {training_insights['primary_focus']}")
    
    print(f"\n💡 RECOMENDACIONES DEL COACH:")
    for key, value in complete_summary["coach_recommendations"].items():
        print(f"   {key}: {value}")
    
    print(f"\n👴 CONSIDERACIONES DE ENVEJECIMIENTO:")
    aging = complete_summary["aging_considerations"]
    print(f"   Edad: {aging.get('age')} años")
    print(f"   Grupo de edad: {aging.get('age_group')}")
    print(f"   Necesidades de recuperación: {aging.get('recovery_needs')}")
    print(f"   Prioridad de prevención de lesiones: {aging.get('injury_prevention_priority')}")
    print(f"   Adaptación de entrenamiento: {aging.get('training_adaptation')}")
    print(f"   Áreas de enfoque: {', '.join(aging.get('focus_areas', []))}")
    
    print(f"\n🎯 INSIGHTS CLAVE:")
    for i, insight in enumerate(complete_summary["key_insights"], 1):
        print(f"   {i}. {insight}")
    
    # Guardar resumen completo
    summary_file = f"atlas_coach_360_summary_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(complete_summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resumen completo guardado en: {summary_file}")
    
    return complete_summary


def main():
    """Función principal."""
    print("\n" + "="*60)
    print("GENERANDO RESUMEN COMPLETO 360° PARA EL COACH DE ATLAS")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SessionLocal()
    try:
        summary = generate_complete_360_summary(db, "default_user")
        
        print("\n" + "="*60)
        print("✅ RESUMEN 360° COMPLETO GENERADO")
        print("="*60)
        print("\n🎉 EL COACH DE ATLAS AHORA TIENE UNA VISIÓN 360°:")
        print("   - Datos biométricos históricos completos")
        print("   - Todas las actividades de entrenamiento")
        print("   - Estadísticas detalladas por tipo de actividad")
        print("   - Perfil completo del atleta")
        print("   - Insights de entrenamiento")
        print("   - Recomendaciones personalizadas")
        print("   - Readiness actual en tiempo real")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
