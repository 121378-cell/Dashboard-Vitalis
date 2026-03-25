#!/usr/bin/env python3
"""
Test script for Garmin connection
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from utils.garmin import get_garmin_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_garmin_connection():
    """Test Garmin connection with provided credentials"""
    # Load environment variables
    load_dotenv()

    # Get credentials from environment variables
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        logger.error("Missing GARMIN_EMAIL or GARMIN_PASSWORD environment variables")
        return False

    logger.info(f"Testing Garmin connection for user: {email}")

    try:
        client, session_updated = get_garmin_client(email, password)

        if not client:
            logger.error("Failed to create Garmin client")
            return False

        logger.info(
            f"Successfully connected to Garmin. Session updated: {session_updated}"
        )

        # Test getting user profile
        try:
            profile = client.get_user_profile()
            logger.info(f"User profile: {profile.get('displayName', 'Unknown')}")
        except Exception as e:
            logger.warning(f"Could not fetch user profile: {e}")

        # Test getting today's stats
        try:
            from datetime import date

            today = date.today().isoformat()
            stats = client.get_stats(today)
            logger.info(f"Today's stats retrieved successfully")
        except Exception as e:
            logger.warning(f"Could not fetch today's stats: {e}")

        return True

    except Exception as e:
        logger.error(f"Error testing Garmin connection: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    if test_garmin_connection():
        logger.info("Garmin connection test passed!")
        sys.exit(0)
    else:
        logger.error("Garmin connection test failed!")
        sys.exit(1)
