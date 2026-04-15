#!/usr/bin/env python3
"""Diagnóstico del mapeo SQLAlchemy del modelo Token"""

from app.models.token import Token
from sqlalchemy import inspect

print("Columnas mapeadas por SQLAlchemy:")
mapper = inspect(Token)
for col in mapper.columns:
    print(f"  {col.name}: {col.type}")

print("\nVerificar si 'email' y 'password' están mapeadas:")
column_names = [col.name for col in mapper.columns]
print(f"  'email' mapeada: {'email' in column_names}")
print(f"  'password' mapeada: {'password' in column_names}")
print(f"  Columnas totales: {column_names}")
