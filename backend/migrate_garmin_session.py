"""
Migration: Add garmin_session column to tokens table
=====================================================

This script adds the garmin_session column to the tokens table
to support session persistence.

Ejecucion:
    cd backend
    python migrate_garmin_session.py
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import engine
from sqlalchemy import text

def migrate():
    """Add garmin_session column to tokens table."""
    print("Adding garmin_session column to tokens table...")
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(tokens)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'garmin_session' in columns:
                print("✅ Column garmin_session already exists")
                return True
            
            # Add the column
            conn.execute(text("ALTER TABLE tokens ADD COLUMN garmin_session TEXT"))
            conn.commit()
            
            print("✅ Column garmin_session added successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
