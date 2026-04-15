#!/usr/bin/env python3
"""
Script para insertar credenciales de Garmin de forma segura en la base de datos.
Usa getpass para ocultar la contraseña durante la entrada.
"""

import sqlite3
import getpass
import re
import os
from datetime import datetime


def mask_email(email: str) -> str:
    """Máscara parcial del email: s***@gmail.com"""
    if not email or '@' not in email:
        return "***"
    
    parts = email.split('@')
    local = parts[0]
    domain = parts[1]
    
    if len(local) <= 1:
        masked_local = "*"
    elif len(local) <= 3:
        masked_local = local[0] + "*" * (len(local) - 1)
    else:
        masked_local = local[0] + "***" + local[-1]
    
    return f"{masked_local}@{domain}"


def validate_email(email: str) -> bool:
    """Valida que el email contenga @"""
    return bool(email and '@' in email and '.' in email.split('@')[-1])


def main():
    print("=" * 60)
    print("🔐 INSERCIÓN SEGURA DE CREDENCIALES GARMIN")
    print("=" * 60)
    print()
    
    # Ruta a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), '..', 'atlas.db')
    db_path = os.path.abspath(db_path)
    
    # Verificar que existe la base de datos
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró la base de datos en:")
        print(f"   {db_path}")
        print()
        print("¿Estás en el directorio correcto? (backend/)")
        return 1
    
    print(f"✅ Base de datos encontrada: {db_path}")
    print()
    
    # Solicitar email
    while True:
        email = input("📧 Email de Garmin: ").strip()
        
        if not email:
            print("❌ El email no puede estar vacío")
            continue
        
        if not validate_email(email):
            print("❌ Email inválido. Debe contener @ y dominio válido")
            continue
        
        break
    
    # Solicitar contraseña (oculta)
    password = getpass.getpass("🔑 Contraseña de Garmin: ")
    
    if not password:
        print("❌ La contraseña no puede estar vacía")
        return 1
    
    confirm_password = getpass.getpass("🔑 Confirma la contraseña: ")
    
    if password != confirm_password:
        print("❌ Las contraseñas no coinciden")
        return 1
    
    print()
    print("💾 Guardando credenciales en la base de datos...")
    print()
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        user_id = 'default_user'
        now = datetime.now().isoformat()
        
        # UPSERT: Insertar o actualizar
        cursor.execute("""
            INSERT INTO tokens (
                user_id, email, password, garmin_session,
                garmin_rate_limited_until, last_login_attempt, login_attempts_count,
                wger_api_key, hevy_username, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email = excluded.email,
                password = excluded.password,
                updated_at = excluded.updated_at
        """, (
            user_id, email, password, None,
            None, None, 0,
            None, None, now
        ))
        
        conn.commit()
        
        # Verificación post-inserción
        cursor.execute(
            "SELECT user_id, email FROM tokens WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if row:
            print("=" * 60)
            print("✅ CREDENCIALES GUARDADAS EXITOSAMENTE")
            print("=" * 60)
            print()
            print(f"👤 User ID:     {row[0]}")
            print(f"📧 Email:       {mask_email(row[1])}")
            print()
            print("🔒 La contraseña está almacenada de forma segura")
            print()
            print("Próximos pasos:")
            print("  1. python generate_garmin_tokens.py")
            print("  2. Iniciar sincronización desde el dashboard")
        else:
            print("❌ Error: No se pudo verificar la inserción")
            return 1
        
        conn.close()
        return 0
        
    except sqlite3.Error as e:
        print(f"❌ Error de base de datos: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
