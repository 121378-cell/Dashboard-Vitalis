import os
import garth
from garminconnect import Garmin
from typing import Any, Optional, Tuple, Union
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
    email: str, password: str, token_dir: str = None, session_data: str = None, user_id: str = None
) -> Tuple[Optional[Garmin], Union[bool, str]]:
    """Authenticates or resumes a Garth session and returns a Garmin client.
    
    Args:
        email: Garmin account email
        password: Garmin account password  
        token_dir: Directory to store tokens (auto-generated if None)
        session_data: JSON string with existing tokens from database
        user_id: User ID for unique token directory (recommended for multi-user)
    
    Returns:
        Tuple of (Garmin client or None, session_data string or False)
        session_data is a JSON string if tokens should be persisted to DB
    """
    session_result = False  # Default: no update needed
    
    # Generate unique token directory per user to avoid conflicts
    if token_dir is None:
        if user_id:
            token_dir = f".garth_{user_id}"
        else:
            token_dir = ".garth"
    
    # Helper function to read tokens as JSON string
    def _read_session_json() -> str:
        import json
        session_dict = {}
        for filename in ["oauth1_token.json", "oauth2_token.json"]:
            filepath = os.path.join(token_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    session_dict[filename] = json.load(f)
        return json.dumps(session_dict) if session_dict else ""
    
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
        
        client = None
        
        if tokens_exist:
            try:
                garth.resume(token_dir)
                client = Garmin(email=email, password=password)
                client.garth = garth.client
                # ✅ Leer tokens actualizados para devolver a DB
                session_result = _read_session_json()
                logger.info("Resumed Garmin session from tokens successfully")
            except Exception as e:
                logger.warning(f"Could not resume token session: {e}")
                # ✅ No retornar, continuar a fresh login
                client = None
        
        # Fresh login si no hay tokens o resume falló
        if client is None:
            try:
                client = Garmin(email=email, password=password)
                client.login()
                garth.save(token_dir)
                # ✅ Leer tokens guardados para devolver a DB
                session_result = _read_session_json()
                logger.info("Fresh login successful, session saved")
            except Exception as e:
                logger.error(f"Login failed: {e}")
                if "429" in str(e) or "Too Many Requests" in str(e):
                    logger.error("429 Too Many Requests — wait 5-10 minutes before retrying")
                return None, False

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

        return client, session_result
    except Exception as e:
        logger.error(f"Error connecting to Garmin: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None, False
