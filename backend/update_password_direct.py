"""
Actualiza la contraseña de Garmin directamente en SQLite
Evita el problema de foreign key
"""
import sqlite3
import os
import getpass
import sys

def update_password_direct():
    db_path = os.path.join(os.path.dirname(__file__), 'atlas_v2.db')
    
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), '..', 'atlas_v2.db')
    
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos en: {db_path}")
        # Buscar en otros lugares comunes
        for alt_path in ['atlas.db', '../atlas.db', './tmp/atlas_v2.db', '/tmp/atlas_v2.db']:
            if os.path.exists(alt_path):
                db_path = alt_path
                print(f"✅ Encontrada en: {db_path}")
                break
        else:
            print("❌ No se encontró ninguna base de datos")
            return False
    
    print(f"📁 Usando base de datos: {db_path}")
    
    # Conectar directamente con SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si existe la tabla tokens
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'")
        if not cursor.fetchone():
            print("❌ La tabla 'tokens' no existe")
            return False
        
        # Ver estructura de la tabla
        cursor.execute("PRAGMA table_info(tokens)")
        columns = cursor.fetchall()
        print(f"\n📋 Columnas en tabla tokens:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Ver registros actuales
        cursor.execute("SELECT user_id, garmin_email FROM tokens WHERE garmin_email IS NOT NULL")
        records = cursor.fetchall()
        
        if not records:
            print("\n❌ No hay registros con garmin_email")
            return False
        
        print(f"\n📧 Registros encontrados: {len(records)}")
        for rec in records:
            print(f"  User ID: {rec[0]}, Email: {rec[1]}")
        
        # Pedir nueva contraseña
        print()
        new_password = getpass.getpass("🔑 Nueva contraseña de Garmin: ")
        
        if not new_password:
            print("❌ Contraseña vacía")
            return False
        
        confirm = getpass.getpass("🔑 Confirma la contraseña: ")
        
        if new_password != confirm:
            print("❌ Las contraseñas no coinciden")
            return False
        
        # Actualizar directamente con SQL
        cursor.execute(
            "UPDATE tokens SET garmin_password = ? WHERE garmin_email IS NOT NULL",
            (new_password,)
        )
        conn.commit()
        
        print(f"\n✅ Contraseña actualizada para {cursor.rowcount} registro(s)")
        
        # Verificar el cambio
        cursor.execute("SELECT garmin_email FROM tokens WHERE garmin_email IS NOT NULL")
        email = cursor.fetchone()
        if email:
            print(f"📧 Email: {email[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 ACTUALIZAR CONTRASEÑA (MODO DIRECTO)")
    print("=" * 60)
    print()
    
    success = update_password_direct()
    
    if success:
        print()
        print("=" * 60)
        print("🎉 CONTRASEÑA ACTUALIZADA")
        print("=" * 60)
        print()
        print("Ahora ejecuta:")
        print("  python generate_garmin_tokens.py")
        print()
    else:
        print()
        print("❌ No se pudo actualizar la contraseña")
        sys.exit(1)
