"""
Analizar actividades descargadas y actualizar perfil del atleta
================================================================

Este script analiza las actividades descargadas de Garmin y
actualiza el perfil del atleta para incluir una visión 360°.

Ejecución:
    cd backend
    python analyze_activities.py
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
from app.models.workout import Workout
from app.models.biometrics import Biometrics
from datetime import datetime, timedelta
import json
import statistics

def analyze_activities(db, user_id):
    """Analiza las actividades descargadas."""
    print("\n" + "="*60)
    print("ANALIZANDO ACTIVIDADES DESCARGADAS")
    print("="*60)
    
    # Obtener todas las actividades
    activities = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).order_by(Workout.date.desc()).all()
    
    if not activities:
        print("❌ No hay actividades para analizar")
        return None
    
    print(f"✅ Total de actividades: {len(activities)}")
    
    # Clasificar actividades por tipo
    activity_types = {}
    total_duration = 0
    total_distance = 0
    total_calories = 0
    
    for act in activities:
        # Extraer tipo de actividad
        sport = "unknown"
        if act.description:
            try:
                metrics = json.loads(act.description)
                sport = metrics.get("sport", "unknown")
            except:
                pass
        
        # Contar por tipo
        if sport not in activity_types:
            activity_types[sport] = {
                "count": 0,
                "total_duration": 0,
                "total_distance": 0,
                "total_calories": 0,
                "durations": [],
                "distances": [],
                "calories": []
            }
        
        activity_types[sport]["count"] += 1
        activity_types[sport]["total_duration"] += act.duration or 0
        activity_types[sport]["total_calories"] += act.calories or 0
        
        if act.duration:
            activity_types[sport]["durations"].append(act.duration)
        
        if act.calories:
            activity_types[sport]["calories"].append(act.calories)
        
        # Extraer distancia si está disponible
        if act.description:
            try:
                metrics = json.loads(act.description)
                distance = metrics.get("distance")
                if distance:
                    activity_types[sport]["total_distance"] += distance
                    activity_types[sport]["distances"].append(distance)
                    total_distance += distance
            except:
                pass
        
        total_duration += act.duration or 0
        total_calories += act.calories or 0
    
    # Calcular estadísticas por tipo
    for sport in activity_types:
        count = activity_types[sport]["count"]
        if count > 0:
            activity_types[sport]["avg_duration"] = activity_types[sport]["total_duration"] / count
            activity_types[sport]["avg_calories"] = activity_types[sport]["total_calories"] / count
            
            # Calcular desviación estándar
            if len(activity_types[sport]["durations"]) >= 2:
                activity_types[sport]["std_duration"] = statistics.stdev(activity_types[sport]["durations"])
            else:
                activity_types[sport]["std_duration"] = 0
            
            if len(activity_types[sport]["calories"]) >= 2:
                activity_types[sport]["std_calories"] = statistics.stdev(activity_types[sport]["calories"])
            else:
                activity_types[sport]["std_calories"] = 0
            
            if activity_types[sport]["total_distance"] > 0:
                activity_types[sport]["avg_distance"] = activity_types[sport]["total_distance"] / count
                
                if len(activity_types[sport]["distances"]) >= 2:
                    activity_types[sport]["std_distance"] = statistics.stdev(activity_types[sport]["distances"])
                else:
                    activity_types[sport]["std_distance"] = 0
    
    # Calcular estadísticas generales
    avg_duration = total_duration / len(activities) if len(activities) > 0 else 0
    avg_calories = total_calories / len(activities) if len(activities) > 0 else 0
    
    # Determinar rango de fechas
    if activities:
        oldest_activity = activities[-1].date
        newest_activity = activities[0].date
        
        try:
            if isinstance(oldest_activity, str):
                oldest_date = datetime.strptime(oldest_activity, "%Y-%m-%d %H:%M:%S").date()
            else:
                oldest_date = oldest_activity.date()
            
            if isinstance(newest_activity, str):
                newest_date = datetime.strptime(newest_activity, "%Y-%m-%d %H:%M:%S").date()
            else:
                newest_date = newest_activity.date()
            
            days_span = (newest_date - oldest_date).days
        except:
            days_span = 0
    else:
        oldest_date = None
        newest_date = None
        days_span = 0
    
    # Calcular frecuencia de entrenamiento
    if days_span > 0:
        training_frequency = len(activities) / days_span * 7  # actividades por semana
    else:
        training_frequency = 0
    
    # Determinar tipo de entrenamiento principal
    primary_sport = max(activity_types.items(), key=lambda x: x[1]["count"])[0] if activity_types else "unknown"
    
    # Generar resumen
    summary = {
        "total_activities": len(activities),
        "date_range": {
            "oldest": oldest_date.isoformat() if oldest_date else None,
            "newest": newest_date.isoformat() if newest_date else None,
            "days_span": days_span
        },
        "overall_stats": {
            "total_duration_seconds": total_duration,
            "total_distance_meters": total_distance,
            "total_calories": total_calories,
            "avg_duration_seconds": round(avg_duration, 2),
            "avg_calories": round(avg_calories, 2),
            "training_frequency_per_week": round(training_frequency, 2)
        },
        "activity_types": activity_types,
        "primary_sport": primary_sport
    }
    
    # Imprimir resumen
    print(f"\n📊 RESUMEN DE ACTIVIDADES:")
    print(f"   Total: {len(activities)} actividades")
    print(f"   Rango: {oldest_date} a {newest_date}")
    print(f"   Días cubiertos: {days_span}")
    print(f"   Frecuencia de entrenamiento: {training_frequency:.1f} actividades/semana")
    print(f"   Duración total: {total_duration / 3600:.1f} horas")
    print(f"   Distancia total: {total_distance / 1000:.1f} km")
    print(f"   Calorías totales: {total_calories}")
    print(f"   Duración promedio: {avg_duration / 60:.1f} minutos")
    print(f"   Calorías promedio: {avg_calories:.0f}")
    print(f"   Deporte principal: {primary_sport}")
    
    print(f"\n🏃 TIPOS DE ACTIVIDAD:")
    for sport, stats in sorted(activity_types.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"   {sport}:")
        print(f"     - Cantidad: {stats['count']}")
        print(f"     - Duración promedio: {stats['avg_duration'] / 60:.1f} ± {stats['std_duration'] / 60:.1f} minutos")
        print(f"     - Calorías promedio: {stats['avg_calories']:.0f} ± {stats['std_calories']:.0f}")
        if stats.get('avg_distance'):
            print(f"     - Distancia promedio: {stats['avg_distance'] / 1000:.1f} ± {stats['std_distance'] / 1000:.1f} km")
    
    return summary


def update_athlete_profile_with_activities(db, user_id, activities_summary):
    """Actualiza el perfil del atleta con información de actividades."""
    print("\n" + "="*60)
    print("ACTUALIZANDO PERFIL DEL ATLETA CON ACTIVIDADES")
    print("="*60)
    
    if not activities_summary:
        print("❌ No hay resumen de actividades para actualizar")
        return False
    
    # Obtener datos biométricos para contexto completo
    biometrics_count = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).count()
    
    # Generar perfil completo 360°
    profile_360 = {
        "user_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "biometrics_coverage": {
            "total_days": biometrics_count
        },
        "activities_summary": activities_summary,
        "training_insights": {
            "training_volume": "high" if activities_summary["overall_stats"]["training_frequency_per_week"] >= 4 else "moderate",
            "consistency": "high" if activities_summary["overall_stats"]["training_frequency_per_week"] >= 3 else "moderate",
            "primary_focus": activities_summary["primary_sport"],
            "total_training_hours": activities_summary["overall_stats"]["total_duration_seconds"] / 3600
        }
    }
    
    # Guardar perfil completo
    profile_file = f"athlete_profile_360_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(profile_file, 'w', encoding='utf-8') as f:
        json.dump(profile_360, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Perfil 360° actualizado")
    print(f"💾 Perfil guardado en: {profile_file}")
    
    print(f"\n🎯 INSIGHTS DE ENTRENAMIENTO:")
    print(f"   Volumen de entrenamiento: {profile_360['training_insights']['training_volume']}")
    print(f"   Consistencia: {profile_360['training_insights']['consistency']}")
    print(f"   Enfoque principal: {profile_360['training_insights']['primary_focus']}")
    print(f"   Horas totales de entrenamiento: {profile_360['training_insights']['total_training_hours']:.1f}")
    
    return True


def main():
    """Función principal."""
    print("\n" + "="*60)
    print("ANÁLISIS DE ACTIVIDADES Y ACTUALIZACIÓN DE PERFIL 360°")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SessionLocal()
    try:
        # Analizar actividades
        activities_summary = analyze_activities(db, "default_user")
        
        if activities_summary:
            # Actualizar perfil del atleta
            success = update_athlete_profile_with_activities(db, "default_user", activities_summary)
            
            if success:
                print("\n" + "="*60)
                print("✅ PERFIL 360° DEL ATLETA COMPLETADO")
                print("="*60)
                print("\n🎉 EL COACH DE ATLAS AHORA TIENE UNA VISIÓN 360°:")
                print("   - Datos biométricos históricos")
                print("   - Todas las actividades de entrenamiento")
                print("   - Estadísticas detalladas por tipo de actividad")
                print("   - Frecuencia y consistencia de entrenamiento")
                print("   - Volumen total de entrenamiento")
                print("   - Enfoque principal del atleta")
                
                return 0
            else:
                print("❌ Error actualizando perfil")
                return 1
        else:
            print("❌ Error analizando actividades")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
