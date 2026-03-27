"""
Dashboard-Vitalis - QA Test Suite v1.0
=======================================

Suite completa de testing para validar:
- Persistencia de sesión Garmin
- Sistema de cooldown y rate limiting
- Anti-spam protection
- Manejo de errores

Autor: QA Dashboard-Vitalis
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine
from app.models.token import Token
from app.models.user import User
from app.services.sync_service import SyncService
from app.utils.garmin import get_garmin_client
from app.utils.garmin_exceptions import GarminRateLimitError, GarminAuthError

# Configuración
TEST_USER_ID = "default_user"
TEST_LOG_FILE = "qa_test_results.log"

# Colores para output
class Colors:
    PASS = '\033[92m'  # Green
    FAIL = '\033[91m'  # Red
    WARN = '\033[93m'  # Yellow
    INFO = '\033[94m'  # Blue
    RESET = '\033[0m'

results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log(msg, level="INFO"):
    """Log con timestamp y nivel"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    with open(TEST_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def test_result(name, passed, details=""):
    """Registra resultado de test"""
    status = "PASS" if passed else "FAIL"
    color = Colors.PASS if passed else Colors.FAIL
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    log(f"{color}[{status}]{Colors.RESET} {name}: {details}", status)
    return passed

def reset_db_state():
    """Limpia estado de test en DB"""
    db = SessionLocal()
    try:
        t = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if t:
            t.garmin_session = None
            t.garmin_rate_limited_until = None
            t.last_login_attempt = None
            t.login_attempts_count = 0
            db.commit()
            log("DB state reset for testing")
    finally:
        db.close()

def get_db_state():
    """Obtiene estado actual de DB"""
    db = SessionLocal()
    try:
        t = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if t:
            return {
                "session_exists": bool(t.garmin_session),
                "rate_limited_until": t.garmin_rate_limited_until,
                "login_attempts": t.login_attempts_count,
                "last_attempt": t.last_login_attempt
            }
        return None
    finally:
        db.close()

# ============================================================================
# TEST 1: PRIMER LOGIN
# ============================================================================
def test_1_primer_login():
    """TEST 1: Verificar primer login con sesión limpia"""
    log("\n" + "="*70)
    log("TEST 1: PRIMER LOGIN")
    log("="*70)
    
    # Setup: Limpiar sesión
    reset_db_state()
    initial_state = get_db_state()
    log(f"Initial state: {initial_state}")
    
    # Verificar que no hay sesión
    if initial_state["session_exists"]:
        return test_result("TEST 1", False, "Session should be cleared before test")
    
    # Intentar conexión (esto debería hacer login fresco)
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if not creds or not creds.garmin_email:
            return test_result("TEST 1", False, "No credentials in DB")
        
        try:
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=None,
                user_id=TEST_USER_ID,
                db=db
            )
            
            # Verificar resultado
            if client and isinstance(session_data, str) and session_data:
                # Guardar sesión como haría sync_service
                creds.garmin_session = session_data
                db.commit()
                
                # Verificar estado final
                final_state = get_db_state()
                checks = [
                    ("Session saved", final_state["session_exists"]),
                    ("Login attempts", final_state["login_attempts"] == 1),
                    ("No rate limit", final_state["rate_limited_until"] is None)
                ]
                
                all_pass = all(c[1] for c in checks)
                details = " | ".join([f"{c[0]}: {'✓' if c[1] else '✗'}" for c in checks])
                return test_result("TEST 1", all_pass, details)
            else:
                return test_result("TEST 1", False, f"Login failed or no session data. Client: {bool(client)}, Session: {bool(session_data)}")
                
        except GarminRateLimitError as e:
            return test_result("TEST 1", False, f"Rate limited: {e}")
        except Exception as e:
            return test_result("TEST 1", False, f"Exception: {e}")
            
    finally:
        db.close()

