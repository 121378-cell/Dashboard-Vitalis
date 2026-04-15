"""
Configura las credenciales de Garmin en la base de datos
"""
import sqlite3
import os
import getpass
import sys

def setup_credentials():
    db_path = os.path.join(os.path.dirname(__file__), 'atlas_v2.db')
    
    print("=" * 60)
    print("🔐 CONFIGURAR CREDENCIALES DE GARMIN")
    print("=" * 60)
    print()
    print("⚠️  No se encontraron credenciales de Garmin en la base de datos.")
    print()
    
    # Pedir datos
    email = input("📧 Email de Garmin: ").strip()
    
    if not email:
        print("❌ Email vacío. Abortando.")
        return False
    
    password = getpass.getpass("🔑 Contraseña de Garmin: ")
    
    if not password:
        print("❌ Contraseña vacía. Abortando.")
        return False
    
    confirm = getpass.getpass("🔑 Confirma la contraseña: ")
    
    if password != confirm:
        print("❌ Las contraseñas no coinciden. Abortando.")
        return False
    
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si existe el registro
        cursor.execute("SELECT user_id FROM tokens WHERE user_id = 'default_user'")
        if cursor.fetchone():
            # Actualizar registro existente
            cursor.execute(
                "UPDATE tokens SET garmin_email = ?, garmin_password = ? WHERE user_id = 'default_user'",
                (email, password)
            )
            print("\n✅ Registro actualizado con credenciales de Garmin")
        else:
            # Crear nuevo registro
            cursor.execute(
                "INSERT INTO tokens (user_id, garmin_email, garmin_password) VALUES (?, ?, ?)",
                ('default_user', email, password)
            )
            print("\n✅ Nuevo registro creado con credenciales de Garmin")
        
        conn.commit()
        
        # Verificar
        cursor.execute("SELECT garmin_email FROM tokens WHERE user_id = 'default_user'")
        result = cursor.fetchone()
        if result and result[0]:
            print(f"\n📧 Guardado: {result[0]}")
            return True
        else:
            print("\n❌ Error al guardar")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = setup_credentials()
    
    if success:
        print()
        print("=" * 60)
        print("🎉 CREDENCIALES GUARDADAS")
        print("=" * 60)
        print()
        print("Ahora ejecuta:")
        print("  python generate_garmin_tokens.py")
        print()
    else:
        sys.exit(1)
