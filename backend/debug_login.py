#!/usr/bin/env python3
"""Debug del login real de Garmin para ver el error exacto"""

import garth
import traceback
from app.db.session import SessionLocal
from app.models.token import Token

db = SessionLocal()
token = db.query(Token).filter(Token.user_id == 'default_user').first()

if not token or not token.password:
    print("❌ No hay credenciales en la base de datos")
    db.close()
    exit(1)

print(f"Email: {token.email}")
print(f"Password: {'[PRESENTE - ' + str(len(token.password)) + ' chars]'}")
print()

try:
    print("Intentando login...")
    garth.login(token.email, token.password)
    print("✅ Login exitoso!")
    
    # Guardar tokens
    garth.save('.garth')
    print("✅ Tokens guardados en .garth/")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}")
    print(f"Mensaje: {str(e)}")
    print()
    print("Traceback completo:")
    traceback.print_exc()

db.close()