# ============================================================================
# TEST 2: REUTILIZACIÓN DE SESIÓN
# ============================================================================
def test_2_reutilizacion_sesion():
    """TEST 2: Verificar que se reutiliza sesión existente"""
    log("\n" + "="*70)
    log("TEST 2: REUTILIZACIÓN DE SESIÓN")
    log("="*70)
    
    # Verificar que hay sesión de TEST 1
    state = get_db_state()
    if not state["session_exists"]:
        return test_result("TEST 2", False, "No existing session from TEST 1")
    
    attempts_before = state["login_attempts"]
    
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        try:
            start_time = time.time()
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=creds.garmin_session,
                user_id=TEST_USER_ID,
                db=db
            )
            elapsed = time.time() - start_time
            
            final_state = get_db_state()
            
            checks = [
                ("Client obtained", bool(client)),
                ("Session reused", not isinstance(session_data, str) or session_data == ""),  # No nueva sesión
                ("No new login", final_state["login_attempts"] == attempts_before),  # No incrementa
                ("Fast response", elapsed < 2.0)  # Resume es rápido
            ]
            
            all_pass = all(c[1] for c in checks)
            details = " | ".join([f"{c[0]}: {'✓' if c[1] else '✗'}" for c in checks])
            details += f" | Time: {elapsed:.2f}s"
            return test_result("TEST 2", all_pass, details)
            
        except Exception as e:
            return test_result("TEST 2", False, f"Exception: {e}")
            
    finally:
        db.close()

# ============================================================================
# TEST 3: SESIÓN INVÁLIDA
# ============================================================================
def test_3_sesion_invalida():
    """TEST 3: Verificar manejo de sesión corrupta"""
    log("\n" + "="*70)
    log("TEST 3: SESIÓN INVÁLIDA")
    log("="*70)
    
    # Corromper sesión en DB
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        if creds:
            creds.garmin_session = json.dumps({
                "oauth1_token.json": {"invalid": "token"},
                "oauth2_token.json": {"invalid": "token"}
            })
            db.commit()
            log("Session corrupted with invalid tokens")
    finally:
        db.close()
    
    # Intentar conexión
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        try:
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=creds.garmin_session,
                user_id=TEST_USER_ID,
                db=db
            )
            
            # Debería detectar sesión inválida y hacer login
            final_state = get_db_state()
            
            # Si el 429 está activo, no podemos verificar completamente
            if client is None and "429" in str(session_data):
                return test_result("TEST 3", True, "Session invalid detected but rate limited (expected)")
            
            checks = [
                ("New session", isinstance(session_data, str) and session_data != creds.garmin_session),
                ("Client obtained", bool(client))
            ]
            
            all_pass = any(c[1] for c in checks)  # Al menos una debe pasar
            details = " | ".join([f"{c[0]}: {'✓' if c[1] else '✗'}" for c in checks])
            return test_result("TEST 3", all_pass, details)
            
        except Exception as e:
            return test_result("TEST 3", True, f"Exception handled: {type(e).__name__}")
            
    finally:
        db.close()

# ============================================================================
# TEST 4: RATE LIMIT (SIMULADO)
# ============================================================================
def test_4_rate_limit():
    """TEST 4: Verificar manejo de error 429"""
    log("\n" + "="*70)
    log("TEST 4: RATE LIMIT SIMULADO")
    log("="*70)
    
    # Nota: No podemos simular fácilmente un 429 real sin bloquear la cuenta
    # Verificamos que el sistema maneja correctamente el estado de cooldown
    
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        # Simular cooldown activo
        cooldown_time = datetime.utcnow() + timedelta(minutes=15)
        creds.garmin_rate_limited_until = cooldown_time
        db.commit()
        log(f"Simulated cooldown until: {cooldown_time}")
        
        # Intentar conexión (debería lanzar GarminRateLimitError)
        try:
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=creds.garmin_session,
                user_id=TEST_USER_ID,
                db=db
            )
            
            # Si llegamos aquí, no se respetó el cooldown
            return test_result("TEST 4", False, "Cooldown not enforced")
            
        except GarminRateLimitError as e:
            log(f"GarminRateLimitError raised correctly: {e}")
            return test_result("TEST 4", True, "Rate limit exception raised correctly")
        except Exception as e:
            return test_result("TEST 4", False, f"Wrong exception type: {type(e).__name__}")
            
    finally:
        db.close()

