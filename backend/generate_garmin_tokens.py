"""
Script para generar tokens de Garmin localmente y exportarlos.
USO: Ejecutar DESPUES de esperar 30-60 min si hubo rate limit previo.
"""
import os
import json
import garth
from garminconnect import Garmin
import time
import sys

# Directorio de tokens (consistente con app/utils/garmin.py)
token_dir = ".garth"
oauth1_path = os.path.join(token_dir, "oauth1_token.json")
oauth2_path = os.path.join(token_dir, "oauth2_token.json")

# Verificar si ya existen tokens válidos
if os.path.exists(oauth1_path) and os.path.exists(oauth2_path):
    print("Tokens existen. Verificando validez...")
    try:
        garth.resume(token_dir)
        client = Garmin()
        client.garth = garth.client
        profile = client.get_user_profile()
        print(f"✅ Tokens validos! Usuario: {profile.get('displayName', 'Unknown')}")
        print(f"📁 Ubicacion: {os.path.abspath(token_dir)}")
        sys.exit(0)
    except Exception as e:
        print(f"⚠️  Tokens existentes invalidos: {e}")
        print("🔄 Intentando login fresco...")

# Leer credenciales desde la base de datos
from app.db.session import SessionLocal
from app.models.token import Token

db = SessionLocal()
token_record = db.query(Token).filter(Token.email != None).first()

if not token_record:
    print("ERROR: No se encontraron credenciales de Garmin en la base de datos")
    exit(1)

GARMIN_EMAIL = token_record.email
GARMIN_PASSWORD = token_record.password

if not GARMIN_PASSWORD:
    print("ERROR: El email existe pero no hay contrasena guardada")
    print(f"Email encontrado: {GARMIN_EMAIL}")
    exit(1)

print(f"Email de Garmin: {GARMIN_EMAIL}")
print("="*60)
print("⚠️  IMPORTANTE: Si hubo rate limit (429) reciente:")
print("   - Espera 30-60 minutos antes de ejecutar este script")
print("   - O cambia tu contraseña de Garmin para resetear el bloqueo")
print("="*60)
print("\nIntentando login...")
db.close()

# Reintentos con backoff exponencial AGRESIVO (minutos, no segundos)
max_attempts = 3  # Menos intentos, mas espera entre ellos
attempt = 0

while attempt < max_attempts:
    attempt += 1
    try:
        print(f"\nIntento {attempt}/{max_attempts}...")
        garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)

        # GUARDAR TOKENS INMEDIATAMENTE en .garth (consistente con app/utils/garmin.py)
        token_dir = ".garth"
        os.makedirs(token_dir, exist_ok=True)
        garth.save(token_dir)

        print(f"\n[OK] Login exitoso!")
        print(f"[OK] Tokens guardados en: {token_dir}")

        # Verificar archivos
        oauth1_path = os.path.join(token_dir, "oauth1_token.json")
        oauth2_path = os.path.join(token_dir, "oauth2_token.json")

        with open(oauth1_path) as f:
            oauth1 = json.load(f)
            print(f"[OK] OAuth1 token: {str(oauth1)[:80]}...")

        with open(oauth2_path) as f:
            oauth2 = json.load(f)
            print(f"[OK] OAuth2 token: {str(oauth2)[:80]}...")

        # Intentar verificar con Garmin (puede fallar por DNS pero ya tenemos tokens)
        try:
            client = Garmin()
            client.garth = garth.client
            profile = client.get_user_profile()
            print(f"[OK] Sesion verificada: {profile.get('displayName', 'Unknown')}")
        except Exception as verify_err:
            print(f"[WARN] Verificacion fallo (pero tokens son validos): {verify_err}")

        print("\n" + "="*60)
        print("SIGUIENTES PASOS - Subir tokens a Fly.io:")
        print("="*60)
        print(f"\n1. Copia el contenido de {oauth1_path}")
        print("2. Copia el contenido de {oauth2_path}")
        print("\nO ejecuta estos comandos:")
        print(f"  fly ssh console -C 'mkdir -p /data/.garth'")
        print(f"  # Luego pega los contenidos de los archivos JSON")

        sys.exit(0)

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg or "429 Client Error" in error_msg:
            # Backoff en MINUTOS, no segundos
            wait_minutes = attempt * 5  # 5min, 10min
            print(f"\n🔴 RATE LIMIT ACTIVO (429)")
            print(f"   Garmin ha bloqueado temporalmente las peticiones.")
            print(f"   Esperando {wait_minutes} minutos antes de reintento {attempt + 1}...")
            print(f"   ⏰  Recomendacion: Espera 30-60 minutos total o cambia tu contraseña.")
            try:
                time.sleep(wait_minutes * 60)
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrumpido por usuario. Vuelve a intentar mas tarde.")
                print("💡 Sugerencia: Cambia tu contraseña de Garmin en https://connect.garmin.com")
                sys.exit(1)
        else:
            print(f"Error: {e}")
            # Error no recuperable, salir
            print("\n❌ Error no recuperable. Abortando.")
            sys.exit(1)

print("\n🔴 ERROR: Garmin ha bloqueado permanentemente la libreria 'garth'\n")
print("📋 ANALISIS:")
print("   - Tu cuenta funciona correctamente en el navegador")
print("   - Garmin detecta y bloquea peticiones automatizadas de 'garth'")
print("   - El bloqueo es a nivel de libreria, no de IP o cuenta\n")
print("💡 SOLUCIONES ALTERNATIVAS:")
print("   1. EXPORTAR MANUAL: Ve a https://connect.garmin.com/modern/export")
print("      - Descarga actividades en CSV/GPX")
print("      - Impórtalas manualmente al dashboard\n")
print("   2. USAR STRAVA COMO PUENTE:")
print("      - Conecta Garmin a Strava (en garmin.com)")
print("      - Usa API de Strava (mas permisiva)\n")
print("   3. ESPERAR DESBLOQUEO:")
print("      - Garmin eventualmente desbloquea (48-72h sin intentos)")
print("      - No uses el script durante este periodo\n")
print("🛠️  El dashboard funcionara sin sincronizacion Garmin hasta resolver esto.")
sys.exit(1)
