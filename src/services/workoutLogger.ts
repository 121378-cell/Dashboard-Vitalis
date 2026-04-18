import { syncService } from './syncService';
import { healthConnectService } from './healthConnectService';
import { Workout } from '../types';

export interface VitalisWorkout {
  id?: number;
  sessionName: string;
  startedAt: Date;
  completedAt: Date;
  sessionType: 'Strength' | 'Cardio' | 'Hiit' | 'Yoga' | 'Flexibilidad' | 'Descanso' | string;
  totalCalories: number;
}

export class WorkoutLogger {

  /**
   * Mapear tipos de ejercicio de Vitalis a Health Connect
   * Basado en la tabla de Phase 4.2
   */
  private mapToHealthConnectType(sessionType: string): string {
    const map: Record<string, string> = {
      'Strength': 'STRENGTH_TRAINING',
      'Cardio': 'RUNNING', // Mapping fallback
      'Hiit': 'HIGH_INTENSITY_INTERVAL_TRAINING',
      'Yoga': 'FLEXIBILITY',
      'Flexibilidad': 'FLEXIBILITY',
      'Descanso': 'REST',
    };
    return map[sessionType] || 'OTHER';
  }

  // 1. Guardar localmente
  async completeWorkout(workout: VitalisWorkout) {
    console.log('[WorkoutLogger] Persistiendo localmente finalización del entrenamiento:', workout.sessionName);
    // Acá iría la implementación local completa (IndexDB específica para estado de la sesión si aplica)
    return { success: true };
  }

  // Flujo orquestador de finalización (Phase 4.1)
  async onWorkoutComplete(workout: VitalisWorkout) {
    console.log(`[WorkoutLogger] Iniciando onWorkoutComplete para: ${workout.sessionName}`);

    // 1. Guardar localmente
    await this.completeWorkout(workout);

    // Transformamos VitalisWorkout a nuestra Interfaz Backend Workout
    const durationMin = Math.max(1, Math.round((workout.completedAt.getTime() - workout.startedAt.getTime()) / 60000));
    const workoutEntity: Workout = {
      id: workout.id || Date.now(),
      source: 'vitalis',
      external_id: `vitalis_${Date.now()}`,
      name: workout.sessionName,
      description: `Sesión de ${workout.sessionType} completada en Vitalis`,
      date: workout.startedAt.toISOString().split('T')[0],
      duration: durationMin,
      calories: workout.totalCalories
    };

    // 2. Sincronizar al backend
    try {
      await syncService.syncWorkoutCompleted(workoutEntity);
      console.log('[WorkoutLogger] Sincronización backend exitosa (o delegada a IndexedDB).');
    } catch (e) {
      console.warn('[WorkoutLogger] Sincronización backend falló en nivel alto:', e);
    }

    // 3. Escribir en Health Connect
    try {
      const hcStatus = await healthConnectService.checkPermissions();
      
      // Chequeo proactivo validando permisos generales y la bandera global
      if (hcStatus.granted) {
        console.log(`[WorkoutLogger] Escribiendo a Health Connect con tipo mapeado: ${this.mapToHealthConnectType(workout.sessionType)}`);
        await healthConnectService.writeWorkout({
          title: workout.sessionName,
          startTime: workout.startedAt,
          endTime: workout.completedAt,
          exerciseType: this.mapToHealthConnectType(workout.sessionType),
          calories: workout.totalCalories,
        });
        console.log('[WorkoutLogger] Notificación enviada a Health Connect');
      } else {
        console.log('[WorkoutLogger] Health Connect omitido (permisos insuficientes o inactivo).');
      }
    } catch (err) {
      console.error('[WorkoutLogger] Error operando contra Health Connect:', err);
    }
  }
}

export const workoutLogger = new WorkoutLogger();
