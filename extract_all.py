import sqlite3
import json

conn = sqlite3.connect('atlas.db')
cursor = conn.cursor()

print('=' * 60)
print('EXTRACCION COMPLETA DE DATOS GARMIN - ATLAS AI')
print('=' * 60)

# USERS
print('\n=== USUARIOS ===')
cursor.execute('SELECT id, name, email, created_at FROM users')
for row in cursor.fetchall():
    print(f'ID: {row[0]}')
    print(f'  Nombre: {row[1]}')
    print(f'  Email: {row[2]}')
    print(f'  Creado: {row[3]}')

# TOKENS
print('\n=== CREDENCIALES GARMIN ===')
cursor.execute('SELECT user_id, email, password, garmin_session FROM tokens')
for row in cursor.fetchall():
    print(f'User ID: {row[0]}')
    print(f'  Email: {row[1]}')
    print(f'  Password: {"***" if row[2] else "NO"}')
    print(f'  Session: {"SI" if row[3] else "NO"}')

# BIOMETRICS
print('\n=== BIOMETRICOS ===')
cursor.execute('SELECT id, user_id, date, source, data, recovery_time, training_status, hrv_status FROM biometrics ORDER BY date DESC')
rows = cursor.fetchall()
print(f'Total registros: {len(rows)}')
for row in rows[:20]:
    print(f'\n--- Registro {row[0]} ---')
    print(f'  Usuario: {row[1]}')
    print(f'  Fecha: {row[2]}')
    print(f'  Fuente: {row[3]}')
    print(f'  Recovery Time: {row[5]}')
    print(f'  Training Status: {row[6]}')
    print(f'  HRV Status: {row[7]}')
    if row[4]:
        try:
            data = json.loads(row[4])
            print(f'  Datos:')
            for k, v in data.items():
                print(f'    {k}: {v}')
        except:
            print(f'  Datos: {row[4]}')

# WORKOUTS
print('\n=== ENTRENAMIENTOS ===')
cursor.execute('SELECT id, user_id, source, external_id, name, description, date, duration, calories FROM workouts ORDER BY date DESC')
rows = cursor.fetchall()
print(f'Total registros: {len(rows)}')
for row in rows[:30]:
    print(f'\n--- Entrenamiento {row[0]} ---')
    print(f'  Usuario: {row[1]}')
    print(f'  Fuente: {row[2]}')
    print(f'  External ID: {row[3]}')
    print(f'  Nombre: {row[4]}')
    print(f'  Descripcion: {row[5]}')
    print(f'  Fecha: {row[6]}')
    print(f'  Duracion: {row[7]}s ({row[7]/60:.1f} min)')
    print(f'  Calorias: {row[8]}')

conn.close()
print('\n' + '=' * 60)
print('EXTRACCION COMPLETADA')
print('=' * 60)
