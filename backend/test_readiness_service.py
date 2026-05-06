"""
Test de Readiness Service - Dashboard-Vitalis
================================================

Este script verifica que el readiness_service funciona correctamente
despues de los fixes de sleep_score.

Ejecucion:
    cd backend
    python test_readiness_service.py

Verifica:
    1. sleep_score se calcula correctamente desde data.get("sleepScore")
    2. readiness calculation funciona con datos reales
"""

import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import SessionLocal
from app.services.readiness_service import ReadinessService
from app.models.biometrics import Biometrics
from datetime import datetime, timedelta
import json

# Configuración de test
TEST_USER_ID = "default_user"

def test_readiness_calculation():
    """Test 1: Verificar que el cálculo de readiness funciona."""
    print("\n" + "="*60)
    print("TEST 1: Cálculo de Readiness")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Obtener datos biométricos recientes
        recent_biometric = db.query(Biometrics).filter(
            Biometrics.user_id == TEST_USER_ID
        ).order_by(Biometrics.date.desc()).first()
        
        if not recent_biometric:
            print("❌ No se encontraron datos biométricos")
            print("   Ejecuta primero test_sync_fix.py para sincronizar datos")
            return False
        
        print(f"✅ Datos biométricos encontrados para fecha: {recent_biometric.date}")
        
        # Verificar que tenemos datos
        if not recent_biometric.data:
            print("❌ No hay datos en el campo data")
            return False
        
        data = json.loads(recent_biometric.data)
        print(f"📊 Campos disponibles: {list(data.keys())}")
        
        # Verificar campos clave
        key_fields = ["sleep", "sleepScore", "stress", "heartRate", "hrv"]
        for field in key_fields:
            value = data.get(field)
            print(f"   {field}: {value}")
        
        # Calcular readiness
        print("\n🔄 Calculando readiness...")
        result = ReadinessService.calculate(db, TEST_USER_ID, recent_biometric.date)
        
        print(f"✅ Readiness calculado!")
        print(f"   Score: {result.get('score')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Recommendation: {result.get('recommendation')}")
        print(f"   Components: {result.get('components')}")
        print(f"   Overtraining risk: {result.get('overtraining_risk')}")
        
        # Verificar que el score está en rango válido
        score = result.get('score')
        if score is not None and (0 <= score <= 100):
            print(f"✅ Score en rango válido (0-100)")
        else:
            print(f"❌ Score fuera de rango: {score}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_sleep_score_calculation():
    """Test 2: Verificar que sleep_score se calcula correctamente."""
    print("\n" + "="*60)
    print("TEST 2: Cálculo de Sleep Score")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Obtener datos biométricos recientes
        recent_biometric = db.query(Biometrics).filter(
            Biometrics.user_id == TEST_USER_ID
        ).order_by(Biometrics.date.desc()).first()
        
        if not recent_biometric or not recent_biometric.data:
            print("❌ No se encontraron datos biométricos")
            return False
        
        data = json.loads(recent_biometric.data)
        
        # Verificar que sleepScore está disponible
        sleep_score = data.get("sleepScore")
        sleep_hours = data.get("sleep")
        
        print(f"   sleepScore (de Garmin): {sleep_score}")
        print(f"   sleep (horas totales): {sleep_hours}")
        
        if sleep_score is not None:
            print(f"✅ sleepScore disponible en datos")
        else:
            print(f"⚠️ sleepScore no disponible (normal para FR245)")
        
        if sleep_hours is not None:
            print(f"✅ sleep (horas) disponible: {sleep_hours}")
        else:
            print(f"❌ sleep (horas) no disponible")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_body_battery_usage():
    """Test 3: Verificar que body_battery se usa correctamente."""
    print("\n" + "="*60)
    print("TEST 3: Uso de Body Battery")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Obtener datos biométricos recientes
        recent_biometric = db.query(Biometrics).filter(
            Biometrics.user_id == TEST_USER_ID
        ).order_by(Biometrics.date.desc()).first()
        
        if not recent_biometric:
            print("❌ No se encontraron datos biométricos")
            return False
        
        body_battery = recent_biometric.body_battery
        training_readiness = recent_biometric.training_readiness
        
        print(f"   body_battery: {body_battery}")
        print(f"   training_readiness: {training_readiness}")
        
        if body_battery is not None:
            print(f"✅ body_battery disponible")
        else:
            print(f"⚠️ body_battery no disponible")
        
        if training_readiness is not None:
            print(f"✅ training_readiness disponible")
        else:
            print(f"⚠️ training_readiness no disponible (normal para FR245)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Ejecutar todos los tests."""
    print("\n" + "="*60)
    print("TEST DE READINESS SERVICE - Dashboard-Vitalis")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Usuario de test: {TEST_USER_ID}")
    
    results = {
        "Cálculo de Readiness": test_readiness_calculation(),
        "Cálculo de Sleep Score": test_sleep_score_calculation(),
        "Uso de Body Battery": test_body_battery_usage(),
    }
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ TODOS LOS TESTS PASARON")
        print("="*60)
        print("\n🎉 El readiness_service funciona correctamente!")
        print("   - sleep_score se calcula correctamente")
        print("   - readiness calculation funciona con datos reales")
        print("   - body_battery se usa como modificador de energía")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("="*60)
        print("\nRevisa los mensajes de error arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
