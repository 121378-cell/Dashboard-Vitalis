"""
Verificar y actualizar información del usuario
"""
import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import SessionLocal
from app.models.user import User
from datetime import date

db = SessionLocal()
try:
    user = db.query(User).filter(User.id == 'default_user').first()
    
    if user:
        print(f'Usuario encontrado: {user.id}')
        print(f'Nombre actual: {user.name}')
        print(f'Email: {user.email}')
        print(f'Fecha de nacimiento actual: {user.birth_date}')
        
        # Actualizar información
        user.name = "Sergi"
        user.birth_date = date(1978, 5, 30)
        
        db.commit()
        
        print(f'\n✅ Información actualizada:')
        print(f'   Nombre: {user.name}')
        print(f'   Fecha de nacimiento: {user.birth_date}')
        print(f'   Edad: {user.age} años')
    else:
        print('❌ Usuario no encontrado')
finally:
    db.close()
