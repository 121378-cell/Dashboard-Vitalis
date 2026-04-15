"""
Servicio de sincronización Strava → Atlas Workouts
"""

from sqlalchemy.orm import Session
from app.models.token import Token
from app.models.workout import Workout
from app.core.config import settings
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger("app.services.strava")

STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaService:
    """Servicio para sincronizar datos de Strava con Atlas"""
    
    @staticmethod
    async def sync_recent_activities(
        db: Session, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Sincroniza actividades de Strava de los últimos N días.
        
        Returns:
            dict con: synced_count, skipped_count, errors
        """
        token = db.query(Token).filter(Token.user_id == user_id).first()
        
        if not token or not token.strava_access_token:
            return {
                "success": False,
                "error": "Strava no conectado",
                "synced_count": 0,
                "skipped_count": 0
            }
        
        # Verificar si token expiró
        if token.strava_expires_at and datetime.utcnow() > token.strava_expires_at:
            refreshed = await StravaService._refresh_token(token, db)
            if not refreshed:
                return {
                    "success": False,
                    "error": "Token expirado y no se pudo renovar",
                    "synced_count": 0,
                    "skipped_count": 0
                }
        
        try:
            # Calcular timestamp para 'after'
            after_timestamp = int((datetime.utcnow() - timedelta(days=days)).timestamp())
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{STRAVA_API_BASE}/athlete/activities",
                    headers={"Authorization": f"Bearer {token.strava_access_token}"},
                    params={
                        "after": after_timestamp,
                        "per_page": 100  # Máximo por página
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                activities = response.json()
            
            logger.info(f"Obtenidas {len(activities)} actividades de Strava para user {user_id}")
            
            # Sincronizar cada actividad
            synced_count = 0
            skipped_count = 0
            errors = []
            
            for activity in activities:
                try:
                    result = StravaService._save_activity_as_workout(db, user_id, activity)
                    if result:
                        synced_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    logger.error(f"Error guardando actividad {activity.get('id')}: {e}")
                    errors.append(str(e))
                    skipped_count += 1
            
            return {
                "success": True,
                "synced_count": synced_count,
                "skipped_count": skipped_count,
                "total_received": len(activities),
                "errors": errors[:5]  # Solo primeros 5 errores
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP de Strava: {e}")
            return {
                "success": False,
                "error": f"Error Strava API: {e.response.status_code}",
                "synced_count": 0,
                "skipped_count": 0
            }
        except Exception as e:
            logger.error(f"Error sincronizando Strava: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced_count": 0,
                "skipped_count": 0
            }
    
    @staticmethod
    def _save_activity_as_workout(
        db: Session, 
        user_id: str, 
        activity: Dict[str, Any]
    ) -> bool:
        """
        Convierte una actividad de Strava en un Workout y lo guarda.
        
        Returns:
            True si se guardó, False si ya existía o hubo error
        """
        # Extraer datos de Strava
        strava_id = str(activity.get("id"))
        name = activity.get("name", "Actividad Strava")
        activity_type = activity.get("type", "Workout")
        
        # Parsear fecha
        start_date = activity.get("start_date_local", "")
        try:
            date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
        except:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Verificar si ya existe (evitar duplicados)
        existing = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.notes.contains(f"strava_id:{strava_id}")
        ).first()
        
        if existing:
            logger.debug(f"Actividad Strava {strava_id} ya existe, saltando")
            return False
        
        # Mapear tipo de actividad Strava → tipo Atlas
        type_mapping = {
            "Run": "cardio",
            "Ride": "cardio",
            "Swim": "cardio",
            "Workout": "strength",
            "WeightTraining": "strength",
            "Hike": "cardio",
            "Walk": "cardio",
            "VirtualRide": "cardio",
            "Yoga": "flexibility",
            "Crossfit": "strength",
            "HIIT": "cardio"
        }
        atlas_type = type_mapping.get(activity_type, "cardio")
        
        # Extraer métricas
        duration_minutes = activity.get("moving_time", 0) // 60  # segundos → minutos
        distance_km = activity.get("distance", 0) / 1000  # metros → km
        calories = activity.get("calories", 0)
        avg_hr = activity.get("average_heartrate")
        max_hr = activity.get("max_heartrate")
        
        # Calcular intensidad estimada
        intensity = "medium"
        if avg_hr and max_hr:
            hr_percent = avg_hr / max_hr if max_hr > 0 else 0
            if hr_percent > 0.85:
                intensity = "high"
            elif hr_percent < 0.65:
                intensity = "low"
        elif duration_minutes > 60:
            intensity = "high"
        elif duration_minutes < 20:
            intensity = "low"
        
        # Crear workout
        workout = Workout(
            user_id=user_id,
            date=date_str,
            type=atlas_type,
            duration=duration_minutes,
            intensity=intensity,
            notes=f"{name} | strava_id:{strava_id} | Tipo: {activity_type} | Dist: {distance_km:.1f}km | Avg HR: {avg_hr or 'N/A'}",
            completed=True,
            source="strava"
        )
        
        db.add(workout)
        db.commit()
        
        logger.info(f"Workout creado desde Strava: {strava_id} - {name}")
        return True
    
    @staticmethod
    async def _refresh_token(token: Token, db: Session) -> bool:
        """Renueva el token de Strava"""
        if not token.strava_refresh_token:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{STRAVA_API_BASE}/oauth/token",
                    data={
                        "client_id": settings.STRAVA_CLIENT_ID,
                        "client_secret": settings.STRAVA_CLIENT_SECRET,
                        "refresh_token": token.strava_refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token.strava_access_token = data.get("access_token")
                    token.strava_refresh_token = data.get("refresh_token")
                    expires_at = data.get("expires_at")
                    if expires_at:
                        token.strava_expires_at = datetime.fromtimestamp(expires_at)
                    db.commit()
                    logger.info("Token de Strava renovado")
                    return True
                else:
                    logger.error(f"Error renovando token: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error en refresh: {e}")
            return False
    
    @staticmethod
    async def get_activity_details(
        db: Session,
        user_id: str,
        activity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtiene detalles completos de una actividad específica"""
        token = db.query(Token).filter(Token.user_id == user_id).first()
        
        if not token or not token.strava_access_token:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{STRAVA_API_BASE}/activities/{activity_id}",
                    headers={"Authorization": f"Bearer {token.strava_access_token}"},
                    params={"include_all_efforts": True},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo detalles: {e}")
            return None


# Instancia para importar fácilmente
strava_service = StravaService()
