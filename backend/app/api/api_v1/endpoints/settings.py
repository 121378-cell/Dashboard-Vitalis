from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.token import Token
from app.models.user import User
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ServiceSettings(BaseModel):
    wger_api_key: Optional[str] = None
    hevy_username: Optional[str] = None

@router.get("/services")
def get_services(db: Session = Depends(get_db), user_id: str = "default_user"):
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if not creds:
        return {"wger_api_key": "", "hevy_username": ""}
    return {
        "wger_api_key": creds.wger_api_key,
        "hevy_username": creds.hevy_username
    }

@router.post("/services")
def save_services(settings: ServiceSettings, db: Session = Depends(get_db), user_id: str = "default_user"):
    creds = db.query(Token).filter(Token.user_id == user_id).first()
    if not creds:
        creds = Token(user_id=user_id)
        db.add(creds)
    
    if settings.wger_api_key is not None:
        creds.wger_api_key = settings.wger_api_key
    if settings.hevy_username is not None:
        creds.hevy_username = settings.hevy_username
        
    db.commit()
    return {"success": True}

@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user_id: str = "default_user"):
    """Devuelve el perfil guardado del usuario."""
    user = db.query(User).filter(User.id == user_id).first()
    token = db.query(Token).filter(Token.user_id == user_id).first()
    
    if not user:
        return {"exists": False}
    
    return {
        "exists": True,
        "user_id": user_id,
        "name": user.name if user and user.name else "Sergi",
        "age": 47,
        "goal": "Proyecto 31/07 - Definición y Fuerza",
        "bench_press_max": 50,
        "leg_press_max": 100,
        "garmin_connected": bool(token and token.garmin_email),
        "garmin_email": token.garmin_email if token else None,
    }

@router.post("/profile")
def save_profile(
    name: str = Body(...),
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """Guarda el nombre del perfil del usuario."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, name=name)
        db.add(user)
    else:
        user.name = name
    db.commit()
    return {"success": True, "name": name}
