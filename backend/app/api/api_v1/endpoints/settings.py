from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.token import Token
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
