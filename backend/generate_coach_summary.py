"""
Generar resumen inicial para el coach de Atlas con datos disponibles
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
from app.services.readiness_service import ReadinessService
from datetime import datetime, date, timedelta
import json

def generate_initial_coach_summary(db, user_id):
    """Genera un resumen inicial con los datos disponibles."""
    print("\n" + "="*60)
    print("GENERANDO RESUMEN INICIAL PARA EL COACH DE ATLAS")
    print("="*60)
    
    # Obtener estadísticas de datos
    biometrics_count = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).count()
    
    workouts_count = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).count()
    
    # Rango de fechas
    oldest_biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.asc()).first()
    
    newest_biometric = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.desc()).first()
    
    print(f"\n📊 COBERTURA DE DATOS:")
    print(f"   Registros biométricos: {biometrics_count} días")
    print(f"   Actividades: {workouts_count}")
    print(f"   Fecha más antigua: {oldest_biometric.date if oldest_biometric else 'N/A'}")
    print(f"   Fecha más reciente: {newest_biometric.date if newest_biometric else 'N/A'}")
    
    if oldest_biometric and newest_biometric:
        try:
            oldest_date = datetime.strptime(oldest_biometric.date, "%Y-%m-%d").date()
            newest_date = datetime.strptime(newest_biometric.date, "%Y-%m-%d").date()
            days_covered = (newest_date - oldest_date).days
            print(f"   Días cubiertos: {days_covered}")
            print(f"   Progreso de descarga: {biometrics_count / 730 * 100:.1f}%")
        except:
            pass
    
    # Calcular promedios de métricas clave (todos los datos disponibles)
    all_biometrics = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).all()
    
    avg_sleep = 0
    avg_steps = 0
    avg_hrv = 0
    avg_stress = 0
    avg_rhr = 0
    avg_body_battery = 0
    
    sleep_count = 0
    steps_count = 0
    hrv_count = 0
    stress_count = 0
    rhr_count = 0
    body_battery_count = 0
    
    sleep_values = []
    steps_values = []
    hrv_values = []
    stress_values = []
    rhr_values = []
    body_battery_values = []
    
    for bio in all_biometrics:
        if bio.data:
            try:
                data = json.loads(bio.data)
                
                if data.get("sleep"):
                    sleep_values.append(data["sleep"])
                    avg_sleep += data["sleep"]
                    sleep_count += 1
                
                if data.get("steps"):
                    steps_values.append(data["steps"])
                    avg_steps += data["steps"]
                    steps_count += 1
                
                if data.get("hrv"):
                    hrv_values.append(data["hrv"])
                    avg_hrv += data["hrv"]
                    hrv_count += 1
                
                if data.get("stress"):
                    stress_values.append(data["stress"])
                    avg_stress += data["stress"]
                    stress_count += 1
                
                if data.get("heartRate"):
                    rhr_values.append(data["heartRate"])
                    avg_rhr += data["heartRate"]
                    rhr_count += 1
                
                if bio.body_battery:
                    body_battery_values.append(bio.body_battery)
                    avg_body_battery += bio.body_battery
                    body_battery_count += 1
                    
            except:
                pass
    
    # Calcular promedios
    avg_sleep = avg_sleep / sleep_count if sleep_count > 0 else 0
    avg_steps = avg_steps / steps_count if steps_count > 0 else 0
    avg_hrv = avg_hrv / hrv_count if hrv_count > 0 else 0
    avg_stress = avg_stress / stress_count if stress_count > 0 else 0
    avg_rhr = avg_rhr / rhr_count if rhr_count > 0 else 0
    avg_body_battery = avg_body_battery / body_battery_count if body_battery_count > 0 else 0
    
    # Calcular estadísticas adicionales
    import statistics
    
    sleep_std = statistics.stdev(sleep_values) if len(sleep_values) >= 2 else 0
    steps_std = statistics.stdev(steps_values) if len(steps_values) >= 2 else 0
    hrv_std = statistics.stdev(hrv_values) if len(hrv_values) >= 2 else 0
    stress_std = statistics.stdev(stress_values) if len(stress_values) >= 2 else 0
    rhr_std = statistics.stdev(rhr_values) if len(rhr_values) >= 2 else 0
    
    print(f"\n📊 ESTADÍSTICAS GENERALES (TODOS LOS DATOS):")
    print(f"   Sueño: {avg_sleep:.2f} ± {sleep_std:.2f} horas/día ({sleep_count} días)")
    print(f"   Pasos: {avg_steps:.0f} ± {steps_std:.0f} pasos/día ({steps_count} días)")
    print(f"   HRV: {avg_hrv:.1f} ± {hrv_std:.1f} ms ({hrv_count} días)")
    print(f"   Estrés: {avg_stress:.1f} ± {stress_std:.1f}/100 ({stress_count} días)")
    print(f"   FC reposo: {avg_rhr:.1f} ± {rhr_std:.1f} bpm ({rhr_count} días)")
    print(f"   Body Battery: {avg_body_battery:.1f} ({body_battery_count} días)")
    
    # Calcular readiness actual
    print(f"\n🔄 READINESS ACTUAL:")
    try:
        readiness_result = ReadinessService.calculate(db, user_id)
        print(f"   Score: {readiness_result.get('score')}")
        print(f"   Status: {readiness_result.get('status')}")
        print(f"   Recomendación: {readiness_result.get('recommendation')}")
        
        components = readiness_result.get('components', {})
        print(f"   Componentes:")
        for key, value in components.items():
            print(f"     - {key}: {value}")
    except Exception as e:
        print(f"   Error calculando readiness: {e}")
    
    # Generar perfil de atleta
    print(f"\n🏃 PERFIL DE ATLETA:")
    
    # Determinar tipo de atleta basado en datos
    if steps_count > 0:
        if avg_steps >= 15000:
            athlete_type = "Muy activo"
        elif avg_steps >= 10000:
            athlete_type = "Activo"
        elif avg_steps >= 7000:
            athlete_type = "Moderadamente activo"
        else:
            athlete_type = "Sedentario"
        print(f"   Nivel de actividad: {athlete_type}")
    
    if sleep_count > 0:
        if avg_sleep >= 8:
            sleep_quality = "Excelente"
        elif avg_sleep >= 7:
            sleep_quality = "Bueno"
        elif avg_sleep >= 6:
            sleep_quality = "Adecuado"
        else:
            sleep_quality = "Insuficiente"
        print(f"   Calidad de sueño: {sleep_quality}")
    
    if hrv_count > 0:
        if avg_hrv >= 60:
            recovery_capacity = "Alta"
        elif avg_hrv >= 45:
            recovery_capacity = "Media"
        else:
            recovery_capacity = "Baja"
        print(f"   Capacidad de recuperación: {recovery_capacity}")
    
    if stress_count > 0:
        if avg_stress <= 30:
            stress_level = "Bajo"
        elif avg_stress <= 50:
            stress_level = "Moderado"
        else:
            stress_level = "Alto"
        print(f"   Nivel de estrés: {stress_level}")
    
    # Generar resumen JSON
    summary = {
        "user_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "data_coverage": {
            "total_biometrics_records": biometrics_count,
            "total_activities": workouts_count,
            "oldest_date": oldest_biometric.date if oldest_biometric else None,
            "newest_date": newest_biometric.date if newest_biometric else None,
            "download_progress": f"{biometrics_count / 730 * 100:.1f}%"
        },
        "overall_statistics": {
            "sleep": {
                "average": round(avg_sleep, 2),
                "std": round(sleep_std, 2),
                "days_with_data": sleep_count
            },
            "steps": {
                "average": round(avg_steps, 0),
                "std": round(steps_std, 0),
                "days_with_data": steps_count
            },
            "hrv": {
                "average": round(avg_hrv, 1),
                "std": round(hrv_std, 1),
                "days_with_data": hrv_count
            },
            "stress": {
                "average": round(avg_stress, 1),
                "std": round(stress_std, 1),
                "days_with_data": stress_count
            },
            "resting_heart_rate": {
                "average": round(avg_rhr, 1),
                "std": round(rhr_std, 1),
                "days_with_data": rhr_count
            },
            "body_battery": {
                "average": round(avg_body_battery, 1),
                "days_with_data": body_battery_count
            }
        },
        "athlete_profile": {
            "activity_level": athlete_type if steps_count > 0 else "Unknown",
            "sleep_quality": sleep_quality if sleep_count > 0 else "Unknown",
            "recovery_capacity": recovery_capacity if hrv_count > 0 else "Unknown",
            "stress_level": stress_level if stress_count > 0 else "Unknown"
        },
        "current_readiness": readiness_result if 'readiness_result' in locals() else None
    }
    
    # Guardar resumen en archivo
    summary_file = f"atlas_coach_summary_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resumen guardado en: {summary_file}")
    
    print(f"\n✅ EL COACH DE ATLAS AHORA TIENE CONTEXTO INICIAL:")
    print(f"   - {biometrics_count} días de datos históricos")
    print(f"   - Perfil de atleta completo")
    print(f"   - Estadísticas de todas las métricas clave")
    print(f"   - Readiness actual con recomendaciones")
    
    return summary


def main():
    """Función principal."""
    db = SessionLocal()
    try:
        summary = generate_initial_coach_summary(db, "default_user")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
