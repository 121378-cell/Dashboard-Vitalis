"""
Limpiar planes existentes y generar uno nuevo
============================================

Este script limpia los planes existentes y genera uno nuevo para testing.

Ejecución:
    cd backend
    python clean_and_generate_plan.py
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
from app.services.training_plan_service import TrainingPlanService
from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession
from datetime import date, timedelta

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("LIMPIAR PLANES EXISTENTES Y GENERAR UNO NUEVO")
    print("="*60)
    
    db = SessionLocal()
    try:
        user_id = "default_user"
        
        # Limpiar planes existentes
        print("\n🔄 Limpiando planes existentes...")
        
        # Eliminar sesiones
        deleted_sessions = db.query(AdaptivePlannedSession).filter(
            AdaptivePlannedSession.plan_id.in_(
                db.query(AdaptiveTrainingPlan.id).filter(
                    AdaptiveTrainingPlan.user_id == user_id
                )
            )
        ).delete(synchronize_session=False)
        
        print(f"   Sesiones eliminadas: {deleted_sessions}")
        
        # Eliminar planes
        deleted_plans = db.query(AdaptiveTrainingPlan).filter(
            AdaptiveTrainingPlan.user_id == user_id
        ).delete(synchronize_session=False)
        
        print(f"   Planes eliminados: {deleted_plans}")
        
        db.commit()
        
        print(f"✅ Limpieza completada")
        
        # Generar nuevo plan
        print("\n🔄 Generando nuevo plan...")
        week_start = date.today() - timedelta(days=date.today().weekday())
        goal = "Mejorar fuerza general y mantener cardio"
        
        plan = TrainingPlanService.generate_weekly_plan(
            db=db,
            user_id=user_id,
            goal=goal,
            week_start=week_start
        )
        
        print(f"✅ Plan generado exitosamente")
        print(f"   Plan ID: {plan.get('plan_id')}")
        print(f"   Semana: {plan.get('week_start')} al {plan.get('week_end')}")
        print(f"   Objetivo semanal: {plan.get('weekly_goal')}")
        print(f"   Razonamiento: {plan.get('reasoning')}")
        print(f"   Total minutos: {plan.get('total_planned_minutes')}")
        print(f"   Sesiones: {len(plan.get('sessions', []))}")
        
        # Mostrar sesiones
        if len(plan.get('sessions', [])) > 0:
            print(f"\n   Sesiones:")
            for session in plan.get('sessions', []):
                print(f"      {session.get('day_of_week')} ({session.get('date')}): {session.get('title')} - {session.get('session_type')} - {session.get('duration_minutes')} min")
        else:
            print(f"\n   ⚠️  No hay sesiones en el plan")
        
        # Verificar plan actual
        print("\n🔄 Verificando plan actual...")
        current_plan = TrainingPlanService.get_current_plan(db, user_id)
        
        if current_plan:
            print(f"✅ Plan actual obtenido")
            print(f"   Plan ID: {current_plan.get('plan_id')}")
            print(f"   Estado: {current_plan.get('status')}")
            print(f"   Progreso: {current_plan.get('progress', {}).get('completed', 0)}/{current_plan.get('progress', {}).get('total', 0)}")
            
            plan_data = current_plan.get('plan', {})
            print(f"   Objetivo semanal: {plan_data.get('weekly_goal')}")
            print(f"   Razonamiento: {plan_data.get('reasoning')}")
            print(f"   Total minutos: {plan_data.get('total_planned_minutes')}")
            print(f"   Sesiones: {len(plan_data.get('sessions', []))}")
            
            if len(plan_data.get('sessions', [])) > 0:
                print(f"\n   Sesiones del plan actual:")
                for session in plan_data.get('sessions', []):
                    print(f"      {session.get('day_of_week')} ({session.get('date')}): {session.get('title')} - {session.get('session_type')} - {session.get('duration_minutes')} min")
            else:
                print(f"\n   ⚠️  No hay sesiones en el plan actual")
        else:
            print(f"❌ No hay plan actual")
        
        print("\n" + "="*60)
        print("✅ LIMPIEZA Y GENERACIÓN COMPLETADAS")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
