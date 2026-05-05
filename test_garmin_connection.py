#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de conexion Garmin con garminconnect 0.3.1
Hace login con email/password de la BD y prueba una llamada a la API.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

BACKEND_DIR = Path("backend")
TOKEN_DIR = BACKEND_DIR / ".garth"
TOKEN_FILE = TOKEN_DIR / "garmin_tokens.json"
DB_PATH = Path("atlas_v2.db")

print("=== TEST CONEXION GARMIN (v0.3.1) ===\n")

# Verificar BD
if not DB_PATH.exists():
    print(f"[ERROR] BD no encontrada: {DB_PATH}")
    sys.exit(1)

# Leer credenciales
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT email, password FROM tokens WHERE user_id='default_user'").fetchone()
conn.close()

email = row["email"] if row else None
password = row["password"] if row else None
print(f"Credenciales en BD: email={email}, password={'***' if password else 'NO'}")

# Verificar si hay token guardado
if TOKEN_FILE.exists():
    size = TOKEN_FILE.stat().st_size
    print(f"Token guardado: {TOKEN_FILE} ({size} bytes)")
else:
    print(f"Sin token guardado en {TOKEN_FILE}")

TOKEN_DIR.mkdir(exist_ok=True)

# Conectar
print("\nConectando a Garmin Connect...")
try:
    from garminconnect import Garmin

    # Intentar con token primero
    client = None
    if TOKEN_FILE.exists():
        try:
            c = Garmin()
            c.login(tokenstore=str(TOKEN_DIR))
            client = c
            print(f"[OK] Sesion desde token: {client.display_name}")
        except Exception as e:
            print(f"[WARN] Token invalido: {e}")
            TOKEN_FILE.unlink(missing_ok=True)

    # Si no, usar email/password
    if not client:
        if not email or not password:
            print("[ERROR] Sin credenciales. Configura email/password en tokens tabla de BD.")
            sys.exit(1)
        print(f"Login con {email}...")
        client = Garmin(email=email, password=password)
        mfa = client.login(tokenstore=str(TOKEN_DIR))
        if mfa:
            print("\nMFA requerido! Introduce el codigo:")
            code = input("Codigo: ").strip()
            client.resume_login(mfa, code)
        print(f"[OK] Login exitoso: {client.display_name}")

    # Guardar token
    client.garth.dump(str(TOKEN_DIR))
    print(f"[OK] Token guardado: {TOKEN_FILE}")

    # Test API
    from datetime import date
    today = date.today().isoformat()
    yesterday = (date.today().from_year_and_day(2026, 90)).isoformat()  # fallback

    print(f"\nProbando API get_stats({today})...")
    stats = client.get_stats(today)
    if stats:
        rhr = stats.get("restingHeartRate", "N/A")
        steps = stats.get("totalSteps", "N/A")
        cals = stats.get("totalKilocalories", "N/A")
        print(f"[OK] API funcionando!")
        print(f"  FC reposo: {rhr} bpm")
        print(f"  Pasos: {steps}")
        print(f"  Calorias: {cals}")
    else:
        print("[INFO] Sin datos para hoy (puede ser normal si es muy temprano)")

    print("\n*** TEST EXITOSO ***")
    print("Ahora ejecuta: python sync_garmin_to_atlas.py")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    print("\nPosibles causas:")
    print("  1. Credenciales incorrectas en la BD")
    print("  2. Garmin tiene rate limiting activo (espera 30min)")
    print("  3. MFA requerido")
    sys.exit(1)
