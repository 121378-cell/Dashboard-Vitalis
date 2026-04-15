#!/usr/bin/env python3
"""Test de validación del mapeo Token"""

from app.db.session import SessionLocal
from app.models.token import Token

db = SessionLocal()

# Test 1: Leer registro existente
token = db.query(Token).filter(Token.user_id == 'default_user').first()

if token:
    print(f"✅ Registro encontrado")
    print(f"   user_id: {token.user_id}")
    print(f"   email: {token.email}")
    print(f"   password: {'[PRESENTE]' if token.password else '[VACÍO]'}")
    print(f"   garmin_email (property): {token.garmin_email}")
    print(f"   garmin_password (property): {'[PRESENTE]' if token.garmin_password else '[VACÍO]'}")
    
    # Test 2: Verificar que garmin_email mapea a email
    assert token.garmin_email == token.email, "Property garmin_email no funciona"
    assert token.garmin_password == token.password, "Property garmin_password no funciona"
    print("\n✅ Todas las validaciones pasaron")
else:
    print("❌ No se encontró registro default_user")

db.close()
