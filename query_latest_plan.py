import sqlite3
import json

db_path = 'backend/atlas_v2.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get the latest adaptive plan
cur.execute('SELECT id, plan_json FROM adaptive_training_plans ORDER BY id DESC LIMIT 1')
row = cur.fetchone()
if row:
    plan_id, plan_json = row
    print(f'PLAN ID: {plan_id}')
    try:
        data = json.loads(plan_json)
        for s in data.get('sessions', []):
            date = s.get('date', '')
            day = s.get('day_of_week', '')
            stype = s.get('session_type', '')
            title = s.get('title', '')
            print(f'{date} ({day}): {stype} - {title}')
    except Exception as e:
        print('Error parsing JSON:', e)
else:
    print('No plans found.')
