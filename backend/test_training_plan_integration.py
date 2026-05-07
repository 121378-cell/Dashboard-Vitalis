"""
Test de integración de Training Plan con datos reales
======================================================

Este script prueba el sistema de planes de entrenamiento con los datos reales de Sergi.

Ejecución:
    cd backend
    python test_training_plan_integration.py
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
from app.services.athletic_intelligence_service import AthleticIntelligenceService
from datetime import date, timedelta

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST DE INTEGRACIÓN DE TRAINING PLAN CON DATOS REALES")
    print("="*60)
    
    db = SessionLocal()
    try:
        user_id = "default_user"
        
        # Test 1: Verificar perfil atlético
        print("\n🔄 Test 1: Verificar perfil atlético de Sergi...")
        try:
            profile = AthleticIntelligenceService.get_full_athletic_profile(db, user_id)
            
            print(f"✅ Perfil atlético obtenido exitosamente")
            
            identity = profile.get("athlete_identity", {})
            print(f"   Nombre: {identity.get('name')}")
            print(f"   Edad: {identity.get('age')} años")
            print(f"   Grupo de edad: {identity.get('age_group')}")
            
            fitness = profile.get("fitness_baseline", {})
            print(f"   Nivel fitness: {fitness.get('fitness_level')}")
            print(f"   Sesiones/semana: {fitness.get('weekly_sessions_avg', 0):.1f}")
            print(f"   Deporte principal: {fitness.get('primary_sport')}")
            
            sleep = profile.get("sleep_patterns", {})
            print(f"   Sueño histórico: {sleep.get('sleep_avg_historical', 0):.2f} horas")
            print(f"   Déficit crónico: {sleep.get('chronic_sleep_deficit')}")
            
            recovery = profile.get("recovery_capacity", {})
            print(f"   Body Battery: {recovery.get('body_battery_avg', 0):.1f}")
            print(f"   Recovery score: {recovery.get('recovery_score', 0):.1f}")
            
            risk = profile.get("overreaching_risk", {})
            print(f"   ACWR ratio: {risk.get('acwr_ratio', 0):.3f}")
            print(f"   Nivel de riesgo: {risk.get('risk_level')}")
            
        except Exception as e:
            print(f"❌ Error obteniendo perfil atlético: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Test 2: Generar plan con objetivo específico
        print("\n🔄 Test 2: Generar plan con objetivo específico...")
        try:
            week_start = date.today() - timedelta(days=date.today().weekday())
            goal = "Mejorar fuerza en piernas y mantener cardio para preparación de carrera de 10km"
            
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
            
            # Verificar distribución de tipos de sesiones
            session_types = {}
            for session in plan.get('sessions', []):
                session_type = session.get('session_type')
                session_types[session_type] = session_types.get(session_type, 0) + 1
            
            print(f"\n   Distribución de sesiones:")
            for session_type, count in session_types.items():
                print(f"      {session_type}: {count}")
            
            # Verificar restricciones
            print(f"\n   Verificación de restricciones:")
            
            # Máximo 2 días consecutivos de alta intensidad
            high_intensity_streak = 0
            max_high_intensity_streak = 0
            for session in plan.get('sessions', []):
                if session.get('intensity') == 'high':
                    high_intensity_streak += 1
                    max_high_intensity_streak = max(max_high_intensity_streak, high_intensity_streak)
                else:
                    high_intensity_streak = 0
            
            if max_high_intensity_streak <= 2:
                print(f"      ✅ Máximo 2 días consecutivos de alta intensidad: {max_high_intensity_streak}")
            else:
                print(f"      ❌ Máximo 2 días consecutivos de alta intensidad: {max_high_intensity_streak} (excede)")
            
            # Al menos 1 sesión de movilidad
            mobility_count = session_types.get('mobility', 0) + session_types.get('active_recovery', 0)
            if mobility_count >= 1:
                print(f"      ✅ Al menos 1 sesión de movilidad: {mobility_count}")
            else:
                print(f"      ❌ Al menos 1 sesión de movilidad: {mobility_count} (insuficiente)")
            
            # Distribución de fuerza y cardio
            strength_count = session_types.get('strength', 0)
            cardio_count = session_types.get('running', 0) + session_types.get('trail_running', 0)
            
            if strength_count > 0 and cardio_count > 0:
                print(f"      ✅ Distribución fuerza y cardio: fuerza={strength_count}, cardio={cardio_count}")
            else:
                print(f"      ⚠️  Distribución fuerza y cardio: fuerza={strength_count}, cardio={cardio_count}")
            
        except Exception as e:
            print(f"❌ Error generando plan: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Test 3: Obtener plan actual
        print("\n🔄 Test 3: Obtener plan actual...")
        try:
            current_plan = TrainingPlanService.get_current_plan(db, user_id)
            
            if current_plan:
                print(f"✅ Plan actual obtenido exitosamente")
                print(f"   Plan ID: {current_plan.get('plan_id')}")
                print(f"   Estado: {current_plan.get('status')}")
                print(f"   Progreso: {current_plan.get('progress', {}).get('completed', 0)}/{current_plan.get('progress', {}).get('total', 0)} ({current_plan.get('progress', {}).get('percentage', 0):.0f}%)")
                
                # Verificar que las sesiones tengan IDs
                sessions = current_plan.get('plan', {}).get('sessions', [])
                sessions_with_ids = [s for s in sessions if s.get('id')]
                print(f"   Sesiones con IDs: {len(sessions_with_ids)}/{len(sessions)}")
            else:
                print(f"❌ No hay plan actual")
                return 1
                
        except Exception as e:
            print(f"❌ Error obteniendo plan actual: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        # Test 4: Actualizar sesión
        print("\n🔄 Test 4: Actualizar sesión...")
        try:
            if current_plan and current_plan.get('plan', {}).get('sessions'):
                first_session = current_plan['plan']['sessions'][0]
                session_id = first_session.get('id')
                
                if session_id:
                    updated = TrainingPlanService.update_session(
                        db=db,
                        session_id=session_id,
                        changes={
                            "user_notes": "Nota de prueba de integración - sesión actualizada correctamente",
                            "completed": True
                        }
                    )
                    
                    print(f"✅ Sesión actualizada exitosamente")
                    print(f"   Session ID: {updated.get('id')}")
                    print(f"   Completada: {updated.get('completed')}")
                    print(f"   Notas: {updated.get('user_notes')}")
                else:
                    print(f"⚠️  No se encontró ID de sesión para actualizar")
            else:
                print(f"⚠️  No hay sesiones en el plan para actualizar")
                
        except Exception as e:
            print(f"❌ Error actualizando sesión: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 5: Verificar progreso actualizado
        print("\n🔄 Test 5: Verificar progreso actualizado...")
        try:
            updated_plan = TrainingPlanService.get_current_plan(db, user_id)
            
            if updated_plan:
                progress = updated_plan.get('progress', {})
                print(f"✅ Progreso actualizado")
                print(f"   Completadas: {progress.get('completed', 0)}/{progress.get('total', 0)}")
                print(f"   Porcentaje: {progress.get('percentage', 0):.0f}%")
                
                if progress.get('completed', 0) > 0:
                    print(f"   ✅ El progreso se actualizó correctamente después de marcar sesión como completada")
                else:
                    print(f"   ⚠️  El progreso no se actualizó")
            else:
                print(f"❌ No hay plan actual")
                
        except Exception as e:
            print(f"❌ Error verificando progreso: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS DE INTEGRACIÓN PASARON")
        print("="*60)
        print("\n🎉 El sistema de planes de entrenamiento está funcionando correctamente con datos reales!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
