"""
Convierte tokens formato garth (oauth1_token.json + oauth2_token.json)
al formato nativo garminconnect (garmin_tokens.json con di_token, di_refresh_token, di_client_id).

El access_token de garth es un JWT del DI de Garmin — el mismo di_token que necesita garminconnect.
El refresh_token de garth es el mismo di_refresh_token.
El client_id se extrae del payload del JWT.
"""

import json
import base64
import sys
import os
from pathlib import Path


def decode_jwt_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError(f"Not a JWT: {token[:50]}...")
    payload = parts[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    return json.loads(base64.b64decode(payload, validate=False))


def convert_garth_to_garminconnect(garth_dir: str, output_path: str = None):
    garth_dir = Path(garth_dir)
    oauth2_file = garth_dir / "oauth2_token.json"

    if not oauth2_file.exists():
        print(f"ERROR: {oauth2_file} not found")
        sys.exit(1)

    with open(oauth2_file) as f:
        garth_data = json.load(f)

    access_token = garth_data["access_token"]
    refresh_token = garth_data["refresh_token"]

    try:
        payload = decode_jwt_payload(access_token)
        client_id = payload.get("client_id")
        if not client_id:
            print("ERROR: JWT no contiene client_id")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR decodificando JWT: {e}")
        sys.exit(1)

    garminconnect_data = {
        "di_token": access_token,
        "di_refresh_token": refresh_token,
        "di_client_id": client_id,
    }

    if output_path is None:
        output_path = garth_dir / "garmin_tokens.json"
    else:
        output_path = Path(output_path)

    with open(output_path, "w") as f:
        json.dump(garminconnect_data, f, indent=2)

    print(f"Tokens convertidos exitosamente:")
    print(f"  di_client_id: {client_id}")
    print(f"  di_token: {access_token[:50]}...")
    print(f"  di_refresh_token: {refresh_token[:50]}...")
    print(f"  Guardado en: {output_path}")

    return str(output_path)


if __name__ == "__main__":
    garth_dir = sys.argv[1] if len(sys.argv) > 1 else "garmin_tokens_local"
    output = sys.argv[2] if len(sys.argv) > 2 else None
    convert_garth_to_garminconnect(garth_dir, output)
