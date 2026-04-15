"""
Script para subir los tokens de Garmin a Fly.io
"""
import subprocess
import json
import os

token_dir = "./garmin_tokens_local"
fly_app = "atlas-vitalis-backend"

# Leer tokens
with open(os.path.join(token_dir, "oauth1_token.json")) as f:
    oauth1 = json.load(f)
with open(os.path.join(token_dir, "oauth2_token.json")) as f:
    oauth2 = json.load(f)

print("Subiendo tokens a Fly.io...")

# Comando para crear directorio
subprocess.run(["fly", "ssh", "console", "--command", "mkdir -p /data/.garth"], check=False)

# Escribir oauth1_token.json
oauth1_json = json.dumps(oauth1, indent=4)
cmd1 = f'fly ssh console --command "echo \'{oauth1_json}\' > /data/.garth/oauth1_token.json"'
print(f"Ejecutando: {cmd1[:80]}...")
subprocess.run(cmd1, shell=True, check=False)

# Escribir oauth2_token.json
oauth2_json = json.dumps(oauth2, indent=4)
cmd2 = f'fly ssh console --command "echo \'{oauth2_json}\' > /data/.garth/oauth2_token.json"'
print(f"Ejecutando: {cmd2[:80]}...")
subprocess.run(cmd2, shell=True, check=False)

# Verificar
print("\nVerificando archivos...")
subprocess.run(["fly", "ssh", "console", "--command", "ls -la /data/.garth/"], check=False)

print("\n[OK] Tokens subidos a Fly.io")
print("Ahora intenta el sync de Garmin en tu app")
