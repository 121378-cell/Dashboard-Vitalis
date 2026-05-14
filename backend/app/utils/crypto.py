import os
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# --- Carga robusta de la clave de cifrado ---
# Se lee de la variable de entorno FERNET_KEY o de settings.FERNET_KEY (desde .env).
# Si no existe, el sistema genera una clave temporal para desarrollo (INSEGURA).

try:
    _ENCRYPTION_KEY = os.getenv("FERNET_KEY")
    if not _ENCRYPTION_KEY:
        # Fallback: leer desde pydantic settings (carga .env vía python-dotenv)
        try:
            from app.core.config import settings
            _ENCRYPTION_KEY = settings.FERNET_KEY
        except ImportError:
            pass
        except Exception:
            pass
    
    if not _ENCRYPTION_KEY:
        # Generar una clave temporal para desarrollo
        from cryptography.fernet import Fernet
        _key = Fernet.generate_key()
        logger.warning("FERNET_KEY no establecida. Usando clave temporal (INSEGURA). "
                       "Por favor, establece FERNET_KEY en producción.")
    else:
        _key = _ENCRYPTION_KEY.encode() if isinstance(_ENCRYPTION_KEY, str) else _ENCRYPTION_KEY
    
    # Instanciar el cipher de Fernet
    from cryptography.fernet import Fernet
    _cipher = Fernet(_key)
    
except ImportError:
    logger.error("cryptography no instalado. Instalar: pip install cryptography")
    _cipher = None
except Exception as e:
    logger.error(f"Error inicializando cifrado: {e}")
    _cipher = None

def encrypt_text(plain_text: str) -> Optional[str]:
    """Encripta un string y devuelve el texto encriptado.
       Si el input es None o vacío, devuelve None."""
    if not _cipher:
        raise RuntimeError("Cifrado no inicializado")
    if not plain_text:
        return None
    try:
        return _cipher.encrypt(plain_text.encode()).decode()
    except Exception as e:
        logger.error(f"Error al encriptar: {e}")
        return None

def decrypt_text(encrypted_text: str) -> Optional[str]:
    """Desencripta un string y devuelve el texto plano.
       Si el input es None o vacío, devuelve None."""
    if not _cipher:
        raise RuntimeError("Cifrado no inicializado")
    if not encrypted_text:
        return None
    try:
        return _cipher.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        logger.error(f"Error al desencriptar (posible clave incorrecta): {e}")
        return None

def encrypt_field(value: str) -> Optional[str]:
    """Encripta un campo de la base de datos de forma segura (permite None)."""
    return encrypt_text(value)

def decrypt_field(value: str) -> Optional[str]:
    """Desencripta un campo de la base de datos de forma segura (permite None)."""
    return decrypt_text(value)