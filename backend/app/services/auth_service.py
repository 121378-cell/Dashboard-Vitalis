from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days
REFRESH_TOKEN_EXPIRE_MINUTES = 90 * 24 * 60  # 90 days

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def _create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None
    
    def register(self, email: str, password: str, name: str) -> Dict[str, Any]:
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        hashed_password = self._hash_password(password)
        user = User(
            id=email,  # Using email as ID for simplicity
            name=name,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            is_pro=False
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
        
        access_token = self._create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        refresh_token = self._create_refresh_token(
            data={"sub": user.id}, expires_delta=refresh_token_expires
        )
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active,
                "is_pro": user.is_pro,
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not self._verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        
        if not user.is_active:
            raise ValueError("User account is inactive")
        
        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
        
        access_token = self._create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        refresh_token = self._create_refresh_token(
            data={"sub": user.id}, expires_delta=refresh_token_expires
        )
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active,
                "is_pro": user.is_pro,
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        user_id = self.verify_token(refresh_token)
        if not user_id:
            raise ValueError("Invalid refresh token")
        
        # Check if it's actually a refresh token
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "refresh":
                raise ValueError("Invalid refresh token")
        except JWTError:
            raise ValueError("Invalid refresh token")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self._create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }