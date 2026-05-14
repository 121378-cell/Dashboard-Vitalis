from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.models.token import Token
from app.models.user import User
from app.utils.garmin import get_garmin_client
from app.core.config import settings
import json
import logging
from datetime import datetime, timedelta

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
            db_user = User(id=user_id, name="Sergi")
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
def get_auth_status(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    token = db.query(Token).filter(Token.user_id == user_id).first()
    return {"authenticated": bool(token and token.garmin_email)}

@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    db.query(Token).filter(Token.user_id == user_id).delete()
    db.commit()
    return {"success": True}


@router.post("/jwt/login")
def jwt_login(
    db: Session = Depends(get_db),
    email: str = Body(..., description="User email"),
    password: str = Body(..., description="User password"),
):
    """
    Login with email/password, returns JWT access and refresh tokens.

    Para la app single-user:
    1. Busca el usuario por email en la tabla users
    2. Si JWT_ADMIN_PASSWORD esta configurado en .env, valida contra el
    3. Si no hay JWT_ADMIN_PASSWORD, acepta cualquier usuario existente (dev)
    """
    try:
        from jose import jwt as jose_jwt
    except ImportError:
        raise HTTPException(status_code=500, detail="JWT library not installed")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Fallback: buscar por id = email (default_user case)
        user = db.query(User).filter(User.id == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    # Validar password si JWT_ADMIN_PASSWORD esta configurado
    admin_password = settings.JWT_ADMIN_PASSWORD
    if admin_password:
        if password != admin_password:
            raise HTTPException(status_code=401, detail="Credenciales invalidas")
    else:
        # Sin password admin configurado: solo loguear warning (dev mode)
        logger.warning("JWT_ADMIN_PASSWORD no configurado. Login sin verificacion de password.")

    # Generar JWT access token
    access_expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expire = datetime.utcnow() + timedelta(days=90)

    access_token = jose_jwt.encode(
        {"sub": user.id, "exp": access_expire},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    refresh_token = jose_jwt.encode(
        {"sub": user.id, "exp": refresh_expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/jwt/register")
def jwt_register(
    db: Session = Depends(get_db),
    email: str = Body(...),
    password: str = Body(...),
    name: str = Body(...),
):
    """Register a new user, returns JWT tokens."""
    try:
        from jose import jwt as jose_jwt
    except ImportError:
        raise HTTPException(status_code=500, detail="JWT library not installed")

    # Check if user already exists
    existing = db.query(User).filter(
        (User.email == email) | (User.id == email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya esta registrado")        # Validar password si JWT_ADMIN_PASSWORD esta configurado
    admin_password = settings.JWT_ADMIN_PASSWORD
    if admin_password:
        if password != admin_password:
            raise HTTPException(status_code=400, detail="Credenciales invalidas")

    # Create new user with fields that exist on the model
    user = User(
        id=email,
        name=name,
        email=email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate tokens
    access_expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expire = datetime.utcnow() + timedelta(days=90)

    access_token = jose_jwt.encode(
        {"sub": user.id, "exp": access_expire},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    refresh_token = jose_jwt.encode(
        {"sub": user.id, "exp": refresh_expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/jwt/refresh")
def jwt_refresh(
    db: Session = Depends(get_db),
    refresh_token: str = Body(...),
):
    """Refresh an expired access token using a refresh token."""
    from jose import JWTError, jwt as jose_jwt

    try:
        payload = jose_jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token de refresh invalido")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalido")

        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        # Generar nuevo access token
        access_expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = jose_jwt.encode(
            {"sub": user.id, "exp": access_expire},
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de refresh invalido o expirado")
