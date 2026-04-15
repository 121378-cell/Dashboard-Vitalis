import sqlite3
conn = sqlite3.connect('atlas_v2.db')
cursor = conn.cursor()
cursor.execute('SELECT garmin_email, garmin_password FROM tokens WHERE garmin_email IS NOT NULL')
row = cursor.fetchone()
if row:
    print(f"Email: {row[0]}")
    print(f"Password: {row[1] if row[1] else 'VACIA'}")
else:
    print("No hay registro")
conn.close()
