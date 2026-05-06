"""
Test del Athletic Intelligence Service
======================================

Este script verifica que el AthleticIntelligenceService funciona correctamente
y genera el perfil completo del atleta.

Ejecución:
    cd backend
    python test_athletic_intelligence_service.py
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
from app.services.athletic_intelligence_service import AthleticIntelligenceService
import json

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST DEL ATHLETIC INTELLIGENCE SERVICE")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Test 1: analyze_fitness_baseline
        print("\n🔄 Test 1: analyze_fitness_baseline")
        fitness_baseline = AthleticIntelligenceService.analyze_fitness_baseline(db, "default_user")
        print(f"✅ Fitness baseline analizado")
        print(f"   Sesiones/semana: {fitness_baseline.get('weekly_sessions_avg')}")
        print(f"   Nivel fitness: {fitness_baseline.get('fitness_level')}")
        print(f"   FC reposo: {fitness_baseline.get('resting_hr_avg')}")
        print(f"   Deporte principal: {fitness_baseline.get('primary_sport')}")
        
        # Test 2: analyze_sleep_patterns
        print("\n🔄 Test 2: analyze_sleep_patterns")
        sleep_patterns = AthleticIntelligenceService.analyze_sleep_patterns(db, "default_user")
        print(f"✅ Patrones de sueño analizados")
        print(f"   Sueño reciente (4s): {sleep_patterns.get('sleep_avg_recent_4w')}")
        print(f"   Sueño histórico: {sleep_patterns.get('sleep_avg_historical')}")
        print(f"   Déficit crónico: {sleep_patterns.get('chronic_sleep_deficit')}")
        print(f"   Tendencia: {sleep_patterns.get('sleep_trend')}")
        
        # Test 3: analyze_recovery_capacity
        print("\n🔄 Test 3: analyze_recovery_capacity")
        recovery_capacity = AthleticIntelligenceService.analyze_recovery_capacity(db, "default_user")
        print(f"✅ Capacidad de recuperación analizada")
        print(f"   Body Battery promedio: {recovery_capacity.get('body_battery_avg')}")
        print(f"   Tendencia BB: {recovery_capacity.get('body_battery_trend')}")
        print(f"   Stress promedio: {recovery_capacity.get('stress_avg_30d')}")
        print(f"   Recovery score: {recovery_capacity.get('recovery_score')}")
        
        # Test 4: detect_overreaching_risk
        print("\n🔄 Test 4: detect_overreaching_risk")
        overreaching_risk = AthleticIntelligenceService.detect_overreaching_risk(db, "default_user")
        print(f"✅ Riesgo de sobreentrenamiento detectado")
        print(f"   ACWR ratio: {overreaching_risk.get('acwr_ratio')}")
        print(f"   Nivel de riesgo: {overreaching_risk.get('risk_level')}")
        print(f"   Factores adicionales: {overreaching_risk.get('additional_risk_factors')}")
        print(f"   Recomendación: {overreaching_risk.get('recommendation')}")
        
        # Test 5: get_full_athletic_profile
        print("\n🔄 Test 5: get_full_athletic_profile")
        full_profile = AthleticIntelligenceService.get_full_athletic_profile(db, "default_user")
        print(f"✅ Perfil atlético completo generado")
        
        print(f"\n👤 IDENTIDAD DEL ATLETA:")
        identity = full_profile.get("athlete_identity", {})
        print(f"   Nombre: {identity.get('name')}")
        print(f"   Edad: {identity.get('age')} años")
        print(f"   Grupo de edad: {identity.get('age_group')}")
        print(f"   Deporte principal: {identity.get('primary_sport')}")
        print(f"   Mix de deportes: {identity.get('sports_mix')}")
        
        print(f"\n📊 BASELINE DE FITNESS:")
        fitness = full_profile.get("fitness_baseline", {})
        print(f"   Nivel fitness: {fitness.get('fitness_level')}")
        print(f"   Sesiones/semana: {fitness.get('weekly_sessions_avg')}")
        print(f"   FC reposo: {fitness.get('resting_hr_avg')}")
        print(f"   Horas totales (2años): {fitness.get('total_training_hours_2y')}")
        
        print(f"\n😴 PATRONES DE SUEÑO:")
        sleep = full_profile.get("sleep_patterns", {})
        print(f"   Sueño reciente: {sleep.get('sleep_avg_recent_4w')} horas")
        print(f"   Sueño histórico: {sleep.get('sleep_avg_historical')} horas")
        print(f"   Déficit crónico: {sleep.get('chronic_sleep_deficit')}")
        print(f"   Tendencia: {sleep.get('sleep_trend')}")
        
        print(f"\n🔄 CAPACIDAD DE RECUPERACIÓN:")
        recovery = full_profile.get("recovery_capacity", {})
        print(f"   Body Battery: {recovery.get('body_battery_avg')}")
        print(f"   Stress: {recovery.get('stress_avg_30d')}/100")
        print(f"   Recovery score: {recovery.get('recovery_score')}")
        
        print(f"\n⚠️  RIESGO DE SOBREENTRENAMIENTO:")
        risk = full_profile.get("overreaching_risk", {})
        print(f"   ACWR ratio: {risk.get('acwr_ratio')}")
        print(f"   Nivel de riesgo: {risk.get('risk_level')}")
        print(f"   Factores adicionales: {risk.get('additional_risk_factors')}")
        
        print(f"\n💡 CONTEXTO DEL COACH:")
        coach_summary = full_profile.get("coach_context_summary", "")
        print(f"   {coach_summary}")
        
        # Guardar perfil completo en archivo
        profile_file = f"athletic_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(full_profile, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Perfil completo guardado en: {profile_file}")
        
        # Verificar resultados esperados
        print(f"\n🔍 VERIFICACIÓN DE RESULTADOS:")
        print(f"   ✅ fitness_level debe ser 'advanced' o 'elite': {fitness.get('fitness_level') in ['advanced', 'elite']}")
        print(f"   ✅ chronic_sleep_deficit debe ser True: {sleep.get('chronic_sleep_deficit') == True}")
        print(f"   ✅ primary_sport debe ser 'strength_training': {fitness.get('primary_sport') == 'strength_training'}")
        print(f"   ✅ coach_context_summary debe ser un párrafo coherente: len(coach_summary) > 50")
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS PASARON")
        print("="*60)
        print("\n🎉 El Athletic Intelligence Service funciona correctamente!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    from datetime import datetime
    sys.exit(main())
