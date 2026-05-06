"""
Test del Servicio de Perfil de Atleta
======================================

Este script verifica que el servicio de perfil de atleta funciona
correctamente y genera el contexto completo para el coach de Atlas.

Ejecución:
    cd backend
    python test_athlete_profile_service.py
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
from app.services.athlete_profile_service import AthleteProfileService
import json

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST DEL SERVICIO DE PERFIL DE ATLETA")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Obtener perfil del atleta
        print("\n🔄 Obteniendo perfil del atleta...")
        profile = AthleteProfileService.get_profile(db, "default_user")
        
        print(f"✅ Perfil generado exitosamente")
        print(f"   Usuario: {profile.user_id}")
        print(f"   Registros: {profile.total_biometrics_records} días")
        print(f"   Actividades: {profile.total_activities}")
        print(f"   Rango: {profile.oldest_date} a {profile.newest_date}")
        
        print(f"\n📊 ESTADÍSTICAS HISTÓRICAS:")
        print(f"   Sueño: {profile.sleep.average:.2f} ± {profile.sleep.std:.2f} horas ({profile.sleep.days_with_data} días)")
        print(f"   Pasos: {profile.steps.average:.0f} ± {profile.steps.std:.0f} pasos ({profile.steps.days_with_data} días)")
        print(f"   HRV: {profile.hrv.average:.1f} ± {profile.hrv.std:.1f} ms ({profile.hrv.days_with_data} días)")
        print(f"   Estrés: {profile.stress.average:.1f} ± {profile.stress.std:.1f}/100 ({profile.stress.days_with_data} días)")
        print(f"   FC reposo: {profile.resting_heart_rate.average:.1f} ± {profile.resting_heart_rate.std:.1f} bpm ({profile.resting_heart_rate.days_with_data} días)")
        print(f"   Body Battery: {profile.body_battery.average:.1f} ({profile.body_battery.days_with_data} días)")
        
        print(f"\n🏃 PERFIL DE ATLETA:")
        print(f"   Nombre: {profile.name}")
        print(f"   Fecha de nacimiento: {profile.birth_date}")
        print(f"   Edad: {profile.age} años")
        print(f"   Grupo de edad: {profile.age_group if hasattr(profile, 'age_group') else 'N/A'}")
        print(f"   Nivel de actividad: {profile.activity_level}")
        print(f"   Calidad de sueño: {profile.sleep_quality}")
        print(f"   Capacidad de recuperación: {profile.recovery_capacity}")
        print(f"   Nivel de estrés: {profile.stress_level}")
        print(f"   Nivel de condición física: {profile.fitness_level}")
        
        print(f"\n🔍 PATRONES DETECTADOS:")
        print(f"   Consistencia de sueño: {profile.patterns.get('sleep_consistency', 0):.0f}%")
        print(f"   Consistencia de actividad: {profile.patterns.get('activity_consistency', 0):.0f}%")
        print(f"   Tendencia de recuperación: {profile.patterns.get('recovery_trend', 'stable')}")
        
        print(f"\n🔄 READINESS ACTUAL:")
        if profile.current_readiness:
            print(f"   Score: {profile.current_readiness.get('score')}")
            print(f"   Status: {profile.current_readiness.get('status')}")
            print(f"   Recomendación: {profile.current_readiness.get('recommendation')}")
        else:
            print(f"   No disponible")
        
        # Obtener contexto para el coach
        print(f"\n🤖 OBTENIENDO CONTEXTO PARA EL COACH DE ATLAS...")
        coach_context = AthleteProfileService.get_coach_context(db, "default_user")
        
        print(f"✅ Contexto generado exitosamente")
        
        print(f"\n💡 RECOMENDACIONES DEL COACH:")
        recommendations = coach_context.get("coach_recommendations", {})
        print(f"   Intensidad de entrenamiento: {recommendations.get('training_intensity')}")
        print(f"   Enfoque de recuperación: {recommendations.get('recovery_focus')}")
        print(f"   Optimización del sueño: {recommendations.get('sleep_optimization')}")
        print(f"   Manejo de estrés: {recommendations.get('stress_management')}")
        print(f"   Enfoque apropiado para edad: {recommendations.get('age_appropriate_focus')}")
        
        print(f"\n👴 CONSIDERACIONES DE ENVEJECIMIENTO:")
        aging_considerations = coach_context.get("aging_considerations", {})
        print(f"   Edad: {aging_considerations.get('age')} años")
        print(f"   Grupo de edad: {aging_considerations.get('age_group')}")
        print(f"   Necesidades de recuperación: {aging_considerations.get('recovery_needs')}")
        print(f"   Prioridad de prevención de lesiones: {aging_considerations.get('injury_prevention_priority')}")
        print(f"   Adaptación de entrenamiento: {aging_considerations.get('training_adaptation')}")
        print(f"   Áreas de enfoque: {', '.join(aging_considerations.get('focus_areas', []))}")
        
        print(f"\n🎯 INSIGHTS CLAVE:")
        insights = coach_context.get("key_insights", [])
        for i, insight in enumerate(insights, 1):
            print(f"   {i}. {insight}")
        
        # Guardar contexto completo en archivo
        context_file = f"atlas_coach_context_default_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(coach_context, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Contexto completo guardado en: {context_file}")
        
        print(f"\n✅ EL COACH DE ATLAS AHORA TIENE ACCESO A:")
        print(f"   - Perfil completo del atleta")
        print(f"   - Estadísticas históricas detalladas")
        print(f"   - Patrones de comportamiento")
        print(f"   - Recomendaciones personalizadas")
        print(f"   - Insights clave para toma de decisiones")
        
        print(f"\n🎉 EL CORAZÓN DE ATLAS ESTÁ LISTO PARA COACHear!")
        
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
