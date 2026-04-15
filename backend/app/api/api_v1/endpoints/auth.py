from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.token import Token
from app.models.user import User
from app.utils.garmin import get_garmin_client
import json
import logging

router = APIRouter()
logger = logging.getLogger("app.api.endpoints.auth")

@router.post("/garmin/login")
def garmin_login(
    db: Session = Depends(get_db),
    email: str = Body(...),
    password: str = Body(...),
    user_id: str = Body("default_user")
):
    """Login to Garmin and store tokens/session."""
    try:
        # Ensure user exists
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            db_user = User(id=user_id, name="Atleta ATLAS")
            db.add(db_user)
            db.commit()

        # Attempt Garmin Login
        client, _ = get_garmin_client(email=email, password=password, db=db, user_id=user_id)
        if not client:
            raise HTTPException(status_code=401, detail="Invalid Garmin credentials or rate limit exceeded")
        
        # Store or Update tokens
        token_entry = db.query(Token).filter(Token.user_id == user_id).first()
        if not token_entry:
            token_entry = Token(user_id=user_id)
            db.add(token_entry)
        
        token_entry.garmin_email = email
        token_entry.garmin_password = password
        
        db.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"Garmin login failed: {e}")
        # Log the traceback for better debugging
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_auth_status(db: Session = Depends(get_db), user_id: str = "default_user"):
    token = db.query(Token).filter(Token.user_id == user_id).first()
    return {"authenticated": bool(token and token.garmin_email)}

@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db), user_id: str = "default_user"):
    db.query(Token).filter(Token.user_id == user_id).delete()
    db.commit()
    return {"success": True}
