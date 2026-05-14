"""
ATLAS - Migración: Cifrar credenciales Garmin existentes con Fernet
====================================================================

Convierte los valores de garmin_email y garmin_password almacenados
en texto plano a valores cifrados con Fernet.

Usa SQL directo para BYPASEAR el TypeDecorator de SQLAlchemy,
ya que los valores existentes están en texto plano y el decorador
intentaría descifrarlos como Fernet (fallando).

Uso:
    cd backend/
    python migrate_encrypt_garmin_email.py
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migrate_encrypt")

# Asegurar ruta al backend
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.db.session import SessionLocal
from app.utils.crypto import encrypt_text
from sqlalchemy import text


def migrate_garmin_credentials():
    """
    Migrate existing plaintext garmin_email and garmin_password to encrypted storage.
    Uses raw SQL to bypass the EncryptedString TypeDecorator.
    """
    db = SessionLocal()
    try:
        # 1. Leer valores PLANOS directamente de la BD (sin TypeDecorator)
        result = db.execute(text("SELECT user_id, garmin_email, garmin_password FROM tokens"))
        rows = result.fetchall()

        migrated = 0
        skipped = 0
        errors = 0

        for row in rows:
            user_id, email, password = row
            if not email and not password:
                skipped += 1
                continue

            needs_update = False
            encrypted_email = email
            encrypted_password = password

            # Migrar email si está en texto plano
            if email and not email.startswith("gAAAAA"):
                try:
                    encrypted = encrypt_text(email)
                    if encrypted:
                        encrypted_email = encrypted
                        needs_update = True
                    else:
                        logger.error(f"  No se pudo cifrar email para {user_id}")
                        errors += 1
                        continue
                except Exception as e:
                    logger.error(f"  Error cifrando email para {user_id}: {e}")
                    errors += 1
                    continue

            # Migrar password si está en texto plano
            if password and not password.startswith("gAAAAA"):
                try:
                    encrypted = encrypt_text(password)
                    if encrypted:
                        encrypted_password = encrypted
                        needs_update = True
                    else:
                        logger.error(f"  No se pudo cifrar password para {user_id}")
                        errors += 1
                        continue
                except Exception as e:
                    logger.error(f"  Error cifrando password para {user_id}: {e}")
                    errors += 1
                    continue

            if needs_update:
                # Escribir valores cifrados directamente (SQL directo, sin TypeDecorator)
                db.execute(
                    text("UPDATE tokens SET garmin_email = :email, garmin_password = :password WHERE user_id = :uid"),
                    {"email": encrypted_email, "password": encrypted_password, "uid": user_id}
                )
                db.flush()
                migrated += 1
                logger.info(f"  Token {user_id}: credenciales cifradas correctamente")
            else:
                skipped += 1
                if email and not password:
                    logger.info(f"  Token {user_id}: email ya cifrado, password vacía")
                elif password and not email:
                    logger.info(f"  Token {user_id}: password ya cifrada, email vacío")
                else:
                    logger.info(f"  Token {user_id}: ambas credenciales ya cifradas")

        db.commit()

        # 2. Verificar que se puede leer descifrado
        logger.info("\nVerificando descifrado...")
        verify = db.execute(text("SELECT user_id, garmin_email, garmin_password FROM tokens"))
        for row in verify.fetchall():
            user_id, enc_email, enc_pass = row
            if enc_email and enc_email.startswith("gAAAAA"):
                from app.utils.crypto import decrypt_text
                decrypted = decrypt_text(enc_email)
                if decrypted:
                    logger.info(f"  ✅ Token {user_id}: email descifrado OK")
                else:
                    logger.warning(f"  ⚠️ Token {user_id}: email cifrado pero no se puede descifrar")
            if enc_pass and enc_pass.startswith("gAAAAA"):
                from app.utils.crypto import decrypt_text
                decrypted = decrypt_text(enc_pass)
                if decrypted:
                    logger.info(f"  ✅ Token {user_id}: password descifrada OK")
                else:
                    logger.warning(f"  ⚠️ Token {user_id}: password cifrada pero no se puede descifrar")

        logger.info(f"\nResumen: {migrated} migrados, {skipped} saltados, {errors} errores")
        return errors == 0

    except Exception as e:
        logger.error(f"Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  Migración: Cifrado Fernet de garmin_email")
    print("=" * 60)
    print()

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        print("ERROR: cryptography no instalado. Ejecuta: pip install cryptography")
        sys.exit(1)

    ferret_key = os.getenv("FERNET_KEY")
    if not ferret_key:
        print("AVISO: FERNET_KEY no configurada. Se usará clave temporal (INSEGURA).")
        print("  Para producción, configura FERNET_KEY en backend/.env")
        print()

    success = migrate_garmin_credentials()
    print()
    if success:
        print("✅ Migración completada")
    else:
        print("❌ Migración falló - revisa los errores arriba")
        sys.exit(1)
