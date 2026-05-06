"""
Verificar nombres de tablas en base de datos SQLite
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from sqlalchemy import text

conn = engine.connect()
result = conn.execute(text('SELECT name FROM sqlite_master WHERE type="table"'))
tables = [row[0] for row in result.fetchall()]
print('Tablas:', tables)
conn.close()
