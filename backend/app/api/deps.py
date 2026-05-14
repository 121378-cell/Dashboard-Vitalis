import os
import logging
from typing import Generator, Optional
from fastapi import HTTPException, status, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.user import User
from app.db.session import SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTPBearer scheme for JWT tokens
security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator:
    """Genera una sesion de base de datos y la cierra al finalizar."""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def verify_token(token: str) -> Optional[str]:
    """Verifica un JWT y devuelve el user_id."""
    try:
        from jose import JWTError, jwt
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            return user_id
    except ImportError:
        logger.warning("python-jose no instalado. No se puede verificar JWT.")
    except JWTError:
        logger.warning("Token JWT invalido o expirado.")
    except Exception as e:
        logger.debug(f"Error inesperado verificando token JWT: {e}")
    return None


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_user_id: Optional[str] = Header(None, alias="x-user-id")
) -> str:
    """
    Extrae el user_id del JWT Bearer token (primario) o x-user-id (fallback deprecated).

    En produccion, todos los clientes deben usar Authorization: Bearer <token>.
    El header x-user-id solo se acepta en desarrollo y mostrara una advertencia.
    """
    # Primario: JWT Bearer token via Authorization header
    if credentials:
        user_id = verify_token(credentials.credentials)
        if user_id:
            return user_id

    # Fallback temporal: x-user-id header (solo desarrollo)
    if x_user_id and x_user_id.strip():
        logger.warning(
            "Uso de x-user-id header DEPRECADO. "
            "Los clientes deben usar Authorization: Bearer <token>"
        )
        return x_user_id.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autorizacion requerido. Usa Authorization: Bearer <token>"
    )


def get_current_user_id_from_token(token: Optional[str] = None) -> str:
    """
    Extrae user_id de un token JWT (para WebSockets via query param).

    Los WebSockets no pueden usar headers personalizados facilmente,
    por lo que el token se pasa como query parameter: ?token=<jwt>
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido como query parameter. Ej: ws://host/path?token=<jwt>"
        )

    user_id = verify_token(token)
    if user_id:
        return user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido o expirado."
    )
