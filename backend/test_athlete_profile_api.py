"""
Test del Endpoint API del Perfil de Atleta
============================================

Este script verifica que el endpoint API del perfil de atleta
funciona correctamente y está disponible para el coach de Atlas.

Ejecución:
    cd backend
    python test_athlete_profile_api.py
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
    print("TEST DEL ENDPOINT API DEL PERFIL DE ATLETA")
    print("="*60)
    
    base_url = "http://localhost:8000/api/v1"
    
    # Test 1: Obtener perfil del atleta
    print("\n🔄 Test 1: Obtener perfil del atleta...")
    try:
        response = requests.get(f"{base_url}/athlete-profile?user_id=default_user")
        
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ Perfil obtenido exitosamente")
            print(f"   Usuario: {profile.get('user_id')}")
            print(f"   Registros: {profile.get('total_biometrics_records')} días")
            print(f"   Nivel de actividad: {profile.get('activity_level')}")
            print(f"   Condición física: {profile.get('fitness_level')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Asegúrate de que el servidor backend esté corriendo")
        return 1
    
    # Test 2: Obtener contexto para el coach
    print("\n🔄 Test 2: Obtener contexto para el coach...")
    try:
        response = requests.get(f"{base_url}/athlete-profile/coach-context?user_id=default_user")
        
        if response.status_code == 200:
            context = response.json()
            print(f"✅ Contexto obtenido exitosamente")
            
            athlete_profile = context.get("athlete_profile", {})
            print(f"   Perfil del atleta: {athlete_profile.get('activity_level')}")
            
            recommendations = context.get("coach_recommendations", {})
            print(f"   Recomendación de entrenamiento: {recommendations.get('training_intensity')}")
            
            insights = context.get("key_insights", [])
            print(f"   Insights clave: {len(insights)} insights generados")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print(f"\n✅ TODOS LOS TESTS PASARON")
    print(f"\n🎉 EL COACH DE ATLAS PUEDE ACCEDER A:")
    print(f"   - Perfil del atleta vía API: GET /api/v1/athlete-profile")
    print(f"   - Contexto completo vía API: GET /api/v1/athlete-profile/coach-context")
    print(f"   - Estadísticas históricas detalladas")
    print(f"   - Recomendaciones personalizadas")
    print(f"   - Insights clave para toma de decisiones")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
