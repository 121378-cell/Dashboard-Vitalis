import garth
from garminconnect import Garmin
from typing import Any, Optional, Tuple
from sqlalchemy.orm import Session
import os
import logging
import json
import time
import re
from app.utils.garmin_exceptions import (
    GarminRateLimitError,
    GarminSessionError,
    GarminAuthError,
)

logger = logging.getLogger("app.utils.garmin")

# Rate limiting del lado del cliente
MIN_LOGIN_INTERVAL = 300  # 5 minutos entre logins
_last_login_attempt = 0


def _parse_retry_after(error_msg: str) -> int:
    """Extrae tiempo de espera del mensaje de error 429."""
    patterns = [
        r"retry after (\d+) seconds?",
        r"Retry-After[:\s]*(\d+)",
        r"try again in (\d+) seconds?",
        r"wait (\d+) seconds?",
        r"(\d+)\s*seconds?",
    ]
    for pattern in patterns:
        match = re.search(pattern, error_msg, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 1800  # Default: 30 minutos


def _is_rate_limit_error(error_msg: str) -> bool:
    """Detecta error 429 en mensaje de error."""
    return any(x in error_msg for x in ["429", "Too Many Requests", "rate limit", "Rate limit"])


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
    email: str = None,
    password: str = None,
    token_dir: str = None,
    db: Optional[Session] = None,
    user_id: str = "default_user",
) -> Tuple[Optional[Garmin], Any]:
    """
    Returns a Garmin client.
    Priority: DB session -> Disk tokens -> Fresh login (with rate limiting)
    """
    global _last_login_attempt
    
    if token_dir is None:
        token_dir = os.getenv("GARMIN_TOKEN_DIR", ".garth")

    abs_token_dir = os.path.abspath(token_dir)
    logger.info(f"Using Garmin token directory: {abs_token_dir}")

    # Crear directorio con fallback Windows-compatible
    try:
        os.makedirs(token_dir, exist_ok=True)
        test_file = os.path.join(token_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        logger.error(f"Token directory not writable: {e}")
        if os.name == 'nt':
            fallback_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), '.garth')
        else:
            fallback_dir = "/tmp/.garth"
        
        if token_dir != fallback_dir:
            logger.info(f"Falling back to {fallback_dir}")
            token_dir = fallback_dir
            os.makedirs(token_dir, exist_ok=True)

    oauth1_path = os.path.join(token_dir, "oauth1_token.json")
    oauth2_path = os.path.join(token_dir, "oauth2_token.json")

    # 1. Restaurar desde DB si disponible
    if db and user_id:
        from app.models.token import Token
        token_record = db.query(Token).filter(Token.user_id == user_id).first()
        if token_record and token_record.garmin_session and len(token_record.garmin_session) > 50:
            try:
                logger.info("Restoring session from Database...")
                session_data = json.loads(token_record.garmin_session)
                with open(oauth1_path, "w") as f:
                    json.dump(session_data.get("oauth1"), f)
                with open(oauth2_path, "w") as f:
                    json.dump(session_data.get("oauth2"), f)
                logger.info("Tokens restored from DB to disk.")
            except Exception as e:
                logger.warning(f"Failed to restore from DB: {e}")

    # 2. Resumir sesión existente (SIN VERIFICACIÓN HTTP)
    if os.path.exists(oauth1_path) and os.path.exists(oauth2_path):
        try:
            logger.info("Resuming session from disk...")
            garth.resume(token_dir)
            client = Garmin()
            client.garth = garth.client
            
            # Verificación local sin HTTP request
            if garth.client.oauth1_token and garth.client.oauth2_token:
                try:
                    client.display_name = garth.client.profile.get("displayName", "Unknown")
                except:
                    client.display_name = "Unknown"
                
                logger.info(f"Session resumed: {client.display_name}")
                return client, False
            else:
                raise GarminSessionError("Invalid tokens")
                
        except Exception as e:
            error_msg = str(e)
            if _is_rate_limit_error(error_msg):
                retry_after = _parse_retry_after(error_msg)
                raise GarminRateLimitError(f"Rate limit. Wait {retry_after//60} min.")
            
            logger.warning(f"Session invalid: {e}. Clearing tokens.")
            for path in [oauth1_path, oauth2_path]:
                if os.path.exists(path):
                    os.remove(path)

    # 3. Fresh login con rate limiting del lado del cliente
    if email and password:
        time_since_last = time.time() - _last_login_attempt
        if time_since_last < MIN_LOGIN_INTERVAL:
            wait = MIN_LOGIN_INTERVAL - time_since_last
            logger.info(f"Self rate-limit: waiting {wait:.0f}s...")
            time.sleep(wait)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (5 ** attempt)  # 5, 25, 125s
                    logger.info(f"Retry {attempt + 1}/{max_retries}, waiting {wait_time}s...")
                    time.sleep(wait_time)

                logger.info(f"Login attempt {attempt + 1}/{max_retries} for {email}...")
                _last_login_attempt = time.time()
                
                garth.login(email, password)
                garth.save(token_dir)

                client = Garmin()
                client.garth = garth.client
                try:
                    client.display_name = garth.client.profile.get("displayName", "Unknown")
                except:
                    client.display_name = "Unknown"

                logger.info(f"Login successful: {client.display_name}")
                return client, True
                
            except Exception as e:
                error_msg = str(e)
                
                if _is_rate_limit_error(error_msg):
                    retry_after = _parse_retry_after(error_msg)
                    
                    if attempt == max_retries - 1:
                        raise GarminRateLimitError(
                            f"Rate limit persists. Wait {retry_after//60} min."
                        )
                    
                    wait_time = max(5 ** attempt, min(retry_after, 300))
                    logger.warning(f"429 detected. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                raise GarminAuthError(f"Login failed: {e}")

    raise GarminAuthError("No session tokens and no credentials available.")
