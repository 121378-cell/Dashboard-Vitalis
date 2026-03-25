#!/usr/bin/env python3
"""
Script to test Garmin connection with delay to avoid rate limiting
"""

import os
import sys
import time
from dotenv import load_dotenv
import logging

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), "app")
sys.path.insert(0, backend_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Load environment variables
    load_dotenv()

    # Import after path is set
    try:
        from utils.garmin import get_garmin_client
    except ImportError as e:
        logger.error(f"Could not import garmin module: {e}")
        return False

    # Get credentials
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        logger.error("Please set GARMIN_EMAIL and GARMIN_PASSWORD in your .env file")
        return False

    logger.info(f"Testing Garmin connection for: {email}")
    logger.info("Waiting 5 seconds to avoid rate limiting...")
    time.sleep(5)

    try:
        client, session_updated = get_garmin_client(email, password)

        if client:
            logger.info("✅ Successfully connected to Garmin!")
            logger.info(f"Session updated: {session_updated}")

            # Try to get user info
            try:
                profile = client.get_user_profile()
                logger.info(
                    f"User: {profile.get('displayName', 'Unknown') if profile else 'Unknown'}"
                )
            except Exception as e:
                logger.warning(f"Could not get profile: {e}")

            return True
        else:
            logger.error("❌ Failed to connect to Garmin")
            return False

    except Exception as e:
        logger.error(f"Error connecting to Garmin: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
