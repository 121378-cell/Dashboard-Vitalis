"""Migration script to add missing columns to atlas_memory table."""
import sqlite3
import os

db_path = os.path.abspath('backend/atlas_v2.db')
print(f'Using DB at: {db_path}')
print(f'Exists: {os.path.exists(db_path)}')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(atlas_memory)')
cols = {row[1]: row[2] for row in cursor.fetchall()}
print(f'Current atlas_memory columns: {list(cols.keys())}')

migrations = []
if 'tags' not in cols:
    cursor.execute("ALTER TABLE atlas_memory ADD COLUMN tags TEXT DEFAULT '[]'")
    migrations.append('tags')
if 'updated_at' not in cols:
    cursor.execute("ALTER TABLE atlas_memory ADD COLUMN updated_at DATETIME")
    migrations.append('updated_at')

if migrations:
    conn.commit()
    print(f'Added columns: {migrations}')
else:
    print('No columns to add')

cursor.execute('PRAGMA table_info(atlas_memory)')
cols = {row[1]: row[2] for row in cursor.fetchall()}
print(f'Final columns: {list(cols.keys())}')

conn.close()
print('Migration complete')