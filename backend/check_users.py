import sqlite3
conn = sqlite3.connect("../atlas_v2.db")
users = conn.execute("SELECT * FROM users").fetchall()
print("Usuarios:", users)
conn.close()
