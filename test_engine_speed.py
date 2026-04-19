import time
from app.db.session import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.services.context_service import ContextService

def test_speed():
    db = SessionLocal()
    user_id = "default_user"
    
    print("--- TEST DE VELOCIDAD DE MOTOR ATLAS ---")
    
    start = time.time()
    print("Calculando Readiness y ACWR...")
    coach_context = ContextService.get_full_coach_context(db, user_id)
    end = time.time()
    
    print(f"\nTiempo de respuesta del motor: {end - start:.2f} segundos.")
    print("\n--- RESUMEN GENERADO PARA LA IA ---")
    print(coach_context[:500] + "...")
    
    db.close()

if __name__ == "__main__":
    test_speed()
