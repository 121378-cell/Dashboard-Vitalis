import garth
from garminconnect import Garmin
from typing import Any, Optional, Tuple
import os
import logging

logger = logging.getLogger("app.utils.garmin")


def safe_get(data: Any, *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dictionaries or lists."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            try:
                data = data[key]
            except IndexError:
                return default
        else:
            return default
    return data if data is not None else default


def get_garmin_client(
    email: str = None, password: str = None, token_dir: str = None
) -> Tuple[Optional[Garmin], bool]:
    """
    Returns a Garmin client. 
    1. Tries to resume from existing tokens.
    2. If tokens are missing and credentials are provided, attempts fresh login.
    """
    if token_dir is None:
        # Usar /data/.garth en Fly.io por defecto para persistencia
        token_dir = os.getenv("GARMIN_TOKEN_DIR", ".garth")

    abs_token_dir = os.path.abspath(token_dir)
    logger.info(f"Checking Garmin tokens in: {abs_token_dir}")

    # Asegurar que el directorio existe
    os.makedirs(token_dir, exist_ok=True)

    oauth1_path = os.path.join(token_dir, "oauth1_token.json")
    oauth2_path = os.path.join(token_dir, "oauth2_token.json")
    
    logger.info(f"OAuth1 file exists: {os.path.exists(oauth1_path)}")
    logger.info(f"OAuth2 file exists: {os.path.exists(oauth2_path)}")

    # Intento de RESUMIR sesión existente
    if os.path.exists(oauth1_path) and os.path.exists(oauth2_path):
        try:
            logger.info("Attempting to resume Garmin session...")
            garth.resume(token_dir)
            client = Garmin()
            client.garth = garth.client

            # Verificar si la sesión sigue siendo válida intentando una operación ligera
            try:
                profile = client.get_user_profile()
                client.display_name = profile.get("displayName", "Unknown")
                logger.info("Garmin session resumed successfully from tokens")
                return client, False
            except Exception as e:
                logger.warning(f"Saved tokens expired or invalid: {e}. Attempting re-login...")
                # Limpiar tokens corruptos/inválidos antes de re-login
                try:
                    os.remove(oauth1_path)
                    os.remove(oauth2_path)
                    logger.info("Removed invalid token files")
                except Exception as remove_err:
                    logger.warning(f"Could not remove invalid tokens: {remove_err}")
                # Si tenemos credenciales, intentar login fresco
                if not (email and password):
                    logger.error("Session expired and no credentials provided for re-login")
                    return None, False
        except Exception as e:
            logger.error(f"Error resuming Garmin session: {e}")
            # Limpiar tokens corruptos antes de reintentar
            try:
                if os.path.exists(oauth1_path):
                    os.remove(oauth1_path)
                if os.path.exists(oauth2_path):
                    os.remove(oauth2_path)
                logger.info("Removed corrupt token files after resume failure")
            except Exception as remove_err:
                logger.warning(f"Could not remove corrupt tokens: {remove_err}")

    # Intento de LOGIN fresco si tenemos credenciales
    if email and password:
        try:
            logger.info(f"Attempting fresh Garmin login for {email}...")
            garth.login(email, password)
            garth.save(token_dir)

            client = Garmin()
            client.garth = garth.client
            try:
                client.display_name = garth.client.profile.get("displayName", "Unknown")
            except Exception:
                client.display_name = "Unknown"

            logger.info(f"Garmin login successful. Tokens saved to {token_dir}")
            return client, True
        except Exception as e:
            error_msg = str(e)
            # Detectar rate limit (429) de Garmin
            if "429" in error_msg or "Too Many Requests" in error_msg:
                logger.error("Garmin rate limit (429) hit. User needs to wait ~30-60 minutes before retrying.")
                return None, "rate_limited"  # Return special indicator for rate limit
            logger.error(f"Fresh Garmin login failed: {e}")
            return None, False

    logger.error("No valid Garmin session tokens found and no credentials provided.")
    return None, False
