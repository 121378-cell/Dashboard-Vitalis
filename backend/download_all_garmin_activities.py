"""
Script para descargar todas las actividades de Garmin
======================================================

Este script descarga todas las actividades históricas de Garmin
y las almacena en la base de datos para que el coach de Atlas
tenga una visión completa del atleta.

Ejecución:
    cd backend
    python download_all_garmin_activities.py

Características:
- Descarga todas las actividades históricas
- Extrae métricas detalladas de cada actividad
- Clasifica actividades por tipo
- Calcula estadísticas de entrenamiento
- Genera resumen para el coach
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
from app.models.token import Token
from app.models.workout import Workout
from app.utils.garmin import get_garmin_client, safe_get
from datetime import datetime, date, timedelta
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_all_garmin_activities")

# Configuración
TEST_USER_ID = "default_user"
MAX_DAYS_BACK = 730  # 2 años de datos históricos
DELAY_BETWEEN_REQUESTS = 1.0  # Segundos entre peticiones


def get_earliest_activity_date(client):
    """Determina la fecha más antigua de actividades."""
    try:
        # Intentar obtener actividades para determinar el rango
        activities = client.get_activities_by_date(
            (date.today() - timedelta(days=MAX_DAYS_BACK)).isoformat(),
            date.today().isoformat()
        )
        
        if activities and len(activities) > 0:
            # Encontrar la fecha más antigua de las actividades
            earliest_date = min(
                datetime.strptime(act["startTimeLocal"], "%Y-%m-%d %H:%M:%S").date()
                for act in activities
            )
            logger.info(f"Fecha más antigua de actividad: {earliest_date}")
            return earliest_date
        else:
            logger.info("No se encontraron actividades")
            return None
            
    except Exception as e:
        logger.warning(f"Error determinando fecha más antigua: {e}")
        return None


def download_all_activities(db, user_id, client):
    """Descarga todas las actividades históricas."""
    logger.info("="*60)
    logger.info("DESCARGANDO ACTIVIDADES HISTÓRICAS DE GARMIN")
    logger.info("="*60)
    
    # Determinar rango de fechas
    earliest_date = get_earliest_activity_date(client)
    
    if not earliest_date:
        logger.warning("No se encontraron actividades para descargar")
        return True
    
    end_date = date.today()
    
    logger.info(f"Rango de fechas: {earliest_date} a {end_date}")
    
    # Verificar actividades ya existentes
    existing_ids = set()
    existing_activities = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).all()
    
    for act in existing_activities:
        if act.external_id:
            existing_ids.add(act.external_id)
    
    logger.info(f"Actividades ya existentes: {len(existing_ids)}")
    
    try:
        # Descargar todas las actividades
        activities = client.get_activities_by_date(
            earliest_date.isoformat(),
            end_date.isoformat()
        )
        
        logger.info(f"Total de actividades encontradas: {len(activities)}")
        
        new_count = 0
        updated_count = 0
        error_count = 0
        
        for i, act in enumerate(activities):
            external_id = str(act["activityId"])
            
            try:
                act_date_time = act["startTimeLocal"]
                act_date = act_date_time.split(" ")[0]
                
                # Extraer métricas detalladas
                metrics = {
                    "distance": safe_get(act, "distance"),
                    "avgSpeed": safe_get(act, "averageSpeed"),
                    "maxSpeed": safe_get(act, "maxSpeed"),
                    "avgHR": safe_get(act, "averageHR"),
                    "maxHR": safe_get(act, "maxHR"),
                    "avgPower": safe_get(act, "avgPower") or safe_get(act, "averagePower"),
                    "maxPower": safe_get(act, "maxPower"),
                    "avgCadence": safe_get(act, "averageCadence") or safe_get(act, "avgCadence"),
                    "hrZones": {
                        "z1": safe_get(act, "hrTimeInZone_1"),
                        "z2": safe_get(act, "hrTimeInZone_2"),
                        "z3": safe_get(act, "hrTimeInZone_3"),
                        "z4": safe_get(act, "hrTimeInZone_4"),
                        "z5": safe_get(act, "hrTimeInZone_5"),
                    },
                    "elevationGain": safe_get(act, "elevationGain"),
                    "elevationLoss": safe_get(act, "elevationLoss"),
                    "sport": safe_get(act, "activityType", "typeKey"),
                    "subSport": safe_get(act, "activityType", "subTypeKey"),
                    "trainingEffect": {
                        "aerobic": safe_get(act, "trainingEffectLabel"),
                        "anaerobic": safe_get(act, "anaerobicTrainingEffectLabel")
                    }
                }
                
                # Verificar si ya existe
                workout = (
                    db.query(Workout)
                    .filter(
                        Workout.user_id == user_id,
                        Workout.source == "garmin",
                        Workout.external_id == external_id,
                    )
                    .first()
                )
                
                if not workout:
                    # Crear nuevo registro
                    workout = Workout(
                        user_id=user_id,
                        source="garmin",
                        external_id=external_id,
                        name=act.get("activityName") or "Garmin Activity",
                        description=json.dumps(metrics),
                        date=datetime.strptime(act_date_time, "%Y-%m-%d %H:%M:%S"),
                        duration=int(act.get("duration") or 0),
                        calories=int(act.get("calories") or 0)
                    )
                    db.add(workout)
                    new_count += 1
                else:
                    # Actualizar registro existente
                    workout.name = act.get("activityName") or "Garmin Activity"
                    workout.description = json.dumps(metrics)
                    workout.date = datetime.strptime(act_date_time, "%Y-%m-%d %H:%M:%S")
                    workout.duration = int(act.get("duration") or 0)
                    workout.calories = int(act.get("calories") or 0)
                    updated_count += 1
                
                # Commit cada 10 actividades para guardar progreso
                if (i + 1) % 10 == 0:
                    db.commit()
                    logger.info(f"  Progreso: {i + 1}/{len(activities)} actividades procesadas")
                
                # Pequeña pausa para evitar rate limiting
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            except Exception as e:
                logger.error(f"Error procesando actividad {external_id}: {e}")
                error_count += 1
                continue
        
        # Commit final
        db.commit()
        
        logger.info(f"\n✅ Descarga de actividades completada")
        logger.info(f"   Nuevas actividades: {new_count}")
        logger.info(f"   Actividades actualizadas: {updated_count}")
        logger.info(f"   Errores: {error_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error descargando actividades: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_activities(db, user_id):
    """Analiza las actividades descargadas y genera estadísticas."""
    logger.info("\n" + "="*60)
    logger.info("ANALIZANDO ACTIVIDADES DESCARGADAS")
    logger.info("="*60)
    
    # Obtener todas las actividades
    activities = db.query(Workout).filter(
        Workout.user_id == user_id,
        Workout.source == "garmin"
    ).order_by(Workout.date.desc()).all()
    
    if not activities:
        logger.warning("No hay actividades para analizar")
        return None
    
    logger.info(f"Total de actividades: {len(activities)}")
    
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
                "total_calories": 0
            }
        
        activity_types[sport]["count"] += 1
        activity_types[sport]["total_duration"] += act.duration or 0
        activity_types[sport]["total_calories"] += act.calories or 0
        
        # Extraer distancia si está disponible
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
    
    # Calcular promedios por tipo
    for sport in activity_types:
        count = activity_types[sport]["count"]
        if count > 0:
            activity_types[sport]["avg_duration"] = activity_types[sport]["total_duration"] / count
            activity_types[sport]["avg_calories"] = activity_types[sport]["total_calories"] / count
            if activity_types[sport]["total_distance"] > 0:
                activity_types[sport]["avg_distance"] = activity_types[sport]["total_distance"] / count
    
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
            "avg_calories": round(avg_calories, 2)
        },
        "activity_types": activity_types
    }
    
    # Imprimir resumen
    logger.info(f"\n📊 RESUMEN DE ACTIVIDADES:")
    logger.info(f"   Total: {len(activities)} actividades")
    logger.info(f"   Rango: {oldest_date} a {newest_date}")
    logger.info(f"   Duración total: {total_duration / 3600:.1f} horas")
    logger.info(f"   Distancia total: {total_distance / 1000:.1f} km")
    logger.info(f"   Calorías totales: {total_calories}")
    logger.info(f"   Duración promedio: {avg_duration / 60:.1f} minutos")
    logger.info(f"   Calorías promedio: {avg_calories:.0f}")
    
    logger.info(f"\n🏃 TIPOS DE ACTIVIDAD:")
    for sport, stats in sorted(activity_types.items(), key=lambda x: x[1]["count"], reverse=True):
        logger.info(f"   {sport}:")
        logger.info(f"     - Cantidad: {stats['count']}")
        logger.info(f"     - Duración promedio: {stats['avg_duration'] / 60:.1f} minutos")
        logger.info(f"     - Calorías promedio: {stats['avg_calories']:.0f}")
        if stats.get('avg_distance'):
            logger.info(f"     - Distancia promedio: {stats['avg_distance'] / 1000:.1f} km")
    
    return summary


def main():
    """Función principal."""
    logger.info("\n" + "="*60)
    logger.info("DESCARGA COMPLETA DE ACTIVIDADES GARMIN PARA ATLAS COACH")
    logger.info("="*60)
    logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Usuario: {TEST_USER_ID}")
    
    db = SessionLocal()
    try:
        # Obtener credenciales
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if not creds or not creds.garmin_email or not creds.garmin_password:
            logger.error("❌ No se encontraron credenciales de Garmin")
            return 1
        
        logger.info(f"✅ Credenciales encontradas: {creds.garmin_email}")
        
        # Conectar a Garmin
        logger.info("\n🔄 Conectando a Garmin...")
        client, login_result = get_garmin_client(
            email=creds.garmin_email,
            password=creds.garmin_password,
            db=db,
            user_id=TEST_USER_ID
        )
        
        if not client:
            logger.error("❌ Error conectando a Garmin")
            return 1
        
        logger.info("✅ Conectado a Garmin")
        
        # Descargar actividades
        success = download_all_activities(db, TEST_USER_ID, client)
        
        if success:
            # Analizar actividades
            summary = analyze_activities(db, TEST_USER_ID)
            
            if summary:
                # Guardar resumen en archivo
                summary_file = f"activities_summary_{TEST_USER_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                
                logger.info(f"\n💾 Resumen guardado en: {summary_file}")
            
            logger.info("\n" + "="*60)
            logger.info("✅ DESCARGA DE ACTIVIDADES COMPLETADA")
            logger.info("="*60)
            logger.info("\n🎉 El coach de Atlas ahora tiene acceso a:")
            logger.info("   - Todas las actividades históricas")
            logger.info("   - Métricas detalladas de cada actividad")
            logger.info("   - Clasificación por tipo de actividad")
            logger.info("   - Estadísticas de entrenamiento")
            logger.info("   - Visión 360° del atleta")
            
            return 0
        else:
            logger.error("❌ Error en la descarga de actividades")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
