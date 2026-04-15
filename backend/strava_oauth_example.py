#!/usr/bin/env python3
"""
Ejemplo de OAuth2 con Strava API
Documentación: https://developers.strava.com/docs/authentication/
"""

import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import httpx

app = FastAPI()

# Configuración (obtener de https://www.strava.com/settings/api)
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "tu_client_id")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "tu_client_secret")
STRAVA_REDIRECT_URI = "http://localhost:8000/auth/strava/callback"


@app.get("/auth/strava")
async def strava_auth():
    """Paso 1: Redirigir a Strava para autorización"""
    scope = "read,activity:read_all,profile:read_all"
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={STRAVA_CLIENT_ID}&"
        f"redirect_uri={STRAVA_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope}"
    )
    return RedirectResponse(auth_url)


@app.get("/auth/strava/callback")
async def strava_callback(code: str):
    """Paso 2: Intercambiar code por tokens"""
    
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            }
        )
        
        tokens = response.json()
        # Guardar: tokens['access_token'], tokens['refresh_token'], tokens['expires_at']
        
        return {
            "message": "Conectado a Strava",
            "athlete": tokens.get("athlete"),
            "expires_at": tokens.get("expires_at")
        }


async def get_strava_activities(access_token: str, after: str = None, before: str = None):
    """Obtener actividades de Strava"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "after": after,  # timestamp
                "before": before,  # timestamp
                "per_page": 30
            }
        )
        return response.json()


async def get_activity_details(access_token: str, activity_id: int):
    """Obtener detalles completos de una actividad"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"include_all_efforts": True}
        )
        return response.json()


# Ejemplo de mapeo de datos Strava → tu modelo
def map_strava_to_workout(strava_activity: dict) -> dict:
    """Convierte actividad Strava a tu modelo Workout"""
    return {
        "date": strava_activity["start_date_local"][:10],
        "type": strava_activity["type"],  # Run, Ride, Swim, etc.
        "duration": strava_activity["elapsed_time"],  # segundos
        "distance": strava_activity.get("distance", 0),  # metros
        "avg_hr": strava_activity.get("average_heartrate"),
        "max_hr": strava_activity.get("max_heartrate"),
        "calories": strava_activity.get("calories"),
        "elevation_gain": strava_activity.get("total_elevation_gain"),
        "avg_speed": strava_activity.get("average_speed"),  # m/s
        "max_speed": strava_activity.get("max_speed"),
        "avg_cadence": strava_activity.get("average_cadence"),
        "avg_watts": strava_activity.get("average_watts"),
        "max_watts": strava_activity.get("max_watts"),
        "suffer_score": strava_activity.get("suffer_score"),  # Strava "Relative Effort"
        "device_name": strava_activity.get("device_name"),
        "garmin_id": strava_activity.get("external_id"),  # ID original de Garmin
    }


if __name__ == "__main__":
    print("=" * 60)
    print("STRAVA OAUTH2 - EJEMPLO DE INTEGRACIÓN")
    print("=" * 60)
    print()
    print("Pasos:")
    print("1. Crear app en https://www.strava.com/settings/api")
    print(f"2. Configurar redirect URI: {STRAVA_REDIRECT_URI}")
    print("3. Guardar STRAVA_CLIENT_ID y STRAVA_CLIENT_SECRET en .env")
    print("4. Ejecutar: uvicorn strava_oauth_example:app --reload")
    print("5. Visitar: http://localhost:8000/auth/strava")
    print()
    print("Datos disponibles:")
    print("- Actividades deportivas (run, bike, swim, etc.)")
    print("- Métricas: FC, potencia, cadencia, velocidad, temperatura")
    print("- Mapas GPS y segmentos")
    print("- Esfuerzo relativo (suffer_score)")
    print()
    print("Limitaciones:")
    print("- No datos de salud diaria (pasos, sueño, HRV en reposo)")
    print("- Solo actividades registradas con GPS")
    print("- Delay de sincronización Garmin→Strava de 5-15 min")
