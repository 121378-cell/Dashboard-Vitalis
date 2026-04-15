import sqlite3 
conn = sqlite3.connect('../atlas.db') 
cursor = conn.cursor() 
cursor.execute("SELECT user_id, email, password FROM tokens WHERE user_id = 'default_user'") 
row = cursor.fetchone() 
print(f'Registro: {row}') 
conn.close() 
