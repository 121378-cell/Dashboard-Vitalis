from typing import Generator, Optional
from fastapi import Header, HTTPException
from app.db.session import SessionLocal

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="x-user-id")) -> str:
    """Extract user ID from header or use default for testing."""
    if x_user_id:
        return x_user_id
    return "default_user"  # Fallback para desarrollo

def get_current_user_id_from_token(token: Optional[str] = None) -> str:
    """Extract user ID from JWT token (simplified for now)."""
    # TODO: Implementar decodificación JWT real
    return "default_user"
