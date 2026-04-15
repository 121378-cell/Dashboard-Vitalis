"""
Strava OAuth2 Integration Endpoints
Documentación: https://developers.strava.com/docs/authentication/
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.token import Token
from app.models.user import User
from app.core.config import settings
from datetime import datetime, timedelta
import httpx
import logging
from app.services.strava_service import strava_service

router = APIRouter()
logger = logging.getLogger("app.api.endpoints.strava")

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


@router.get("/auth")
async def strava_auth():
    """
    Inicia el flujo OAuth2 de Strava.
    Redirige al usuario a Strava para autorización.
    """
    scope = "read,activity:read_all,profile:read_all"
    
    auth_url = (
        f"{STRAVA_AUTH_URL}?"
        f"client_id={settings.STRAVA_CLIENT_ID}&"
        f"redirect_uri={settings.STRAVA_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"approval_prompt=auto"
    )
    
    logger.info(f"Iniciando OAuth Strava: {auth_url}")
    return RedirectResponse(auth_url)


@router.get("/callback")
async def strava_callback(
    code: str = Query(..., description="Código de autorización de Strava"),
    scope: str = Query(None, description="Scope aprobado"),
    db: Session = Depends(get_db)
):
    """
    Callback de OAuth2 de Strava.
    Intercambia el código por tokens y los guarda en la BD.
    """
    user_id = "default_user"  # En producción, obtener del session/current_user
    
    try:
        logger.info(f"Recibido callback de Strava con código: {code[:10]}...")
        
        # Intercambiar código por tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": settings.STRAVA_CLIENT_ID,
                    "client_secret": settings.STRAVA_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Error de Strava: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error al obtener tokens de Strava: {response.text}"
                )
            
            token_data = response.json()
        
        # Extraer datos del token
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_at = token_data.get("expires_at")  # timestamp
        athlete = token_data.get("athlete", {})
        athlete_id = str(athlete.get("id"))
        
        logger.info(f"Tokens obtenidos para athlete_id: {athlete_id}")
        
        # Guardar en base de datos
        token_entry = db.query(Token).filter(Token.user_id == user_id).first()
        if not token_entry:
            token_entry = Token(user_id=user_id)
            db.add(token_entry)
            
            # Asegurar que el usuario existe
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(id=user_id, name="Atleta ATLAS")
                db.add(user)
        
        # Actualizar tokens de Strava
        token_entry.strava_access_token = access_token
        token_entry.strava_refresh_token = refresh_token
        token_entry.strava_expires_at = datetime.fromtimestamp(expires_at) if expires_at else None
        token_entry.strava_athlete_id = athlete_id
        token_entry.strava_connected = "true"
        
        db.commit()
        
        logger.info(f"✅ Strava conectado exitosamente para user_id: {user_id}")
        
        # Redirigir al frontend con éxito
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?strava_connected=true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en callback de Strava: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?strava_error=true"
        )


@router.get("/status")
async def strava_status(
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Verifica si el usuario tiene Strava conectado.
    """
    token = db.query(Token).filter(Token.user_id == user_id).first()
    
    is_connected = bool(
        token and 
        token.strava_connected == "true" and 
        token.strava_access_token
    )
    
    # Verificar si el token ha expirado
    expired = False
    if is_connected and token.strava_expires_at:
        expired = datetime.utcnow() > token.strava_expires_at
    
    return {
        "connected": is_connected,
        "expired": expired,
        "athlete_id": token.strava_athlete_id if token else None
    }


@router.post("/disconnect")
async def strava_disconnect(
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Desconecta Strava del usuario.
    """
    token = db.query(Token).filter(Token.user_id == user_id).first()
    
    if token:
        token.strava_access_token = None
        token.strava_refresh_token = None
        token.strava_expires_at = None
        token.strava_athlete_id = None
        token.strava_connected = "false"
        db.commit()
        logger.info(f"Strava desconectado para user_id: {user_id}")
    
    return {"success": True, "message": "Strava desconectado"}


@router.get("/activities")
async def get_strava_activities(
    limit: int = 30,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Obtiene las últimas actividades de Strava del usuario.
    """
    token = db.query(Token).filter(Token.user_id == user_id).first()
    
    if not token or not token.strava_access_token:
        raise HTTPException(
            status_code=401,
            detail="Strava no conectado"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {token.strava_access_token}"},
                params={"per_page": limit}
            )
            
            if response.status_code == 401:
                # Token expirado, intentar refresh
                logger.warning("Token de Strava expirado, intentando refresh...")
                refreshed = await _refresh_strava_token(token, db)
                if refreshed:
                    # Reintentar con nuevo token
                    response = await client.get(
                        f"{STRAVA_API_BASE}/athlete/activities",
                        headers={"Authorization": f"Bearer {token.strava_access_token}"},
                        params={"per_page": limit}
                    )
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="Token expirado y no se pudo renovar"
                    )
            
            response.raise_for_status()
            activities = response.json()
            
        return {
            "success": True,
            "count": len(activities),
            "activities": activities
        }
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error de Strava API: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error de Strava: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error obteniendo actividades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_strava_activities(
    days: int = 30,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Sincroniza actividades de Strava a Atlas Workouts.
    
    Args:
        days: Número de días hacia atrás para sincronizar (default: 30)
    """
    result = await strava_service.sync_recent_activities(db, user_id, days)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Error en sincronización")
        )
    
    return result


async def _refresh_strava_token(token: Token, db: Session) -> bool:
    """
    Renueva el token de Strava usando el refresh_token.
    """
    if not token.strava_refresh_token:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": settings.STRAVA_CLIENT_ID,
                    "client_secret": settings.STRAVA_CLIENT_SECRET,
                    "refresh_token": token.strava_refresh_token,
                    "grant_type": "refresh_token",
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                token.strava_access_token = data.get("access_token")
                token.strava_refresh_token = data.get("refresh_token")
                expires_at = data.get("expires_at")
                if expires_at:
                    token.strava_expires_at = datetime.fromtimestamp(expires_at)
                db.commit()
                logger.info("Token de Strava renovado exitosamente")
                return True
            else:
                logger.error(f"Error renovando token: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error en refresh token: {e}")
        return False
