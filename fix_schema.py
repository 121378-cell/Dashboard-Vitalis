import sqlite3
from pathlib import Path

db_files = [
    "c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas.db",
    "c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas_v2.db"
]

def fix_schema():
    for db_path in db_files:
        if not Path(db_path).exists():
            continue
            
        print(f"Reparando esquema en: {db_path}...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Añadir columnas si no existen en la tabla biometrics
        columns_to_add = [
            ("recovery_time", "INTEGER"),
            ("training_status", "TEXT"),
            ("hrv_status", "TEXT")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE biometrics ADD COLUMN {col_name} {col_type}")
                print(f"  Columna '{col_name}' añadida.")
            except sqlite3.OperationalError:
                # La columna ya existe, ignorar
                print(f"  Columna '{col_name}' ya existe.")
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    fix_schema()
    print("\n--- BASE DE DATOS REPARADA ---")
