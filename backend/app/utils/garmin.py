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


def _try_garminconnect_native(token_dir: str) -> Optional[Garmin]:
    """Intenta cargar garmin_tokens.json nativo y hacer DI refresh si hace falta."""
    gc_path = os.path.join(token_dir, "garmin_tokens.json")
    if not os.path.exists(gc_path):
        return None

    try:
        client = Garmin()
        client.login(tokenstore=gc_path)
        logger.info(f"Native garminconnect session loaded: {client.display_name}")
        return client
    except Exception as e:
        logger.debug(f"Native garminconnect load failed: {e}")
        return None


def _try_garth_bridge(token_dir: str) -> Optional[Garmin]:
    """Intenta cargar tokens garth e inyectarlos directamente en el Client DI de garminconnect."""
    oauth1_path = os.path.join(token_dir, "oauth1_token.json")
    oauth2_path = os.path.join(token_dir, "oauth2_token.json")

    if not (os.path.exists(oauth1_path) and os.path.exists(oauth2_path)):
        return None

    try:
        with open(oauth2_path) as f:
            garth_data = json.load(f)

        access_token = garth_data.get("access_token", "")
        refresh_token_val = garth_data.get("refresh_token", "")

        if not access_token or not refresh_token_val:
            return None

        import base64

        parts = access_token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1] + "===="
        if len(parts[1]) % 4:
            payload += "=" * (4 - len(parts[1]) % 4)
        jwt_data = json.loads(base64.b64decode(payload, validate=False))
        client_id = jwt_data.get("client_id")
        if not client_id:
            return None

        logger.info("Resuming session via garth bridge (DI injection)...")
        garth.resume(token_dir)
        client = Garmin()
        client.client.di_token = access_token
        client.client.di_refresh_token = refresh_token_val
        client.client.di_client_id = client_id
        client.display_name = garth.client.profile.get("displayName", "Unknown")
        logger.info(f"Garth bridge session: {client.display_name}")
        return client
    except Exception as e:
        error_msg = str(e)
        if _is_rate_limit_error(error_msg):
            retry_after = _parse_retry_after(error_msg)
            raise GarminRateLimitError(f"Rate limit. Wait {retry_after//60} min.")

        logger.warning(f"Garth bridge invalid: {e}. Clearing tokens.")
        for path in [oauth1_path, oauth2_path]:
            if os.path.exists(path):
                os.remove(path)
        return None


def _ensure_garmin_tokens_json(token_dir: str):
    """Convierte garth tokens a garmin_tokens.json si este no existe."""
    gc_path = os.path.join(token_dir, "garmin_tokens.json")
    oauth2_path = os.path.join(token_dir, "oauth2_token.json")

    if os.path.exists(gc_path) or not os.path.exists(oauth2_path):
        return

    try:
        with open(oauth2_path) as f:
            garth_data = json.load(f)

        access_token = garth_data.get("access_token", "")
        refresh_token = garth_data.get("refresh_token", "")

        if not access_token or not refresh_token:
            return

        import base64
        parts = access_token.split(".")
        if len(parts) != 3:
            return

        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        jwt_data = json.loads(base64.b64decode(payload, validate=False))
        client_id = jwt_data.get("client_id")
        if not client_id:
            return

        gc_data = {
            "di_token": access_token,
            "di_refresh_token": refresh_token,
            "di_client_id": client_id,
        }
        with open(gc_path, "w") as f:
            json.dump(gc_data, f, indent=2)

        logger.info(f"Converted garth tokens -> garmin_tokens.json (client_id={client_id})")
    except Exception as e:
        logger.warning(f"Auto-convert garth->garminconnect failed: {e}")


def get_garmin_client(
    email: str = None,
    password: str = None,
    token_dir: str = None,
    db: Optional[Session] = None,
    user_id: str = "default_user",
) -> Tuple[Optional[Garmin], Any]:
    """
    Returns a Garmin client.
    Priority: DB session -> Native garminconnect tokens (DI) -> Garth bridge -> Fresh login
    """
    global _last_login_attempt

    if token_dir is None:
        token_dir = os.getenv("GARMIN_TOKEN_DIR", ".garth")

    abs_token_dir = os.path.abspath(token_dir)
    logger.info(f"Using Garmin token directory: {abs_token_dir}")

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

    _ensure_garmin_tokens_json(token_dir)

    # 1. Native garminconnect DI tokens (evita garth/login, usa refresh_token directo)
    client = _try_garminconnect_native(token_dir)
    if client:
        return client, False

    # 2. Garth bridge (solo si native DI falló)
    try:
        client = _try_garth_bridge(token_dir)
        if client:
            return client, False
    except GarminRateLimitError:
        raise

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
                    wait_time = (5 ** attempt)
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
                except Exception:
                    client.display_name = "Unknown"

                logger.info(f"Login successful: {client.display_name}")

                _ensure_garmin_tokens_json(token_dir)

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
