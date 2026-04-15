#!/usr/bin/env python3
"""
Usar token del navegador (JetLagToken) para acceder a Garmin API directamente.
Este token es un JWT Bearer válido extraído del localStorage del navegador.
"""

import json
import os
import requests
from datetime import datetime, timedelta

# El usuario debe pegar aquí su JetLagToken completo
JETLAG_TOKEN = '''{
  "access_token": "eyJhbGciOiJSUzUxMiIsImN0eSI6IkpXVCIsImlzcyI6IkhFUkUiLCJhaWQiOiJ0OXZ5T0lHQ0pnWmxGVmloWFFpSyIsImlhdCI6MTc3NjE4ODk0OCwiZXhwIjoxNzc2Mjc1MzQ4LCJraWQiOiJqMSJ9.ZXlKaGJHY2lPaUprYVhJaUxDSmxibU1pT2lKQk1qVTJRMEpETFVoVE5URXlJbjAuLnZqa2NRLUJza1dqUUk5b0tiV1cwcUEuaEJHOHBQY09XUWxYTG1ySHRpYzA2cjRHX3VjRmJIMFNVOVhORFNJOXJRdXZ3SVFoSU9CYzFEcDFWb1BxWXNvc1RpTkRza253dDh1SThJY2RuNmNOQ0dJQk1JaXhfRU1wdHBaX1hBcmRNSllxejlHUGI3MlVzbDEtNTZOSWVwbTk0TUFtZEEzRWZ1NC1ROHQ5MHhRd1hRLlNnRElTZmFjNWlOOWpHZWg0cWd2b3JDOEE5QWNsbHZ0eWxhTlc1c3NWY3M.c_2LyIy-b1SxigAQmSBei_Zl-7AMAaj1gFt5wVmdWwK-NvWTy23CtAm-gsya89cwmBb7Hv6fD73uAdrMqqrUCBEsJBoyqiv3JZFqYd2XxSpEv5zbKozhxYplx4E0T59d8SM9Y4egXBRaOKLaFLcwFyzJo_7VxKWNcuwxwa1VdQtaRmkoQQkPjKX9Nt-At6Y6xdOQIqRzsvBRkJ194btWtCXz8MKwYspFjh_GE-UOxMFfWkbpLnoarv46Vbt-FCsIwvCmnQpTdIJ3Qes_r-3rw3ptwvv91eFcoY1gpgmOc4WZ3etbH0aGxSm--22AZdmE005swoO2-KeQIJGoA8h1rA",
  "token_type": "bearer",
  "expires_in": 86399,
  "expires": 1776275286841
}'''

def save_browser_token():
    """Guarda el token del navegador para uso futuro."""
    if not JETLAG_TOKEN:
        print("❌ No hay token configurado")
        print("Pega tu JetLagToken en la variable JETLAG_TOKEN de este script")
        return False
    
    try:
        token_data = json.loads(JETLAG_TOKEN)
        
        # Guardar en formato compatible
        token_dir = '.garth'
        os.makedirs(token_dir, exist_ok=True)
        
        # Crear estructura oauth2 compatible
        oauth2_data = {
            'access_token': token_data.get('access_token'),
            'token_type': token_data.get('token_type', 'Bearer'),
            'expires_in': token_data.get('expires_in', 86399),
        }
        
        with open(f'{token_dir}/oauth2_browser.json', 'w') as f:
            json.dump(oauth2_data, f)
        
        print(f"✅ Token guardado en {token_dir}/oauth2_browser.json")
        print(f"   Expira: {datetime.fromtimestamp(token_data.get('expires', 0)/1000)}")
        return True
        
    except json.JSONDecodeError:
        print("❌ El token no es JSON válido")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_api_call():
    """Prueba hacer una llamada API con el token."""
    if not JETLAG_TOKEN:
        print("❌ Configura JETLAG_TOKEN primero")
        return
    
    try:
        token_data = json.loads(JETLAG_TOKEN)
        access_token = token_data.get('access_token')
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Probar endpoint de perfil
        url = 'https://connect.garmin.com/userprofile-service/userprofile/personalInformation'
        
        print(f"\n🔍 Probando API call...")
        print(f"   URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✅ ÉXITO! API responde correctamente")
            data = response.json()
            print(f"   Usuario: {data.get('displayName', 'N/A')}")
            return True
        elif response.status_code == 401:
            print("❌ Token inválido o expirado (401)")
        elif response.status_code == 429:
            print("❌ Rate limit en API también (429)")
        else:
            print(f"❌ Error {response.status_code}: {response.text[:100]}")
            
    except Exception as e:
        print(f"❌ Error en API call: {e}")
    
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("🔑 USAR TOKEN DEL NAVEGADOR")
    print("=" * 60)
    print()
    print("1. Copia TODO el contenido de JetLagToken del navegador")
    print("2. Pégalo en la variable JETLAG_TOKEN de este script")
    print("3. Ejecuta de nuevo: python use_browser_token.py")
    print()
    
    if JETLAG_TOKEN:
        print("✅ Token configurado")
        save_browser_token()
        test_api_call()
    else:
        print("⚠️  Token no configurado aún")
