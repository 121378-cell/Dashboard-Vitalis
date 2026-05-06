"""
Verificación final del Athletic Intelligence Service
============================================

Este script verifica que el servicio funciona correctamente
y genera un resumen de los resultados.

Ejecución:
    cd backend
    python verify_athletic_intelligence.py
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
    print("VERIFICACIÓN FINAL DEL ATHLETIC INTELLIGENCE SERVICE")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Generar perfil completo
        print("\n🔄 Generando perfil atlético completo...")
        full_profile = AthleticIntelligenceService.get_full_athletic_profile(db, "default_user")
        
        print(f"✅ Perfil atlético completo generado exitosamente")
        
        # Mostrar resultados clave
        print(f"\n📊 RESULTADOS CLAVE:")
        
        identity = full_profile.get("athlete_identity", {})
        print(f"   ✅ Nombre: {identity.get('name')}")
        print(f"   ✅ Edad: {identity.get('age')} años")
        print(f"   ✅ Grupo de edad: {identity.get('age_group')}")
        
        fitness = full_profile.get("fitness_baseline", {})
        print(f"   ✅ Nivel fitness: {fitness.get('fitness_level')}")
        print(f"   ✅ Sesiones/semana: {fitness.get('weekly_sessions_avg'):.2f}")
        print(f"   ✅ FC reposo: {fitness.get('resting_hr_avg'):.1f} bpm")
        print(f"   ✅ Deporte principal: {fitness.get('primary_sport')}")
        
        sleep = full_profile.get("sleep_patterns", {})
        print(f"   ✅ Sueño histórico: {sleep.get('sleep_avg_historical'):.2f} horas")
        print(f"   ✅ Déficit crónico: {sleep.get('chronic_sleep_deficit')}")
        
        recovery = full_profile.get("recovery_capacity", {})
        print(f"   ✅ Body Battery: {recovery.get('body_battery_avg'):.1f}")
        print(f"   ✅ Recovery score: {recovery.get('recovery_score'):.1f}")
        
        risk = full_profile.get("overreaching_risk", {})
        print(f"   ✅ ACWR ratio: {risk.get('acwr_ratio'):.3f}")
        print(f"   ✅ Nivel de riesgo: {risk.get('risk_level')}")
        
        # Verificación de requisitos
        print(f"\n🔍 VERIFICACIÓN DE REQUISITOS:")
        
        checks = [
            ("fitness_level es 'advanced' o 'elite'", fitness.get('fitness_level') in ['advanced', 'elite']),
            ("chronic_sleep_deficit es True", sleep.get('chronic_sleep_deficit') == True),
            ("primary_sport es 'strength_training'", fitness.get('primary_sport') == 'strength_training'),
            ("coach_context_summary es coherente", len(full_profile.get('coach_context_summary', '')) > 50),
            ("body_battery_avg está entre 0 y 100", 0 <= recovery.get('body_battery_avg', 0) <= 100),
            ("recovery_score está entre 0 y 100", 0 <= recovery.get('recovery_score', 0) <= 100),
            ("acwr_ratio está calculado", risk.get('acwr_ratio') is not None),
            ("risk_level es válido", risk.get('risk_level') in ['detraining', 'optimal', 'risk_medium', 'risk_high', 'insufficient_data'])
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if not check_result:
                all_passed = False
        
        print(f"\n💡 CONTEXTO DEL COACH:")
        coach_summary = full_profile.get("coach_context_summary", "")
        print(f"   {coach_summary}")
        
        # Guardar perfil completo
        profile_file = f"athletic_profile_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(full_profile, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Perfil completo guardado en: {profile_file}")
        
        if all_passed:
            print("\n" + "="*60)
            print("✅ TODAS LAS VERIFICACIONES PASARON")
            print("="*60)
            print("\n🎉 El Athletic Intelligence Service está listo para producción!")
            return 0
        else:
            print("\n" + "="*60)
            print("❌ ALGUNAS VERIFICACIONES FALLARON")
            print("="*60)
            return 1
        
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
