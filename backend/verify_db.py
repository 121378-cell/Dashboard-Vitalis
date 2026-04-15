import sqlite3

print("=" * 60)
print("VERIFICACIÓN DE BASE DE DATOS - ATLAS")
print("=" * 60)

# Conectar a la base de datos
conn = sqlite3.connect('../atlas.db')
cursor = conn.cursor()

# 1. Listar todas las tablas
print("\n[1] TABLAS EN LA BASE DE DATOS:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"   - {table[0]}")

# 2. Verificar si existe 'tokens'
token_tables = [t[0] for t in tables if 'token' in t[0].lower()]
if token_tables:
    print(f"\n[2] Tablas relacionadas con 'token': {token_tables}")
    
    for table_name in token_tables:
        print(f"\n[3] ESTRUCTURA DE TABLA '{table_name}':")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            print(f"   - {col_name} ({col_type})")
        
        # Verificar si tiene datos
        print(f"\n[4] CONTENIDO DE '{table_name}':")
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            if rows:
                col_names = [c[1] for c in columns]
                print(f"   Columnas: {col_names}")
                for i, row in enumerate(rows):
                    print(f"   Fila {i+1}: {row}")
            else:
                print("   (tabla vacía)")
        except Exception as e:
            print(f"   Error leyendo datos: {e}")
else:
    print("\n[2] No se encontraron tablas con 'token' en el nombre")

conn.close()
print("\n" + "=" * 60)
print("VERIFICACIÓN COMPLETADA")
print("=" * 60)