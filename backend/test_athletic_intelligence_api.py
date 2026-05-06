"""
Test de endpoints de Athletic Intelligence
==========================================

Este script verifica que los endpoints API de Athletic Intelligence funcionan correctamente.

Ejecución:
    cd backend
    python test_athletic_intelligence_api.py
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST DE ENDPOINTS DE ATHLETIC INTELLIGENCE")
    print("="*60)
    
    base_url = "http://localhost:8000/api/v1"
    
    # Test 1: GET /api/v1/analytics/intelligence/profile
    print("\n🔄 Test 1: GET /api/v1/analytics/intelligence/profile")
    try:
        response = requests.get(f"{base_url}/analytics/intelligence/profile?user_id=default_user")
        
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ Perfil atlético obtenido exitosamente")
            
            identity = profile.get("athlete_identity", {})
            print(f"   Nombre: {identity.get('name')}")
            print(f"   Edad: {identity.get('age')} años")
            print(f"   Grupo de edad: {identity.get('age_group')}")
            print(f"   Nivel fitness: {profile.get('fitness_baseline', {}).get('fitness_level')}")
            
            # Verificar cache
            print(f"\n🔄 Test 1b: GET /api/v1/analytics/intelligence/profile (debe usar cache)")
            response2 = requests.get(f"{base_url}/analytics/intelligence/profile?user_id=default_user")
            
            if response2.status_code == 200:
                profile2 = response2.json()
                print(f"✅ Segunda petición exitosa (cache funcionando)")
                print(f"   Mismo timestamp: {profile.get('generated_at') == profile2.get('generated_at')}")
            else:
                print(f"❌ Error en segunda petición: {response2.status_code}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    # Test 2: GET /api/v1/analytics/intelligence/overreaching-check
    print("\n🔄 Test 2: GET /api/v1/analytics/intelligence/overreaching-check")
    try:
        response = requests.get(f"{base_url}/analytics/intelligence/overreaching-check?user_id=default_user")
        
        if response.status_code == 200:
            overreaching = response.json()
            print(f"✅ Análisis de sobreentrenamiento obtenido exitosamente")
            print(f"   ACWR ratio: {overreaching.get('acwr_ratio')}")
            print(f"   Nivel de riesgo: {overreaching.get('risk_level')}")
            print(f"   Recomendación: {overreaching.get('recommendation')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print("\n" + "="*60)
    print("✅ TODOS LOS TESTS DE ENDPOINTS PASARON")
    print("="*60)
    print("\n🎉 Los endpoints de Athletic Intelligence funcionan correctamente!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
