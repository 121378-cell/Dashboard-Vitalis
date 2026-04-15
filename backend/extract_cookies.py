#!/usr/bin/env python3
"""Extrae cookies de Chrome/Edge para Garmin Connect"""

import json
import os
import sys

# Intentar importar browser_cookie3
try:
    import browser_cookie3
except ImportError:
    print("Instalando browser_cookie3...")
    os.system(f"{sys.executable} -m pip install browser-cookie3 -q")
    import browser_cookie3

def extract_garmin_cookies():
    """Extrae cookies de Garmin de Chrome/Edge"""
    
    print("🔍 Extrayendo cookies de navegador...")
    print()
    
    # Intentar Chrome
    try:
        print("Intentando Chrome...")
        cj = browser_cookie3.chrome(domain_name='garmin.com')
        cookies = {c.name: c.value for c in cj}
        
        if cookies:
            print(f"✅ Encontradas {len(cookies)} cookies de Garmin")
            print()
            
            # Cookies importantes
            important = ['GARMIN-SSO', 'GARMIN-SSO-CUST-GUID', 'SESSIONID', 
                      'CASTGC', 'TGC', 'GARMIN_SESSION', 'AccessToken',
                      'JWT_FGP', ' RefreshToken']
            
            print("Cookies relevantes:")
            for name in important:
                if name in cookies:
                    value = cookies[name]
                    print(f"  {name}: {value[:50]}..." if len(value) > 50 else f"  {name}: {value}")
            
            # Guardar en archivo
            with open('.garth/garmin_cookies.json', 'w') as f:
                json.dump(cookies, f, indent=2)
            
            print(f"\n✅ Cookies guardadas en .garth/garmin_cookies.json")
            return cookies
            
    except Exception as e:
        print(f"❌ Chrome: {e}")
    
    # Intentar Edge
    try:
        print("\nIntentando Edge...")
        cj = browser_cookie3.edge(domain_name='garmin.com')
        cookies = {c.name: c.value for c in cj}
        
        if cookies:
            print(f"✅ Encontradas {len(cookies)} cookies de Garmin")
            return cookies
            
    except Exception as e:
        print(f"❌ Edge: {e}")
    
    return None

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 EXTRACTOR DE COOKIES GARMIN")
    print("=" * 60)
    print()
    
    cookies = extract_garmin_cookies()
    
    if not cookies:
        print("\n❌ No se pudieron extraer cookies automáticamente")
        print("\nAlternativa manual:")
        print("1. Abre https://connect.garmin.com en Chrome/Edge")
        print("2. Presiona F12 → Application → Cookies")
        print("3. Copia manualmente GARMIN-SSO y GARMIN-SSO-CUST-GUID")
