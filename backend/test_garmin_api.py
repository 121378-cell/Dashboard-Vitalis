#!/usr/bin/env python3
"""Test diferentes endpoints de Garmin API con el browser token"""

import json
import requests

# Cargar token guardado
with open('.garth/oauth2_browser.json', 'r') as f:
    token_data = json.load(f)

access_token = token_data.get('access_token')
headers = {
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Lista de endpoints a probar
endpoints = [
    ('Profile v1', 'https://connect.garmin.com/modern/proxy/userprofile-service/userprofile/personalInformation'),
    ('Profile v2', 'https://connect.garmin.com/userprofile-service/userprofile/personalInformation'),
    ('Activities', 'https://connect.garmin.com/modern/proxy/activitylist-service/activities/search/activities'),
    ('Daily summary', 'https://connect.garmin.com/wellness-service/wellness/dailySummary/'),
    ('User settings', 'https://connect.garmin.com/userprofile-service/userprofile/user-settings/'),
    ('Health stats', 'https://connect.garmin.com/wellness-service/wellness/epochs'),
]

print("=" * 60)
print("TEST DE ENDPOINTS GARMIN CONNECT")
print("=" * 60)

for name, url in endpoints:
    try:
        print(f"\n🔍 {name}")
        print(f"   URL: {url}")
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=False)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ ÉXITO!")
            try:
                data = response.json()
                print(f"   Respuesta: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Respuesta: {response.text[:100]}")
        elif response.status_code == 401:
            print(f"   ❌ No autorizado (token inválido)")
        elif response.status_code == 429:
            print(f"   ❌ Rate limit")
        elif response.status_code == 404:
            print(f"   ❌ Endpoint no existe")
        elif response.status_code in [301, 302, 307, 308]:
            print(f"   ↪️  Redirección a: {response.headers.get('Location', 'desconocido')}")
        else:
            print(f"   ⚠️  Error {response.status_code}: {response.text[:50]}")
            
    except Exception as e:
        print(f"   💥 Error: {e}")

print("\n" + "=" * 60)
