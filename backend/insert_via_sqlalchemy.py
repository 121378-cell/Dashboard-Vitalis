#!/usr/bin/env python3
"""Inserta credenciales usando SQLAlchemy (mismo método que la app)"""

import getpass
import sys
sys.path.insert(0, '..')

from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Usar la misma ruta que el config ahora
DATABASE_URL = "sqlite:///c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas.db"

Base = declarative_base()

class Token(Base):
    __tablename__ = "tokens"
    
    user_id = Column(String, primary_key=True)
    email = Column(String)
    password = Column(String)
    garmin_session = Column(String)
    garmin_rate_limited_until = Column(DateTime, nullable=True)
    last_login_attempt = Column(DateTime, nullable=True)
    login_attempts_count = Column(Integer, default=0)
    wger_api_key = Column(String)
    hevy_username = Column(String)
    updated_at = Column(DateTime)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

print("=" * 60)
print("🔧 INSERCIÓN VIA SQLALCHEMY")
print(f"DB: {DATABASE_URL}")
print("=" * 60)

email = input("\n📧 Email: ").strip()
password = getpass.getpass("🔑 Contraseña: ")

db = SessionLocal()

# Buscar o crear
token = db.query(Token).filter(Token.user_id == 'default_user').first()
if not token:
    token = Token(user_id='default_user')
    db.add(token)

token.email = email
token.password = password
token.updated_at = datetime.now()

db.commit()

# Verificar
token_check = db.query(Token).filter(Token.user_id == 'default_user').first()
print(f"\n✅ Guardado: user_id={token_check.user_id}, email={token_check.email}")

db.close()
print("\nAhora prueba: python generate_garmin_tokens.py")
