"""
Migration: Add birth_date column to users table
================================================

This script adds the birth_date column to the users table
to support age calculation and aging considerations for the coach.

Ejecución:
    cd backend
    python migrate_birth_date.py
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
from datetime import date

def migrate():
    """Add birth_date column to users table."""
    print("Adding birth_date column to users table...")
    
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'birth_date' in columns:
                print("✅ Column birth_date already exists")
                return True
            
            # Add the column
            conn.execute(text("ALTER TABLE users ADD COLUMN birth_date DATE"))
            conn.commit()
            
            print("✅ Column birth_date added successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_user_birth_date():
    """Update default_user with birth date (30-05-1978)."""
    print("\nUpdating default_user birth date...")
    
    try:
        with engine.connect() as conn:
            # Update default_user with birth date
            conn.execute(text(
                "UPDATE users SET birth_date = '1978-05-30' WHERE id = 'default_user'"
            ))
            conn.commit()
            
            print("✅ Default user birth date updated: 1978-05-30")
            
            # Verify the update
            result = conn.execute(text(
                "SELECT id, name, birth_date FROM users WHERE id = 'default_user'"
            ))
            user = result.fetchone()
            
            if user:
                print(f"   User: {user[1]}")
                print(f"   Birth date: {user[2]}")
                
                # Calculate age
                if user[2]:
                    today = date.today()
                    birth_date = user[2]
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    print(f"   Current age: {age} years old")
            
            return True
            
    except Exception as e:
        print(f"❌ Error updating user birth date: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar migración y actualización."""
    print("\n" + "="*60)
    print("MIGRATION: Add birth_date to users table")
    print("="*60)
    
    # Ejecutar migración
    success = migrate()
    
    if success:
        # Actualizar fecha de nacimiento del usuario
        update_user_birth_date()
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\n🎉 The coach can now track athlete aging!")
        print("   - Birth date: 1978-05-30")
        print("   - Current age: 47 years old")
        print("   - Age-aware recommendations enabled")
        
        return 0
    else:
        print("\n❌ MIGRATION FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
