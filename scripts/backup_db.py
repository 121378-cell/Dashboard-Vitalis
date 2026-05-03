#!/usr/bin/env python3
"""
ATLAS Database Backup Script
=============================
Daily backup of atlas_v2.db to /data/backups/
Keeps last 7 backups, removes older ones.
Designed to run via fly.io scheduled tasks: DAILY 02:00 UTC

Usage:
  python scripts/backup_db.py
  fly ssh console --app atlas-vitalis-backend --command "python /app/scripts/backup_db.py"
"""

import os
import sys
import shutil
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("backup")

MAX_BACKUPS = 7
BACKUP_DIR = "/data/backups"


def get_db_path() -> str:
    database_url = os.getenv("DATABASE_URL", "sqlite:///atlas_v2.db")
    if database_url.startswith("sqlite:///"):
        path = database_url.replace("sqlite:///", "")
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        return path
    return ""


def verify_integrity(db_path: str) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        result = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return result[0] == "ok"
    except Exception as e:
        logger.error(f"Integrity check failed: {e}")
        return False


def create_backup(db_path: str, backup_dir: str) -> str:
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        sys.exit(1)

    if not verify_integrity(db_path):
        logger.error("Database integrity check FAILED — aborting backup")
        sys.exit(2)

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_name = f"atlas_v2_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    source_conn = sqlite3.connect(db_path)
    dest_conn = sqlite3.connect(backup_path)

    source_conn.backup(dest_conn)

    dest_conn.execute("PRAGMA integrity_check")
    dest_conn.close()
    source_conn.close()

    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    logger.info(f"Backup created: {backup_path} ({size_mb:.2f} MB)")

    return backup_path


def prune_old_backups(backup_dir: str, max_backups: int = MAX_BACKUPS):
    backups = sorted(
        Path(backup_dir).glob("atlas_v2_*.db"),
        key=lambda p: p.name,
        reverse=True,
    )

    if len(backups) > max_backups:
        for old_backup in backups[max_backups:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup.name}")


def main():
    logger.info("=" * 50)
    logger.info("ATLAS Database Backup - Starting...")
    logger.info("=" * 50)

    db_path = get_db_path()
    logger.info(f"Database path: {db_path}")

    try:
        backup_path = create_backup(db_path, BACKUP_DIR)
        prune_old_backups(BACKUP_DIR)
        logger.info("Backup completed successfully")
    except SystemExit:
        logger.error("BACKUP FAILED — immediate attention required")
        raise
    except Exception as e:
        logger.error(f"Backup failed with unexpected error: {e}")
        sys.exit(3)

    remaining = list(Path(BACKUP_DIR).glob("atlas_v2_*.db"))
    logger.info(f"Total backups retained: {len(remaining)}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
