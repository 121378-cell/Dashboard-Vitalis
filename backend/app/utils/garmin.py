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
    email: str, password: str, token_dir: str = None, session_data: str = None
) -> Tuple[Optional[Garmin], bool]:
    """Authenticates or resumes a Garth session and returns a Garmin client."""
    session_updated = False
    if token_dir is None:
        token_dir = ".garth"
    try:
        # Create token directory if it doesn't exist
        if not os.path.exists(token_dir):
            os.makedirs(token_dir)

        # Try to resume from session_data first if provided
        if session_data:
            try:
                import json
                # Garth can resume from a directory, but let's see if we can load from memory
                # If session_data is a JSON string of tokens, we could write them to token_dir
                tokens = json.loads(session_data)
                for filename, content in tokens.items():
                    with open(os.path.join(token_dir, filename), "w") as f:
                        f.write(json.dumps(content))
                logger.info("Restored Garmin session from database tokens")
            except Exception as e:
                logger.warning(f"Could not restore session from data: {e}")

        # Check if tokens exist before attempting to resume
        oauth1_path = os.path.join(token_dir, "oauth1_token.json")
        oauth2_path = os.path.join(token_dir, "oauth2_token.json")
        tokens_exist = os.path.exists(oauth1_path) and os.path.exists(oauth2_path)

        if tokens_exist:
            try:
                garth.resume(token_dir)
                client = Garmin(email=email, password=password)
                client.garth = garth.client
                logger.info("Resumed Garmin session from tokens successfully")
            except Exception as e:
                logger.warning(f"Could not resume token session: {e}")
                # If resume fails, we might need a fresh login, but be careful with 429
                return None, False
        else:
            try:
                client = Garmin(email=email, password=password)
                client.login()
                garth.save(token_dir)
                session_updated = True
                logger.info("Fresh login successful, session saved")
            except Exception as e:
                logger.error(f"Login failed: {e}")
                if "429" in str(e):
                    logger.error("429 Too Many Requests — wait before retrying")
                return None, False

        # If login or resume successful, prepare session string for DB
        if session_updated:
            try:
                import json
                session_dict = {}
                for filename in ["oauth1_token.json", "oauth2_token.json"]:
                    with open(os.path.join(token_dir, filename), "r") as f:
                        session_dict[filename] = json.load(f)
                session_updated = json.dumps(session_dict)
            except Exception as e:
                logger.warning(f"Could not prepare session string: {e}")
                session_updated = True # Still True to indicate it worked, but maybe no DB update

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
