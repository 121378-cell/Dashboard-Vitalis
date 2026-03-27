import sqlite3
import os

db_path = r'c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis\atlas_v2.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id, garmin_email, garmin_password IS NOT NULL, garmin_session IS NOT NULL FROM tokens')
        rows = cursor.fetchall()
        for row in rows:
            print(f"User: {row[0]}, Email: {row[1]}, Has Pwd: {row[2]}, Has Session: {row[3]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