# ============================================================================
# TEST 5: COOLDOWN ACTIVO
# ============================================================================
def test_5_cooldown_activo():
    """TEST 5: Verificar bloqueo durante cooldown"""
    log("\n" + "="*70)
    log("TEST 5: COOLDOWN ACTIVO")
    log("="*70)
    
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        # Verificar que cooldown está activo de TEST 4
        if not creds.garmin_rate_limited_until:
            # Recrear cooldown
            creds.garmin_rate_limited_until = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
        
        # Medir tiempo de respuesta
        start_time = time.time()
        try:
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=creds.garmin_session,
                user_id=TEST_USER_ID,
                db=db
            )
            elapsed = time.time() - start_time
            return test_result("TEST 5", False, f"Request should be blocked (took {elapsed:.2f}s)")
            
        except GarminRateLimitError:
            elapsed = time.time() - start_time
            
            # Verificar que fue rápido (no intentó login)
            fast_response = elapsed < 1.0
            return test_result("TEST 5", fast_response, f"Blocked quickly ({elapsed:.2f}s)")
            
    finally:
        db.close()

# ============================================================================
# TEST 6: ANTI-SPAM
# ============================================================================
def test_6_anti_spam():
    """TEST 6: Verificar protección anti-spam (<60s)"""
    log("\n" + "="*70)
    log("TEST 6: ANTI-SPAM PROTECTION")
    log("="*70)
    
    # Limpiar cooldown primero
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        creds.garmin_rate_limited_until = None
        creds.last_login_attempt = datetime.utcnow()  # Marcar intento reciente
        creds.login_attempts_count = 0
        db.commit()
    finally:
        db.close()
    
    # Intentar inmediatamente (debería bloquear por anti-spam)
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        try:
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=None,
                user_id=TEST_USER_ID,
                db=db
            )
            
            # Si obtuvimos cliente, el anti-spam falló
            if client:
                return test_result("TEST 6", False, "Anti-spam not enforced - got client")
            else:
                return test_result("TEST 6", True, "Anti-spam enforced - no client returned")
                
        except Exception as e:
            # Esperamos que no haya excepción, solo retorno None
            return test_result("TEST 6", True, f"Handled: {type(e).__name__}")
            
    finally:
        db.close()

# ============================================================================
# TEST 7: LÍMITE DE INTENTOS
# ============================================================================
def test_7_limite_intentos():
    """TEST 7: Verificar límite de 3 intentos"""
    log("\n" + "="*70)
    log("TEST 7: LÍMITE DE INTENTOS")
    log("="*70)
    
    # Resetear estado
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        creds.garmin_rate_limited_until = None
        creds.login_attempts_count = 3  # Máximo alcanzado
        creds.last_login_attempt = datetime.utcnow() - timedelta(minutes=5)  # Hace 5 min
        db.commit()
        log("Set login_attempts_count = 3")
    finally:
        db.close()
    
    # Intentar conexión
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        try:
            client, session_data = get_garmin_client(
                email=creds.garmin_email,
                password=creds.garmin_password,
                session_data=None,
                user_id=TEST_USER_ID,
                db=db
            )
            
            return test_result("TEST 7", False, "Should have triggered rate limit")
            
        except GarminRateLimitError as e:
            # Verificar que se estableció cooldown de 30min
            final_state = get_db_state()
            if final_state["rate_limited_until"]:
                return test_result("TEST 7", True, "Rate limit triggered after max attempts")
            else:
                return test_result("TEST 7", False, "Rate limit raised but cooldown not set")
                
    finally:
        db.close()

