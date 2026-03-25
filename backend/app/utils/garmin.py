import os
import garth
from garminconnect import Garmin
from typing import Any, Optional
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

def get_garmin_client(email: str, password: str, token_dir: str = ".garth") -> Optional[Garmin]:
    """Authenticates or resumes a Garth session and returns a Garmin client."""
    try:
        # Create token directory if it doesn't exist
        if not os.path.exists(token_dir):
            os.makedirs(token_dir)

        # Try to resume first
        try:
            garth.resume(token_dir)
            client = Garmin(email, password)
            client.login() # This should use the resumed session
            logger.info("Resumed Garmin session successfully")
        except Exception:
            logger.info("Could not resume session, logging in...")
            client = Garmin(email, password)
            client.login()
            client.garth.save(token_dir)
            logger.info("Login successful, session saved")
        
        # Ensure display_name is set
        try:
            client.display_name = client.garth.profile["displayName"]
        except (AttributeError, KeyError):
            profile = client.get_user_profile()
            client.display_name = profile["displayName"]
            
        return client
    except Exception as e:
        logger.error(f"Error connecting to Garmin: {e}")
        return None

import os # Needed for os.path.exists
