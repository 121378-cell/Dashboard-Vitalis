import sqlite3
from pathlib import Path
import json

db_path = Path("c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas_v2.db")

def fix_profile():
    if not db_path.exists():
        print(f"BD no encontrada en {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. Actualizar tabla Users (campo name)
        cursor.execute("UPDATE users SET name = 'Sergi' WHERE id = 'default_user'")
        
        # 2. Actualizar Athlete Profiles
        res = cursor.execute("SELECT data FROM athlete_profiles WHERE user_id = 'default_user'").fetchone()
        if res:
            data = json.loads(res[0])
            data["name"] = "Sergi"
            data["age"] = 47
            data["goal"] = "Proyecto 31/07 - Definición"
            cursor.execute("UPDATE athlete_profiles SET data = ? WHERE user_id = 'default_user'", (json.dumps(data),))
        
        conn.commit()
        print("BD actualizada con exito: Ahora eres Sergi en el servidor.")
    except Exception as e:
        print(f"Error actualizando BD: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_profile()
