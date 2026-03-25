#!/usr/bin/env python3
"""
Script to clear Garmin sessions and tokens
"""

import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_garmin_sessions():
    """Clear all Garmin session files and tokens"""
    token_dirs = [".garth", "garth"]

    for token_dir in token_dirs:
        if os.path.exists(token_dir):
            try:
                shutil.rmtree(token_dir)
                logger.info(f"Removed Garmin session directory: {token_dir}")
            except Exception as e:
                logger.error(f"Error removing {token_dir}: {e}")
        else:
            logger.info(f"Garmin session directory not found: {token_dir}")

    # Also remove any .garth files in current directory
    for file in os.listdir("."):
        if file.startswith(".garth") or file.startswith("garth"):
            try:
                if os.path.isfile(file):
                    os.remove(file)
                    logger.info(f"Removed file: {file}")
                elif os.path.isdir(file):
                    shutil.rmtree(file)
                    logger.info(f"Removed directory: {file}")
            except Exception as e:
                logger.error(f"Error removing {file}: {e}")

    logger.info("Garmin session cleanup completed!")


if __name__ == "__main__":
    clear_garmin_sessions()
