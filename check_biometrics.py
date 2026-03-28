import sqlite3, json
conn = sqlite3.connect("atlas_v2.db")
rows = conn.execute("SELECT date, source, data FROM biometrics ORDER BY date DESC LIMIT 3").fetchall()
for r in rows:
    d = json.loads(r[2]) if r[2] else {}
    print(r[0], r[1], "HR:", d.get("heartRate"), "SpO2:", d.get("spo2"), "Sleep:", round(d.get("sleep",0),1))
conn.close()
