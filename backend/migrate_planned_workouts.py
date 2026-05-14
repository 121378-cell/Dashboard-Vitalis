"""
Migration: Create planned_workouts table
==========================================

This script creates the `planned_workouts` table for the training engine's
PlannedWorkout model (UUID PK) and migrates any existing data from the legacy
`adaptive_planned_sessions` table.

The `workouts` table (Integer PK, for Garmin/Strava activities) remains untouched.

Ejecucion:
    cd backend
    python migrate_planned_workouts.py
"""

import sys
import os
import io
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import logging
from app.db.session import engine
from sqlalchemy import text

logger = logging.getLogger("migration.planned_workouts")


def _table_exists(cursor, table_name):
    """Check if a table exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def create_planned_workouts_table():
    """Create the planned_workouts table if it doesn't exist."""
    logger.info("Creating planned_workouts table...")

    try:
        with engine.connect() as conn:
            # Use raw connection for PRAGMA
            raw = conn.connection.connection
            cursor = raw.cursor()

            if _table_exists(cursor, "planned_workouts"):
                logger.info("Table planned_workouts already exists")
                return True

            # Create the table
            conn.execute(text("""
                CREATE TABLE planned_workouts (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    plan_id VARCHAR,
                    user_id VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    status VARCHAR DEFAULT 'scheduled',
                    workout_type VARCHAR DEFAULT 'strength',
                    scheduled_date DATETIME,
                    completed_date DATETIME,
                    estimated_duration_minutes INTEGER DEFAULT 60,
                    actual_duration_minutes INTEGER,
                    readiness_score_at_creation FLOAT,
                    readiness_score_at_execution FLOAT,
                    fatigue_score FLOAT,
                    sleep_hours_last_night FLOAT,
                    total_sets_planned INTEGER DEFAULT 0,
                    total_sets_completed INTEGER DEFAULT 0,
                    total_volume_kg FLOAT DEFAULT 0,
                    average_rpe_actual FLOAT,
                    user_notes TEXT,
                    coach_notes TEXT,
                    version INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    FOREIGN KEY(plan_id) REFERENCES training_plans(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """))
            conn.commit()

            # Create index on user_id
            conn.execute(text("""
                CREATE INDEX ix_planned_workouts_user_id
                ON planned_workouts(user_id)
            """))
            conn.commit()

            # Create index on plan_id
            conn.execute(text("""
                CREATE INDEX ix_planned_workouts_plan_id
                ON planned_workouts(plan_id)
            """))
            conn.commit()

            logger.info("Table planned_workouts created successfully")
            return True    except Exception as e:
        logger.exception("Error creating table")
        return False



def migrate_adaptive_sessions():
    """Migrate data from adaptive_planned_sessions to planned_workouts."""
    logger.info("Migrating existing data from adaptive_planned_sessions...")

    try:
        with engine.connect() as conn:
            raw = conn.connection.connection
            cursor = raw.cursor()

            # Check source table exists
            if not _table_exists(cursor, "adaptive_planned_sessions"):
                logger.info("Source table adaptive_planned_sessions does not exist, skipping migration")
                return True

            # Count rows to migrate
            cursor.execute("SELECT COUNT(*) FROM adaptive_planned_sessions")
            count = cursor.fetchone()[0]

            if count == 0:
                logger.info("No data to migrate (adaptive_planned_sessions is empty)")
                return True

            logger.info(f"Found {count} sessions to migrate")

            # Check if already migrated (guard against re-migration)
            cursor.execute("SELECT COUNT(*) FROM planned_workouts")
            existing_count = cursor.fetchone()[0]
            if existing_count > 0:
                logger.info(f"planned_workouts already has {existing_count} rows, skipping re-migration")
                return True

            # Fetch all sessions
            cursor.execute("""
                SELECT session_date, title, description,
                       duration_minutes, completed, user_notes, session_type
                FROM adaptive_planned_sessions
            """)
            sessions = cursor.fetchall()

            migrated = 0
            for row_vals in sessions:
                session_date, title, description, \
                    duration_minutes, completed, user_notes, session_type = row_vals

                new_id = str(uuid.uuid4())
                status = "completed" if completed else "scheduled"

                # Convert session_date (DATE string) to datetime
                scheduled_date = None
                if session_date:
                    scheduled_date = f"{session_date}T00:00:00"

                # Legacy plan_ids are INTEGER from adaptive_training_plans,
                # but planned_workouts.plan_id is VARCHAR FK to training_plans(id)
                # (UUID strings). Set to NULL to avoid FK constraint errors.
                conn.execute(text("""
                    INSERT INTO planned_workouts (
                        id, plan_id, user_id, name, description,
                        status, workout_type, scheduled_date,
                        estimated_duration_minutes, user_notes
                    ) VALUES (
                        :id, NULL, 'default_user', :name, :description,
                        :status, :workout_type, :scheduled_date,
                        :duration, :user_notes
                    )
                """), {
                    "id": new_id,
                    "name": title,
                    "description": description,
                    "status": status,
                    "workout_type": session_type or "strength",
                    "scheduled_date": scheduled_date,
                    "duration": duration_minutes,
                    "user_notes": user_notes,
                })
                migrated += 1

            conn.commit()
            logger.info(f"Migrated {migrated} sessions to planned_workouts")
            return True    except Exception as e:
        logger.exception("Error migrating data")
        return False



def verify():
    """Verify the migration results."""
    logger.info("Verifying migration...")

    try:
        with engine.connect() as conn:
            raw = conn.connection.connection
            cursor = raw.cursor()

            # Check table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='planned_workouts'
            """)
            if cursor.fetchone():
                logger.info("planned_workouts table exists")
            else:
                logger.error("planned_workouts table NOT found")
                return False

            # Count rows
            cursor.execute("SELECT COUNT(*) FROM planned_workouts")
            count = cursor.fetchone()[0]
            logger.info(f"planned_workouts rows: {count}")

            # Show sample
            if count > 0:
                cursor.execute("""
                    SELECT id, name, status, workout_type,
                           scheduled_date, user_id
                    FROM planned_workouts LIMIT 3
                """)
                logger.info("Sample rows:")
                for row_vals in cursor.fetchall():
                    logger.info(f"  - {row_vals[0][:8]}... | {row_vals[1]} | {row_vals[2]} | {row_vals[3]} | {row_vals[4]}")

            # Check columns
            logger.info("Table schema:")
            cursor.execute("PRAGMA table_info(planned_workouts)")
            for row_vals in cursor.fetchall():
                logger.info(f"  {row_vals[1]:35s} {row_vals[2]:10s} nullable={not bool(row_vals[3])}")

            return True    except Exception as e:
        logger.exception("Error verifying migration")
        return False



def main():
    """Run the migration."""
    logger.info("=" * 60)
    logger.info("MIGRATION: Create planned_workouts table")
    logger.info("=" * 60)

    # Step 1: Create the table
    if not create_planned_workouts_table():
        logger.error("MIGRATION FAILED at step 1")
        return 1

    # Step 2: Migrate existing data
    if not migrate_adaptive_sessions():
        logger.warning("Data migration step had issues, but table was created")

    # Step 3: Verify
    verify()

    logger.info("=" * 60)
    logger.info("MIGRATION COMPLETED")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
