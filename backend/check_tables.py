import sqlite3
conn = sqlite3.connect("../atlas_v2.db")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tablas:", [t[0] for t in tables])
conn.close()
