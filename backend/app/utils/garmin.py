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
    Returns a Garmin client using saved tokens (no login required).
    email and password are accepted for compatibility but not used.
    NEVER attempts login with credentials - only token-based auth.
    """
    if token_dir is None:
        token_dir = ".garth"

    # Check if tokens exist before attempting anything
    oauth1_path = os.path.join(token_dir, "oauth1_token.json")
    oauth2_path = os.path.join(token_dir, "oauth2_token.json")
    
    if not os.path.exists(oauth1_path) or not os.path.exists(oauth2_path):
        logger.error(
            f"Garmin tokens not found in '{token_dir}'. "
            "Required: oauth1_token.json and oauth2_token.json"
        )
        return None, False

    try:
        garth.resume(token_dir)
        client = Garmin("dummy", "dummy")
        client.garth = garth.client

        # Set display_name required by some endpoints
        try:
            client.display_name = garth.client.profile["displayName"]
        except (AttributeError, KeyError):
            try:
                profile = client.get_user_profile()
                client.display_name = profile.get("displayName", "Unknown")
            except Exception:
                client.display_name = "Unknown"

        logger.info("Garmin session resumed successfully from tokens")
        return client, False

    except Exception as e:
        logger.error(f"Error resuming Garmin session: {e}")
        return None, False
