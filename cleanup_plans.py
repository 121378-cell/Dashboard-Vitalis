import sqlite3

db_path = 'backend/atlas_v2.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    # Marcar todos los planes maestros como cancelados/borrados
    cur.execute("UPDATE master_plans SET status = 'cancelled' WHERE status = 'active'")
    
    # Marcar todos los planes adaptativos como cancelados
    cur.execute("UPDATE adaptive_training_plans SET status = 'cancelled' WHERE status = 'active'")
    
    conn.commit()
    print("Limpieza completada. Todos los planes activos han sido cancelados.")
except Exception as e:
    print(f"Error limpiando la BD: {e}")
finally:
    conn.close()
