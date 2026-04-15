import sqlite3  
conn = sqlite3.connect('../atlas.db')  
cursor = conn.cursor()  
cursor.execute('SELECT user_id, garmin_email, garmin_session IS NOT NULL FROM tokens')  
rows = cursor.fetchall()  
print(f'Registros encontrados: {len(rows)}')  
[print(f'User: {r[0]}, Email: {r[1]}, Session: {bool(r[2])}') for r in rows]  
conn.close() 
