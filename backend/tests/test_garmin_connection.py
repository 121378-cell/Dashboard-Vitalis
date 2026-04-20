#!/usr/bin/env python3
"""Pytest validation for Garmin connectivity."""

import logging
import os
import sys
from datetime import date

import pytest
from dotenv import load_dotenv

# Add the backend/app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

from utils.garmin import get_garmin_client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_garmin_connection() -> None:
    """Test Garmin connection with provided credentials."""
    load_dotenv()

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        pytest.skip("Missing GARMIN_EMAIL or GARMIN_PASSWORD environment variables")

    logger.info("Testing Garmin connection for user: %s", email)

    client, session_updated = get_garmin_client(email, password)
    assert client is not None, "Failed to create Garmin client"

    logger.info("Successfully connected to Garmin. Session updated: %s", session_updated)

    try:
        profile = client.get_user_profile()
        logger.info("User profile: %s", profile.get("displayName", "Unknown"))
    except Exception as exc:  # pragma: no cover - external API variability
        logger.warning("Could not fetch user profile: %s", exc)

    try:
        today = date.today().isoformat()
        client.get_stats(today)
        logger.info("Today's stats retrieved successfully")
    except Exception as exc:  # pragma: no cover - external API variability
        logger.warning("Could not fetch today's stats: %s", exc)


if __name__ == "__main__":
    # Keep script-style execution behavior for manual debugging
    try:
        test_garmin_connection()
        logger.info("Garmin connection test passed!")
        sys.exit(0)
    except Exception:
        logger.exception("Garmin connection test failed!")
        sys.exit(1)
