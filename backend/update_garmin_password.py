"""
Actualiza la contraseña de Garmin en la base de datos local
y genera nuevos tokens evitando el rate limit 429
"""
import os
import sys
import time
import getpass

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.token import Token

def update_password():
    print("=" * 60)
    print("🔐 ACTUALIZAR CONTRASEÑA DE GARMIN")
    print("=" * 60)
    print()
    print("⚠️  INSTRUCCIONES PREVIAS:")
    print("1. Ve a https://connect.garmin.com")
    print("2. Click en tu perfil (arriba derecha)")
    print("3. Account Settings → Security")
    print("4. Change Password")
    print("5. Guarda la nueva contraseña")
    print()
    input("Presiona ENTER cuando hayas cambiado la contraseña...")
    print()
    
    # Conectar a la base de datos
    db = SessionLocal()
    
    try:
        # Buscar registro de token
        token_record = db.query(Token).filter(Token.garmin_email != None).first()
        
        if not token_record:
            print("❌ No se encontró registro de Garmin en la base de datos")
            return False
        
        print(f"📧 Email: {token_record.garmin_email}")
        print()
        
        # Pedir nueva contraseña (oculta)
        new_password = getpass.getpass("🔑 Nueva contraseña de Garmin: ")
        
        if not new_password:
            print("❌ Contraseña vacía. Abortando.")
            return False
        
        confirm = getpass.getpass("🔑 Confirma la contraseña: ")
        
        if new_password != confirm:
            print("❌ Las contraseñas no coinciden. Abortando.")
            return False
        
        # Actualizar en la base de datos
        token_record.garmin_password = new_password
        db.commit()
        
        print()
        print("✅ Contraseña actualizada en la base de datos")
        print()
        
        # Limpiar tokens antiguos si existen
        token_dir = ".garth"
        oauth1_path = os.path.join(token_dir, "oauth1_token.json")
        oauth2_path = os.path.join(token_dir, "oauth2_token.json")
        
        if os.path.exists(oauth1_path):
            os.remove(oauth1_path)
            print("🗑️  Token antiguo (oauth1) eliminado")
        
        if os.path.exists(oauth2_path):
            os.remove(oauth2_path)
            print("🗑️  Token antiguo (oauth2) eliminado")
        
        print()
        print("=" * 60)
        print("🎉 LISTO PARA GENERAR NUEVOS TOKENS")
        print("=" * 60)
        print()
        print("Ahora ejecuta:")
        print("  python generate_garmin_tokens.py")
        print()
        print("Con la contraseña nueva, el rate limit debería estar reseteado.")
        print()
        
        # Preguntar si quiere ejecutar ahora
        response = input("¿Quieres ejecutar generate_garmin_tokens.py ahora? (s/n): ")
        
        if response.lower() in ['s', 'si', 'sí', 'y', 'yes']:
            print()
            print("🚀 Ejecutando generate_garmin_tokens.py...")
            print()
            time.sleep(1)
            
            # Ejecutar el script
            import subprocess
            result = subprocess.run(
                [sys.executable, "generate_garmin_tokens.py"],
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            return result.returncode == 0
        else:
            print()
            print("👌 Ejecuta manualmente cuando estés listo:")
            print("  python generate_garmin_tokens.py")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = update_password()
    sys.exit(0 if success else 1)
