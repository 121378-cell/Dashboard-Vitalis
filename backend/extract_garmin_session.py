"""
Extrae sesión de Garmin desde cookies del navegador
Evita el login y el rate limit 429
"""
import browser_cookie3
import requests
import json
import os
import sys
from datetime import datetime

def extract_garmin_session():
    """Extrae cookies de sesión de Chrome/Edge para Garmin"""
    
    print("🔍 Buscando cookies de Garmin en Chrome...")
    
    try:
        # Intentar obtener cookies de Chrome
        cj = browser_cookie3.chrome(domain_name='garmin.com')
    except Exception as e:
        print(f"❌ Error leyendo cookies de Chrome: {e}")
        print("🔍 Intentando con Edge...")
        try:
            cj = browser_cookie3.edge(domain_name='garmin.com')
        except Exception as e2:
            print(f"❌ Error leyendo cookies de Edge: {e2}")
            return None
    
    # Convertir a diccionario
    cookies = {}
    garmin_cookies = []
    
    for cookie in cj:
        if 'garmin' in cookie.domain.lower():
            cookies[cookie.name] = cookie.value
            garmin_cookies.append({
                'name': cookie.name,
                'value': cookie.value[:100] + '...' if len(cookie.value) > 100 else cookie.value,
                'domain': cookie.domain
            })
    
    print(f"\n✅ Cookies de Garmin encontradas: {len(garmin_cookies)}")
    for c in garmin_cookies:
        print(f"  - {c['name']}: {c['value'][:50]}...")
    
    # Verificar si hay sesión activa
    if not any('SSO' in name for name in cookies.keys()):
        print("\n❌ No se encontró cookie de sesión GARMIN-SSO")
        print("   Asegúrate de estar logueado en https://connect.garmin.com")
        return None
    
    return cookies

def test_garmin_api(cookies):
    """Prueba la API de Garmin con las cookies"""
    
    print("\n🧪 Probando API de Garmin con cookies...")
    
    # Headers típicos de Garmin Connect
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://connect.garmin.com/modern/dashboard',
    }
    
    # URLs de prueba
    urls = [
        'https://connect.garmin.com/user-info',
        'https://connect.garmin.com/modern/proxy/userprofile-service/userprofile/personal-information',
        'https://connect.garmin.com/modern/proxy/usersummary-service/usersummary/daily/2024-01-01',
    ]
    
    session = requests.Session()
    session.headers.update(headers)
    
    # Añadir cookies
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='.garmin.com')
    
    results = {}
    
    for url in urls:
        try:
            print(f"\n  Testing: {url.split('/')[-1]}")
            response = session.get(url, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ Success! Data preview: {str(data)[:200]}")
                    results[url] = True
                    
                    # Si es el perfil, extraer info útil
                    if 'personal-information' in url:
                        display_name = data.get('displayName') or data.get('username')
                        if display_name:
                            print(f"  👤 Usuario: {display_name}")
                            
                except:
                    print(f"  ⚠️  Response no es JSON: {response.text[:200]}")
                    results[url] = False
            else:
                print(f"  ❌ Failed: {response.text[:200]}")
                results[url] = False
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[url] = False
    
    return results

def save_session_for_garth(cookies):
    """
    Intenta crear tokens compatibles con garth
    Nota: Esto es experimental, garth normalmente requiere OAuth flow completo
    """
    print("\n💾 Guardando sesión...")
    
    # Crear estructura de sesión
    session_data = {
        'cookies': cookies,
        'timestamp': datetime.now().isoformat(),
        'source': 'browser_cookies'
    }
    
    # Guardar como archivo de sesión
    os.makedirs('.garth', exist_ok=True)
    session_file = '.garth/browser_session.json'
    
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"✅ Sesión guardada en: {session_file}")
    print("\n⚠️  NOTA IMPORTANTE:")
    print("   Las cookies de navegador NO son directamente compatibles con garth.")
    print("   garth requiere tokens OAuth obtenidos mediante su propio handshake.")
    print("\n   Opciones:")
    print("   1. Usar las cookies directamente con requests (como hace test_garmin_api)")
    print("   2. Esperar 30-60 min y reintentar login con garth")
    print("   3. Usar una herramienta como mitmproxy para capturar tokens durante login")
    
    return session_file

def main():
    print("=" * 60)
    print("🔐 EXTRACTOR DE SESIÓN GARMIN DESDE NAVEGADOR")
    print("=" * 60)
    print()
    
    # Extraer cookies
    cookies = extract_garmin_session()
    
    if not cookies:
        print("\n❌ No se pudo extraer la sesión")
        print("\nAsegúrate de:")
        print("1. Estar logueado en https://connect.garmin.com")
        print("2. Usar Chrome o Edge")
        print("3. No tener el navegador en modo privado/incógnito")
        sys.exit(1)
    
    # Probar API
    results = test_garmin_api(cookies)
    
    # Verificar si funcionó
    if any(results.values()):
        print("\n" + "=" * 60)
        print("✅ SESIÓN VÁLIDA - API de Garmin accesible")
        print("=" * 60)
        print("\nPuedes usar estas cookies para hacer peticiones directas")
        print("a la API de Garmin sin pasar por garth.")
        
        # Guardar sesión
        save_session_for_garth(cookies)
        
        print("\n💡 EJEMPLO DE USO:")
        print("""
import requests
import browser_cookie3

# Obtener cookies
cj = browser_cookie3.chrome(domain_name='garmin.com')

# Hacer petición
session = requests.Session()
for cookie in cj:
    if 'garmin' in cookie.domain:
        session.cookies.set(cookie.name, cookie.value, domain=cookie.domain)

# Obtener datos
response = session.get('https://connect.garmin.com/modern/proxy/usersummary-service/usersummary/daily/2024-01-01')
data = response.json()
        """)
        
    else:
        print("\n" + "=" * 60)
        print("❌ LAS COOKIES NO FUNCIONAN PARA LA API")
        print("=" * 60)
        print("\nEsto puede significar:")
        print("1. La sesión expiró")
        print("2. Garmin requiere tokens OAuth específicos (no cookies de sesión)")
        print("3. Hay protección anti-scraping")
        print("\nRecomendación: Esperar 30-60 minutos y reintentar login con garth")

if __name__ == "__main__":
    main()
