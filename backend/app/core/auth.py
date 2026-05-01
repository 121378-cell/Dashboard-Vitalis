from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_active_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Returns the current authenticated user.
    For now, returns a default user for development.
    Replace with real JWT validation in production.
    """
    return db.query(User).filter(User.id == "default_user").first()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional auth — returns None if no token provided."""
    if not credentials:
        return None
    return db.query(User).filter(User.id == "default_user").first()