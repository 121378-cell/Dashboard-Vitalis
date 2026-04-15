#!/usr/bin/env python3
"""
Script de migración para añadir columnas de rate limiting a tabla tokens.
Ejecutar desde: backend/
Base de datos: ../atlas.db (ruta relativa desde backend/)
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'atlas.db')


def migrate_tokens_table():
    """Añade columnas de rate limiting a la tabla tokens si no existen."""
    
    # a. Verificación de existencia de archivo
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: No se encontró la base de datos en {os.path.abspath(DB_PATH)}")
        return False
    
    try:
        # b. Conexión a SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # c. Detección de columnas existentes
        cursor.execute("PRAGMA table_info(tokens)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        print(f"Columnas actuales: {existing_columns}")
        
        # d. Definición de columnas a añadir
        columns_to_add = [
            ('garmin_rate_limited_until', 'DATETIME'),
            ('last_login_attempt', 'DATETIME'),
            ('login_attempts_count', 'INTEGER DEFAULT 0')
        ]
        
        # e. Bucle de alteración
        added_count = 0
        for col_name, col_type in columns_to_add:
            if col_name in existing_columns:
                print(f"⏭️  Columna {col_name} ya existe, omitiendo")
                continue
            
            sql = f"ALTER TABLE tokens ADD COLUMN {col_name} {col_type}"
            cursor.execute(sql)
            print(f"✅ Añadida columna: {col_name} ({col_type})")
            added_count += 1
        
        conn.commit()
        
        # f. Verificación final
        cursor.execute("PRAGMA table_info(tokens)")
        final_columns = [col[1] for col in cursor.fetchall()]
        print(f"\nColumnas finales en tabla 'tokens' ({len(final_columns)} total):")
        print(f"  {final_columns}")
        
        # g. Resumen de ejecución
        if added_count > 0:
            print(f"\n✅ Migración completada: {added_count} columnas nuevas")
        else:
            print(f"\n✅ Verificación completada: todas las columnas ya existían")
        
        # h. Cierre de conexión
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error de base de datos SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACIÓN DE BASE DE DATOS - Tabla tokens")
    print("=" * 60)
    
    success = migrate_tokens_table()
    
    print("=" * 60)
    if success:
        print("Estado: ✅ ÉXITO")
        print("Puedes ejecutar ahora: python insert_garmin_credentials.py")
    else:
        print("Estado: ❌ FALLIDO")
        print("Revisa el error arriba.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