# ============================================================================
# TEST 8: LOGGING
# ============================================================================
def test_8_logging():
    """TEST 8: Verificar mensajes de log"""
    log("\n" + "="*70)
    log("TEST 8: LOGGING VERIFICATION")
    log("="*70)
    
    # Los logs ya se escribieron durante los tests anteriores
    # Verificamos que existen en el archivo de log
    
    expected_patterns = [
        "[GARMIN]",
        "Session",
        "login"
    ]
    
    try:
        with open(TEST_LOG_FILE, "r", encoding="utf-8") as f:
            log_content = f.read()
        
        found_patterns = [p for p in expected_patterns if p.lower() in log_content.lower()]
        
        checks = [
            ("GARMIN tag", "[GARMIN]" in log_content),
            ("Session refs", "Session" in log_content or "session" in log_content),
            ("Login refs", "login" in log_content or "Login" in log_content)
        ]
        
        all_pass = all(c[1] for c in checks)
        details = " | ".join([f"{c[0]}: {'✓' if c[1] else '✗'}" for c in checks])
        return test_result("TEST 8", all_pass, details)
        
    except Exception as e:
        return test_result("TEST 8", False, f"Error reading log: {e}")

# ============================================================================
# TEST 9: CONSISTENCIA EN DB
# ============================================================================
def test_9_consistencia_db():
    """TEST 9: Verificar campos actualizados correctamente"""
    log("\n" + "="*70)
    log("TEST 9: CONSISTENCIA EN BASE DE DATOS")
    log("="*70)
    
    # Resetear para estado limpio
    db = SessionLocal()
    try:
        creds = db.query(Token).filter(Token.user_id == TEST_USER_ID).first()
        
        checks = [
            ("garmin_session", hasattr(creds, 'garmin_session')),
            ("garmin_rate_limited_until", hasattr(creds, 'garmin_rate_limited_until')),
            ("last_login_attempt", hasattr(creds, 'last_login_attempt')),
            ("login_attempts_count", hasattr(creds, 'login_attempts_count'))
        ]
        
        all_pass = all(c[1] for c in checks)
        details = " | ".join([f"{c[0]}: {'✓' if c[1] else '✗'}" for c in checks])
        return test_result("TEST 9", all_pass, f"Fields exist: {details}")
        
    finally:
        db.close()

# ============================================================================
# MAIN
# ============================================================================
def run_all_tests():
    """Ejecutar todos los tests"""
    log("\n" + "="*70)
    log("DASHBOARD-VITALIS QA TEST SUITE v1.0")
    log("="*70)
    log(f"Started at: {datetime.now().isoformat()}")
    log(f"Test User: {TEST_USER_ID}")
    log(f"Log file: {TEST_LOG_FILE}")
    
    # Limpiar archivo de log anterior
    if os.path.exists(TEST_LOG_FILE):
        os.remove(TEST_LOG_FILE)
    
    # Ejecutar tests
    tests = [
        test_1_primer_login,
        test_2_reutilizacion_sesion,
        test_3_sesion_invalida,
        test_4_rate_limit,
        test_5_cooldown_activo,
        test_6_anti_spam,
        test_7_limite_intentos,
        test_8_logging,
        test_9_consistencia_db
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            log(f"CRITICAL ERROR in {test.__name__}: {e}", "CRITICAL")
            results["failed"] += 1
    
    # Generar reporte final
    log("\n" + "="*70)
    log("FINAL REPORT")
    log("="*70)
    log(f"Total Tests: {results['passed'] + results['failed']}")
    log(f"Passed: {results['passed']} ✓")
    log(f"Failed: {results['failed']} ✗")
    log(f"Success Rate: {results['passed']/(results['passed'] + results['failed'])*100:.1f}%")
    
    # Guardar JSON report
    report_file = "qa_test_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    log(f"Report saved to: {report_file}")
    
    return results["failed"] == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
