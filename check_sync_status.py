#!/usr/bin/env python3
"""Check sync status and credentials in atlas_v2.db"""
import sqlite3
import os

DB_PATH = "atlas_v2.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== TOKENS TABLE ===")
c.execute("SELECT user_id, email, password, garmin_session FROM tokens LIMIT 5")
rows = c.fetchall()
for r in rows:
    sess_info = f"YES ({len(r['garmin_session'])} chars)" if r['garmin_session'] else "None"
    print(f"  user={r['user_id']}, email={r['email']}, pwd={'***' if r['password'] else 'None'}, session={sess_info}")

print("\n=== DATA COUNTS ===")
c.execute("SELECT COUNT(*) as cnt FROM biometrics")
print(f"  Biometrics rows: {c.fetchone()['cnt']}")

c.execute("SELECT COUNT(*) as cnt FROM workouts WHERE source='garmin'")
print(f"  Garmin workouts: {c.fetchone()['cnt']}")

c.execute("SELECT MAX(date) as latest FROM biometrics")
row = c.fetchone()
print(f"  Latest biometrics date: {row['latest']}")

c.execute("SELECT MAX(date) as latest FROM workouts WHERE source='garmin'")
row = c.fetchone()
print(f"  Latest garmin workout: {row['latest']}")

print("\n=== GARTH TOKENS ON DISK ===")
garth_dirs = [
    "backend/.garth",
    ".garth",
    "backend/garmin_tokens_local"
]
for d in garth_dirs:
    files = []
    if os.path.exists(d):
        files = os.listdir(d)
    print(f"  {d}: {files}")

conn.close()
print("\nDone!")
