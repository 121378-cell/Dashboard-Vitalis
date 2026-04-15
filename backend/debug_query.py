#!/usr/bin/env python3
"""Debug de la consulta SQLAlchemy"""

from app.db.session import SessionLocal
from app.models.token import Token
from app.core.config import settings

print(f"DATABASE_URL en config: {settings.DATABASE_URL}")
print()

db = SessionLocal()

# Consulta exacta que hace generate_garmin_tokens.py
print("Consulta: db.query(Token).filter(Token.email != None).first()")
token_record = db.query(Token).filter(Token.email != None).first()

print(f"Resultado: {token_record}")

if token_record:
    print(f"  user_id: {token_record.user_id}")
    print(f"  email: {token_record.email}")
    print(f"  password: {'[PRESENTE]' if token_record.password else '[VACIO]'}")
else:
    print("  No se encontró registro")
    
    # Intentar sin filtro
    print("\nIntentando sin filtro:")
    all_tokens = db.query(Token).all()
    print(f"  Total tokens en BD: {len(all_tokens)}")
    for t in all_tokens:
        print(f"    user_id={t.user_id}, email={t.email}, pass={'[OK]' if t.password else '[NO]'}")

db.close()
