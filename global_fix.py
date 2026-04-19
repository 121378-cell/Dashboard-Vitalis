import sqlite3
import os
import json

db_files = [
    "c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas.db",
    "c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas_v2.db",
    "c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/backend/atlas.db",
    "c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/backend/atlas_v2.db"
]

def global_cleanup():
    for db_path in db_files:
        if not os.path.exists(db_path):
            continue
            
        print(f"Abriendo: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Limpiar Tabla USERS
        try:
            cursor.execute("UPDATE users SET name = 'Sergi' WHERE id = 'default_user' OR name = 'Atleta ATLAS'")
            print(f"  Tabla 'users' actualizada.")
        except:
            pass
            
        # 2. Limpiar Tabla ATHLETE_PROFILES
        try:
            res = cursor.execute("SELECT data FROM athlete_profiles").fetchall()
            for row in res:
                try:
                    data = json.loads(row[0])
                    data["name"] = "Sergi"
                    data["age"] = 47
                    data["goal"] = "Proyecto 31/07 - Definicion"
                    cursor.execute("UPDATE athlete_profiles SET data = ? WHERE user_id = 'default_user'", (json.dumps(data),))
                except:
                    continue
            print(f"  Tabla 'athlete_profiles' actualizada.")
        except:
            pass
            
        conn.commit()
        conn.close()

if __name__ == "__main__":
    global_cleanup()
    print("\nPROCESO TERMINADO. Todas las DBs del PC estan sincronizadas como Sergi.")
