import sqlite3
import json

conn = sqlite3.connect('atlas.db')
cursor = conn.cursor()

print('=' * 70)
print('EXTRACCION COMPLETA DE DATOS - ATLAS AI CONTEXT FOR AI')
print('=' * 70)

# USERS
print('\n### USUARIOS ###')
cursor.execute('SELECT id, name, email, created_at FROM users')
for row in cursor.fetchall():
    print(f'user_id: {row[0]}')
    print(f'  name: {row[1]}')
    print(f'  email: {row[2]}')
    print(f'  created_at: {row[3]}')

# TOKENS
print('\n### CREDENCIALES ###')
cursor.execute('SELECT user_id, email, password, garmin_session FROM tokens')
rows = cursor.fetchall()
if not rows:
    print('No hay credenciales guardadas')
else:
    for row in rows:
        print(f'user_id: {row[0]}')
        print(f'  garmin_email: {row[1]}')
        print(f'  has_password: {bool(row[2])}')
        print(f'  has_session: {bool(row[3])}')

# BIOMETRICS
print('\n### BIOMETRICOS (todos los registros) ###')
cursor.execute('SELECT user_id, date, source, data, timestamp FROM biometrics ORDER BY date DESC')
rows = cursor.fetchall()
print(f'Total: {len(rows)} registros')
for row in rows:
    print(f'\n--- {row[1]} ({row[2]}) ---')
    print(f'user_id: {row[0]}')
    print(f'timestamp: {row[4]}')
    if row[3]:
        try:
            data = json.loads(row[3])
            for k, v in data.items():
                print(f'{k}: {v}')
        except:
            print(f'data: {row[3]}')

# WORKOUTS
print('\n### ENTRENAMIENTOS (todos los registros) ###')
cursor.execute('SELECT user_id, source, name, description, date, duration, calories FROM workouts ORDER BY date DESC')
rows = cursor.fetchall()
print(f'Total: {len(rows)} registros')
for row in rows:
    print(f'\n--- {row[2]} ---')
    print(f'user_id: {row[0]}')
    print(f'source: {row[1]}')
    print(f'description: {row[3]}')
    print(f'date: {row[4]}')
    print(f'duration_seconds: {row[5]}')
    print(f'calories: {row[6]}')

conn.close()
print('\n' + '=' * 70)
print('EXTRACCION COMPLETADA')
print('=' * 70)
