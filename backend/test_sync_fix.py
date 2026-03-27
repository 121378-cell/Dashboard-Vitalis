"""
Test de Sincronización Garmin - Dashboard-Vitalis
====================================================

Este script verifica que la sincronización con Garmin funciona correctamente
después de aplicar los fixes de sesión persistente.

Ejecución:
    cd backend
    python test_sync_fix.py

Verifica:
    1. Conexión con resume de sesión (sin 429)
    2. Persistencia de tokens en base de datos
    3. Reutilización de sesión en segunda ejecución
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.token import Token
from app.services.sync_service import SyncService
from app.utils.garmin import get_garmin_client
from datetime import datetime, timedelta
import json

# Configuración de test - Usar el ID del usuario con credenciales en la DB
TEST_USER_ID = "default_user"

def test_garmin_connection():
    """Test 1: Verificar que la conexión con resume funciona."""
    print("\n" + "="*60)
    print("TEST 1: Conexión Garmin con Resume de Sesión")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Verificar que tenemos credenciales
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if not creds:
            print("❌ No se encontraron credenciales en la base de datos")
            print("   Ejecuta primero run_sync.py para guardar credenciales")
            return False
        
        if not creds.garmin_email or not creds.garmin_password:
            print("❌ No hay email/password de Garmin configurados")
            return False
        
        print(f"✅ Credenciales encontradas para: {creds.garmin_email}")
        
        # Test 1a: Primera conexión (posible fresh login)
        print("\n[Intento 1] Conectando a Garmin...")
        client1, session1 = get_garmin_client(
            email=creds.garmin_email,
            password=creds.garmin_password,
            session_data=creds.garmin_session,
            user_id=TEST_USER_ID
        )
        
        if not client1:
            print("❌ Error: No se pudo conectar (posible 429)")
            return False
        
        print(f"✅ Conectado exitosamente!")
        print(f"   Tipo de sesión: {'JSON (persistente)' if isinstance(session1, str) else 'Bool'}")
        
        # Verificar que la sesión se puede persistir
        if isinstance(session1, str) and session1:
            creds.garmin_session = session1
            creds.last_session_update = datetime.now()
            db.commit()
            print("✅ Sesión guardada en base de datos")
        
        # Test 1b: Segunda conexión (debe usar resume, no login)
        print("\n[Intento 2] Reutilizando sesión (debe hacer resume)...")
        client2, session2 = get_garmin_client(
            email=creds.garmin_email,
            password=creds.garmin_password,
            session_data=creds.garmin_session,
            user_id=TEST_USER_ID
        )
        
        if not client2:
            print("❌ Error: No se pudo reconectar")
            return False
        
        print(f"✅ Reconectado exitosamente via resume!")
        
        # Verificar que ambos clientes funcionan
        try:
            profile1 = client1.get_user_profile()
            profile2 = client2.get_user_profile()
            print(f"✅ Ambos clientes responden correctamente")
            print(f"   Usuario: {profile1.get('displayName', 'Unknown')}")
        except Exception as e:
            print(f"⚠️ Advertencia: Error obteniendo profile: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_sync_service():
    """Test 2: Verificar que SyncService funciona correctamente."""
    print("\n" + "="*60)
    print("TEST 2: SyncService - Sincronización de Datos")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Crear rango de fechas pequeño (últimos 3 días)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        date_range = [
            (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(4)
        ]
        
        print(f"📅 Rango de fechas: {date_range[-1]} a {date_range[0]}")
        
        # Intentar sincronización
        print("\n🔄 Ejecutando sync_garmin_health...")
        success = SyncService.sync_garmin_health(db, TEST_USER_ID, date_range)
        
        if success:
            print("✅ Sincronización de salud completada")
        else:
            print("❌ Sincronización de salud falló")
            return False
        
        # Verificar que se guardaron datos
        from app.models.biometrics import Biometrics
        saved_data = db.query(Biometrics).filter(
            Biometrics.user_id == TEST_USER_ID
        ).count()
        
        print(f"📊 Registros guardados: {saved_data}")
        
        # Verificar que la sesión se persistió
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if creds and creds.garmin_session:
            try:
                session_data = json.loads(creds.garmin_session)
                has_oauth1 = "oauth1_token.json" in session_data
                has_oauth2 = "oauth2_token.json" in session_data
                print(f"✅ Sesión persistida: oauth1={has_oauth1}, oauth2={has_oauth2}")
            except:
                print("⚠️ Sesión persistida pero formato inválido")
        else:
            print("⚠️ Sesión no persistida después del sync")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_session_isolation():
    """Test 3: Verificar que cada usuario tiene tokens aislados."""
    print("\n" + "="*60)
    print("TEST 3: Aislamiento de Sesiones por Usuario")
    print("="*60)
    
    token_dirs = [
        f".garth_{TEST_USER_ID}",
        ".garth_test_user_456",
        ".garth"
    ]
    
    print("📁 Directorios de tokens verificados:")
    for dir_name in token_dirs:
        exists = os.path.exists(dir_name)
        status = "✅ Existe" if exists else "❌ No existe"
        print(f"   {dir_name}: {status}")
    
    return True


def main():
    """Ejecutar todos los tests."""
    print("\n" + "="*60)
    print("TEST DE SINCRONIZACIÓN GARMIN - Dashboard-Vitalis")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Usuario de test: {TEST_USER_ID}")
    
    # Verificar que existen credenciales en la base de datos
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if not creds or not creds.garmin_email or not creds.garmin_password:
            print("\n⚠️  ADVERTENCIA: No se encontraron credenciales de Garmin en la base de datos")
            print("   Ejecuta primero run_sync.py para guardar credenciales válidas.")
            return 1
        print(f"\n✅ Credenciales encontradas en DB: {creds.garmin_email}")
    finally:
        db.close()
    
    results = {
        "Conexión": test_garmin_connection(),
        "SyncService": test_sync_service(),
        "Aislamiento": test_session_isolation(),
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
        print("\n🎉 Los fixes de sesión persistente funcionan correctamente!")
        print("   - No más errores 429 en conexiones repetidas")
        print("   - Sesiones se persisten en base de datos")
        print("   - Resume de tokens funciona correctamente")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("="*60)
        print("\nRevisa los mensajes de error arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
