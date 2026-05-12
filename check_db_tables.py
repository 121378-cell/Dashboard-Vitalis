import sqlite3

db_path = 'backend/atlas_v2.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('TABLAS EN BD:')
for t in tables:
    print(' -', t)

critical = ['master_plans', 'adaptive_training_plans', 'adaptive_planned_sessions']
missing = [t for t in critical if t not in tables]
if missing:
    print('\nFALTAN TABLAS CRITICAS:', missing)
else:
    print('\nTodas las tablas del plan maestro EXISTEN OK')

# Check column structure of adaptive_training_plans
if 'adaptive_training_plans' in tables:
    cur.execute("PRAGMA table_info(adaptive_training_plans)")
    cols = [r[1] for r in cur.fetchall()]
    print('\nColumnas adaptive_training_plans:', cols)
    required = ['master_plan_id', 'phase_number', 'week_number', 'confirmed_by_user']
    missing_cols = [c for c in required if c not in cols]
    if missing_cols:
        print('FALTAN COLUMNAS:', missing_cols)
    else:
        print('Columnas de master plan OK')

if 'master_plans' in tables:
    cur.execute("SELECT COUNT(*) FROM master_plans")
    count = cur.fetchone()[0]
    print(f'\nmaster_plans tiene {count} registros')
    cur.execute("PRAGMA table_info(master_plans)")
    mp_cols = [r[1] for r in cur.fetchall()]
    print('Columnas master_plans:', mp_cols)

conn.close()
