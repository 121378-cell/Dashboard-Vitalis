"""
Crear usuario default_user con información de Sergi
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
    # Verificar si el usuario ya existe
    existing_user = db.query(User).filter(User.id == 'default_user').first()
    
    if existing_user:
        print('Usuario default_user ya existe')
        print(f'Nombre: {existing_user.name}')
        print(f'Fecha de nacimiento: {existing_user.birth_date}')
        print(f'Edad: {existing_user.age} años')
    else:
        # Crear nuevo usuario
        new_user = User(
            id='default_user',
            name='Sergi',
            email='sergi.marquez.brugal@gmail.com',
            birth_date=date(1978, 5, 30)
        )
        
        db.add(new_user)
        db.commit()
        
        print('✅ Usuario default_user creado exitosamente')
        print(f'   Nombre: {new_user.name}')
        print(f'   Email: {new_user.email}')
        print(f'   Fecha de nacimiento: {new_user.birth_date}')
        print(f'   Edad: {new_user.age} años')
        
finally:
    db.close()
