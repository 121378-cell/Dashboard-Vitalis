import sqlite3
import json

conn = sqlite3.connect('atlas_v2.db')
cursor = conn.cursor()

print('=== TABLAS EN LA BASE DE DATOS ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for t in cursor.fetchall():
    print(f'  - {t[0]}')

print('\n=== BIOMETRICS (ultimos 10) ===')
cursor.execute('SELECT id, user_id, date, source, recovery_time, training_status, hrv_status, data FROM biometrics ORDER BY date DESC LIMIT 10')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, User: {row[1]}, Date: {row[2]}, Source: {row[3]}, Recovery: {row[4]}, Status: {row[5]}, HRV Status: {row[6]}')
    print(f'  Data: {row[7][:200] if row[7] else None}...')

print('\n=== WORKOUTS (ultimos 10) ===')
cursor.execute('SELECT id, user_id, source, name, date, duration, calories, description FROM workouts ORDER BY date DESC LIMIT 10')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, User: {row[1]}, Source: {row[2]}, Name: {row[3]}, Date: {row[4]}, Duration: {row[5]}s, Calories: {row[6]}')
    print(f'  Description: {row[7][:100] if row[7] else None}...')

print('\n=== TOKENS ===')
cursor.execute('SELECT user_id, garmin_email, garmin_session IS NOT NULL as has_session, wger_api_key IS NOT NULL as has_wger, hevy_username FROM tokens')
for row in cursor.fetchall():
    print(f'User: {row[0]}, Garmin: {row[1]}, Session: {row[2]}, Wger: {row[3]}, Hevy: {row[4]}')

print('\n=== USERS ===')
cursor.execute('SELECT id, name, email FROM users')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, Name: {row[1]}, Email: {row[2]}')

conn.close()
