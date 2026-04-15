#!/usr/bin/env python3
"""Test API con cookies de navegador"""

import json
import requests

# Cargar cookies
with open('.garth/garmin_cookies.json', 'r') as f:
    cookies = json.load(f)

headers = {
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://connect.garmin.com/modern/dashboard',
    'NK': 'NT',
    'X-Requested-With': 'XMLHttpRequest',
}

print("=" * 60)
print("TEST CON COOKIES DE NAVEGADOR")
print("=" * 60)

# Endpoints a probar
endpoints = [
    ('Current User', 'https://connect.garmin.com/currentuser-service/user/info'),
    ('User Summary', 'https://connect.garmin.com/userprofile-service/userprofile/user-settings/'),
]

for name, url in endpoints:
    try:
        print(f"\n🔍 {name}")
        print(f"   URL: {url}")
        
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ ÉXITO!")
            try:
                data = response.json()
                print(f"   Respuesta: {json.dumps(data, indent=2)[:300]}")
            except:
                print(f"   Texto: {response.text[:100]}")
        elif response.status_code == 401:
            print(f"   ❌ No autorizado - cookies inválidas")
        elif response.status_code == 403:
            print(f"   ❌ Forbidden - posible CSRF")
        else:
            print(f"   ⚠️  {response.status_code}: {response.text[:50]}")
            
    except Exception as e:
        print(f"   💥 Error: {e}")

print("\n" + "=" * 60)
