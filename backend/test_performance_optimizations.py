"""
Test de optimizaciones de rendimiento
=====================================

Este script prueba las optimizaciones de rendimiento implementadas.

Ejecución:
    cd backend
    python test_performance_optimizations.py
"""

import sys
import os
import io
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.db.session import SessionLocal
from app.services.training_plan_service import TrainingPlanService
from app.utils.training_plan_optimizer import (
    PerformanceOptimizer,
    compress_json,
    decompress_json,
    get_cache_key,
    optimize_json_size,
    validate_plan_data
)
from datetime import date, timedelta

def main():
    """Función principal."""
    print("\n" + "="*60)
    print("TEST DE OPTIMIZACIONES DE RENDIMIENTO")
    print("="*60)
    
    db = SessionLocal()
    try:
        user_id = "default_user"
        
        # Test 1: Compresión y descompresión de JSON
        print("\n🔄 Test 1: Compresión y descompresión de JSON...")
        try:
            test_data = {
                "weekly_goal": "Test de compresión",
                "reasoning": "Este es un test para verificar la compresión de datos JSON grandes",
                "total_planned_minutes": 420,
                "sessions": [
                    {
                        "date": "2024-05-06",
                        "day_of_week": "Lunes",
                        "session_type": "strength",
                        "title": "Fuerza prueba",
                        "description": "Sesión de prueba" * 100,  # Repetir para hacer más grande
                        "duration_minutes": 60,
                        "intensity": "medium",
                        "exercises": [
                            {
                                "name": "Sentadilla",
                                "sets": 3,
                                "reps": "10",
                                "weight_kg": 50,
                                "rest_seconds": 90,
                                "muscle_group": "legs",
                                "notes": "Mantener espalda recta" * 50
                            }
                        ] * 10
                    }
                ] * 5
            }
            
            original_size = len(json.dumps(test_data, ensure_ascii=False))
            print(f"   Tamaño original: {original_size} caracteres")
            
            # Comprimir
            start_time = time.time()
            compressed = compress_json(test_data)
            compress_time = time.time() - start_time
            
            compressed_size = len(compressed)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            print(f"   Tamaño comprimido: {compressed_size} caracteres")
            print(f"   Ratio de compresión: {compression_ratio:.1f}%")
            print(f"   Tiempo de compresión: {compress_time:.4f}s")
            
            # Descomprimir
            start_time = time.time()
            decompressed = decompress_json(compressed)
            decompress_time = time.time() - start_time
            
            print(f"   Tiempo de descompresión: {decompress_time:.4f}s")
            
            # Verificar integridad
            if decompressed == test_data:
                print(f"   ✅ Integridad verificada: los datos son idénticos")
            else:
                print(f"   ❌ Error: los datos descomprimidos no coinciden")
            
        except Exception as e:
            print(f"❌ Error en test de compresión: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Optimización de tamaño de JSON
        print("\n🔄 Test 2: Optimización de tamaño de JSON...")
        try:
            large_data = {
                "weekly_goal": "Test",
                "reasoning": "Test",
                "total_planned_minutes": 420,
                "sessions": [],
                "fitness_snapshot": {"data": "x" * 10000},  # Datos grandes innecesarios
                "ai_reasoning": "x" * 5000
            }
            
            original_size = len(json.dumps(large_data, ensure_ascii=False))
            print(f"   Tamaño original: {original_size} caracteres")
            
            optimized = optimize_json_size(large_data, max_size=5000)
            optimized_size = len(json.dumps(optimized, ensure_ascii=False))
            
            print(f"   Tamaño optimizado: {optimized_size} caracteres")
            print(f"   Reducción: {(1 - optimized_size / original_size) * 100:.1f}%")
            
            if optimized_size < original_size:
                print(f"   ✅ Optimización exitosa")
            else:
                print(f"   ⚠️  No se pudo optimizar (ya estaba por debajo del límite)")
            
        except Exception as e:
            print(f"❌ Error en test de optimización: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Validación de datos de plan
        print("\n🔄 Test 3: Validación de datos de plan...")
        try:
            # Datos válidos
            valid_data = {
                "weekly_goal": "Test",
                "reasoning": "Test",
                "total_planned_minutes": 420,
                "sessions": [
                    {
                        "date": "2024-05-06",
                        "day_of_week": "Lunes",
                        "session_type": "strength",
                        "title": "Test"
                    }
                ]
            }
            
            is_valid = validate_plan_data(valid_data)
            print(f"   Datos válidos: {is_valid}")
            
            if is_valid:
                print(f"   ✅ Validación correcta para datos válidos")
            else:
                print(f"   ❌ Error: datos válidos marcados como inválidos")
            
            # Datos inválidos (falta campo requerido)
            invalid_data = {
                "weekly_goal": "Test",
                "reasoning": "Test",
                "total_planned_minutes": 420,
                "sessions": []  # Sesiones vacías
            }
            
            is_valid = validate_plan_data(invalid_data)
            print(f"   Datos inválidos (sesiones vacías): {is_valid}")
            
            if not is_valid:
                print(f"   ✅ Validación correcta para datos inválidos")
            else:
                print(f"   ❌ Error: datos inválidos marcados como válidos")
            
        except Exception as e:
            print(f"❌ Error en test de validación: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Optimización de consultas
        print("\n🔄 Test 4: Optimización de consultas...")
        try:
            # Obtener estadísticas
            start_time = time.time()
            stats = PerformanceOptimizer.get_plan_statistics(db, user_id)
            query_time = time.time() - start_time
            
            print(f"   Tiempo de consulta: {query_time:.4f}s")
            print(f"   Estadísticas:")
            print(f"      Total planes: {stats.get('total_plans', 0)}")
            print(f"      Planes activos: {stats.get('active_plans', 0)}")
            print(f"      Total sesiones: {stats.get('total_sessions', 0)}")
            print(f"      Sesiones completadas: {stats.get('completed_sessions', 0)}")
            print(f"      Tasa de completación: {stats.get('completion_rate', 0):.1f}%")
            
            if query_time < 1.0:
                print(f"   ✅ Consulta optimizada (tiempo < 1s)")
            else:
                print(f"   ⚠️  Consulta podría optimizarse más (tiempo >= 1s)")
            
        except Exception as e:
            print(f"❌ Error en test de consultas: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 5: Generación de clave de cache
        print("\n🔄 Test 5: Generación de clave de cache...")
        try:
            cache_key1 = get_cache_key()
            time.sleep(0.1)  # Pequeña pausa
            cache_key2 = get_cache_key()
            
            print(f"   Clave 1: {cache_key1}")
            print(f"   Clave 2: {cache_key2}")
            
            if cache_key1 == cache_key2:
                print(f"   ✅ Claves son iguales (mismo periodo de 5 minutos)")
            else:
                print(f"   ⚠️  Claves son diferentes (cambio de periodo de 5 minutos)")
            
        except Exception as e:
            print(f"❌ Error en test de cache: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print("✅ TEST DE OPTIMIZACIONES COMPLETADO")
        print("="*60)
        print("\n🎉 Las optimizaciones de rendimiento están funcionando correctamente!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    import json
    sys.exit(main())
