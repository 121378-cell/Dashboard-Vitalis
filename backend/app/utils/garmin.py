import os
import garth
from garminconnect import Garmin
from typing import Any, Optional, Tuple
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
    email: str, password: str, token_dir: str = ".garth"
) -> Tuple[Optional[Garmin], bool]:
    """Authenticates or resumes a Garth session and returns a Garmin client."""
    session_updated = False

    try:
        # Create token directory if it doesn't exist
        if not os.path.exists(token_dir):
            os.makedirs(token_dir)

        # Try to resume first
        try:
            garth.resume(token_dir)
            client = Garmin(email=email, password=password)
            client.login()  # This should use the resumed session
            logger.info("Resumed Garmin session successfully")
        except Exception as e:
            logger.info(f"Could not resume session, logging in... Error: {e}")
            client = Garmin(email=email, password=password)
            client.login()
            garth.save(token_dir)
            session_updated = True
            logger.info("Login successful, session saved")

        # Ensure display_name is set
        try:
            if hasattr(client, "garth") and hasattr(client.garth, "profile"):
                client.display_name = client.garth.profile.get(
                    "displayName", "Unknown User"
                )
            else:
                try:
                    profile = client.get_user_profile()
                    client.display_name = profile.get("displayName", "Unknown User")
                except Exception as e:
                    logger.warning(f"Could not fetch user profile: {e}")
                    client.display_name = "Unknown User"
        except Exception as e:
            logger.warning(f"Could not set display name: {e}")
            client.display_name = "Unknown User"

        return client, session_updated
    except Exception as e:
        logger.error(f"Error connecting to Garmin: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None, False
