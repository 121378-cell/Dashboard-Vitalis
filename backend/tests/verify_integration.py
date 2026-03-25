import requests
import sys
import json

BASE_URL = "http://localhost:8001"
API_V1 = f"{BASE_URL}/api/v1"

def run_test(name, func):
    print(f"--- Running Test: {name} ---")
    try:
        func()
        print(f"✓ {name} PASSED\n")
    except AssertionError as e:
        print(f"❌ {name} FAILED: Assertion Error")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {name} ERROR: {str(e)}")
        sys.exit(1)

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}, Body: {r.text}")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_auth_status():
    r = requests.get(f"{API_V1}/auth/status", params={"user_id": "default_user"})
    print(f"Status: {r.status_code}, Body: {r.text}")
    assert r.status_code == 200

def test_biometrics_fallback():
    # TEST WITHOUT TRAILING SLASH
    r = requests.get(f"{API_V1}/biometrics", params={"user_id": "default_user"})
    print(f"Status: {r.status_code}, Body: {r.text}")
    assert r.status_code == 200
    data = r.json()
    assert data.get("source") == "demo"

def test_sync_hevy_mock():
    r = requests.post(f"{API_V1}/sync/hevy", params={"user_id": "default_user"})
    print(f"Status: {r.status_code}, Body: {r.text}")
    assert r.status_code == 200

if __name__ == "__main__":
    run_test("Health", test_health)
    run_test("Auth Status", test_auth_status)
    run_test("Biometrics (No Trailing Slash)", test_biometrics_fallback)
    run_test("Hevy Sync (Mock)", test_sync_hevy_mock)
    print("ALL INTEGRATION TESTS PASSED ✓")
