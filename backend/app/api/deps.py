import os
import logging
import secrets
import base64
from typing import Generator, Optional
from fastapi import HTTPException, status, Header
from sqlalchemy.orm import Session
from app.models.user import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Secret key for JWT - loads from environment
try:
    from jose import JWTError, jwt
except ImportError:
    logger.warning("python-jose no instalado. La verificación JWT no estará disponible.")
    jwt = None
    JWTError = None

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_db() -> Generator:
    """Genera una sesión de base de datos y la cierra al finalizar."""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def create_access_token(user_id: str, expires_delta: Optional[int] = None) -> str:
    """Crea un token JWT para el usuario."""
    if not jwt:
        logger.warning("python-jose no instalado. Token JWT simulado.")
        # Fallback si jose no está instalado
        return f"TEMP_TOKEN_{user_id}"
    
    expire = None
    if expires_delta:
        import datetime
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_delta)
    else:
        import datetime
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    """Decodifica un token JWT y devuelve el user_id."""
    if not jwt:
        logger.warning("python-jose no instalado. No se puede decodificar token.")
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return user_id
    except JWTError:
        return None

class AuthenticationError(Exception):
    """Excepción personalizada para errores de autenticación."""
    pass

def get_current_user_id(
    x_user_id: Optional[str] = Header(None, alias="x-user-id")
) -> str:
    """
    Extrae el user_id del header x-user-id. 
    El header es obligatorio y no puede estar vacío.
    """
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Header x-user-id requerido para operar."
    )

def get_current_user_id_from_token(token: Optional[str] = None) -> str:
    """
    Extrae user_id de un token JWT o del header x-user-id.
    """
    if not jwt:
        logger.debug("JWT no disponible, usando x-user-id como fallback")
        return "default_user"  # Sólo para desarrollo temprano
    
    if token:
        try:
            user_id = decode_access_token(token)
            if user_id:
                return user_id
        except Exception:
            pass
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autorización requerido."
    )