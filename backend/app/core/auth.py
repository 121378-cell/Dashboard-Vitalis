from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_active_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Returns the current authenticated user from JWT Bearer token.

    Valida el token JWT, extrae el user_id y devuelve el objeto User.
    Lanza HTTP 401 si el token es invalido, expirado, o el usuario no existe.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autorizacion requerido (Authorization: Bearer <token>)"
        )

    auth_service = AuthService(db)
    user_id = auth_service.verify_token(credentials.credentials)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )

    if not getattr(user, 'is_active', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional auth — returns None if no token provided, no error."""
    if not credentials:
        return None

    auth_service = AuthService(db)
    user_id = auth_service.verify_token(credentials.credentials)

    if not user_id:
        return None

    return db.query(User).filter(User.id == user_id).first()
