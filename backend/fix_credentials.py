#!/usr/bin/env python3
"""Corrige credenciales usando SQLAlchemy (mismo método que la app)"""

import getpass
from app.db.session import SessionLocal
from app.models.token import Token
from datetime import datetime

print("=" * 60)
print("🔧 CORRECCIÓN DE CREDENCIALES GARMIN")
print("=" * 60)
print()

db = SessionLocal()

# Buscar registro existente
token = db.query(Token).filter(Token.user_id == 'default_user').first()

if token:
    print(f"Registro encontrado:")
    print(f"  Email actual: {token.email}")
    print(f"  Password: {'[PRESENTE]' if token.password else '[VACÍO]'}")
else:
    print("No existe registro. Creando nuevo...")
    token = Token(user_id='default_user')
    db.add(token)

print()
email = input("📧 Email de Garmin: ").strip()
password = getpass.getpass("🔑 Contraseña de Garmin: ")

# Actualizar valores
token.email = email
token.password = password
token.updated_at = datetime.now()

db.commit()
db.close()

print()
print("=" * 60)
print("✅ CREDENCIALES ACTUALIZADAS")
print("=" * 60)
print()
print("Verifica con: python test_mapping.py")
