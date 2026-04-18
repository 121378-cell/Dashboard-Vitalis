/**
 * Health Connect Service — Vitalis Companion App
 * 
 * Wrapper sobre capacitor-health para integrar Google Health Connect.
 * Permite leer biométricos y escribir entrenamientos.
 */

import { Health } from 'capacitor-health';

// ============================================================================
// TYPES
// ============================================================================

export interface HCBiometrics {
  heartRate: number | null;
  restingHeartRate: number | null;
  hrv: number | null;
  steps: number | null;
  sleepSeconds: number | null;
  sleepHours: number | null;
  calories: number | null;
  activeCalories: number | null;
  spo2: number | null;
  weight: number | null;
  bodyFat: number | null;
  source: 'health_connect' | 'cache' | 'demo';
  date: string;
}

export interface HCWorkout {
  id: string;
  title: string;
  startTime: Date;
  endTime: Date;
  exerciseType: string;
  calories: number;
  duration: number;
  steps?: number;
  distance?: number;
  source: string;
  heartRate?: { timestamp: string; bpm: number }[];
}

export interface HCPermissionStatus {
  granted: boolean;
  permissions: { [key: string]: boolean };
}

// Permissions que soporta el plugin
export type HCHealthPermission =
  | 'READ_STEPS'
  | 'READ_WORKOUTS'
  | 'WRITE_WORKOUTS'
  | 'READ_ACTIVE_CALORIES'
  | 'READ_TOTAL_CALORIES'
  | 'READ_DISTANCE'
  | 'READ_HEART_RATE'
  | 'READ_ROUTE'
  | 'READ_MINDFULNESS';

// ============================================================================
// MAPPINGS: Vitalis ↔ Health Connect
// ============================================================================

export const EXERCISE_TYPE_MAP: Record<string, string> = {
  'strength': 'STRENGTH_TRAINING',
  'strength_training': 'STRENGTH_TRAINING',
  'weightlifting': 'WEIGHTLIFTING',
  'cardio': 'RUNNING',
  'running': 'RUNNING',
  'cycling': 'CYCLING',
  'swimming': 'SWIMMING',
  'hiit': 'HIGH_INTENSITY_INTERVAL_TRAINING',
  'crossfit': 'CROSS_TRAINING',
  'cross_training': 'CROSS_TRAINING',
  'yoga': 'YOGA',
  'pilates': 'PILATES',
  'boxing': 'BOXING',
  'martial_arts': 'MARTIAL_ARTS',
  'rowing': 'ROWING',
  'elliptical': 'ELLIPTICAL',
  'walk': 'WALKING',
  'hiking': 'HIKING',
  'rest': 'OTHER',
  'descanso': 'OTHER',
};

export const VITALIS_SESSION_MAP: Record<string, string> = {
  'STRENGTH_TRAINING': 'strength',
  'WEIGHTLIFTING': 'strength',
  'RUNNING': 'cardio',
  'CYCLING': 'cardio',
  'SWIMMING': 'cardio',
  'HIGH_INTENSITY_INTERVAL_TRAINING': 'hiit',
  'CROSS_TRAINING': 'crossfit',
  'YOGA': 'yoga',
  'PILATES': 'flexibility',
  'BOXING': 'boxing',
  'MARTIAL_ARTS': 'martial_arts',
  'WALKING': 'walk',
  'HIKING': 'hiking',
};

// ============================================================================
// HEALTH CONNECT SERVICE
// ============================================================================

class HealthConnectServiceClass {
  private available: boolean = false;
  private permissionsGranted: boolean = false;

  // ========================================================================
  // INITIALIZATION
  // ========================================================================

  async initialize(): Promise<void> {
    try {
      const result = await Health.isHealthAvailable();
      this.available = result.available;
      console.log(`[HealthConnect] Available: ${this.available}`);
    } catch (error) {
      console.error('[HealthConnect] Init error:', error);
      this.available = false;
    }
  }

  // ========================================================================
  // PERMISSIONS
  // ========================================================================

  async isAvailable(): Promise<boolean> {
    return this.available;
  }

  async checkPermissions(): Promise<HCPermissionStatus> {
    if (!this.available) {
      return { granted: false, permissions: {} };
    }

    try {
      const result = await Health.checkHealthPermissions({
        permissions: [
          'READ_STEPS',
          'READ_HEART_RATE',
          'READ_WORKOUTS',
          'READ_ACTIVE_CALORIES',
          'READ_TOTAL_CALORIES',
        ],
      });

      const permMap: { [key: string]: boolean } = {};
      let allGranted = true;

      for (const item of result.permissions) {
        for (const [key, value] of Object.entries(item)) {
          permMap[key] = value;
          if (!value) allGranted = false;
        }
      }

      this.permissionsGranted = allGranted;
      return { granted: allGranted, permissions: permMap };
    } catch (error) {
      console.error('[HealthConnect] Check permissions error:', error);
      return { granted: false, permissions: {} };
    }
  }

  async requestPermissions(): Promise<HCPermissionStatus> {
    if (!this.available) {
      return { granted: false, permissions: {} };
    }

    try {
      const result = await Health.requestHealthPermissions({
        permissions: [
          'READ_STEPS',
          'READ_HEART_RATE',
          'READ_WORKOUTS',
          'READ_ACTIVE_CALORIES',
          'READ_TOTAL_CALORIES',
          'WRITE_WORKOUTS',
        ],
      });

      const permMap: { [key: string]: boolean } = {};
      let allGranted = true;

      for (const item of result.permissions) {
        for (const [key, value] of Object.entries(item)) {
          permMap[key] = value;
          if (!value) allGranted = false;
        }
      }

      this.permissionsGranted = allGranted;
      return { granted: allGranted, permissions: permMap };
    } catch (error) {
      console.error('[HealthConnect] Request permissions error:', error);
      return { granted: false, permissions: {} };
    }
  }

  async openSettings(): Promise<void> {
    try {
      await Health.openHealthConnectSettings();
    } catch (error) {
      console.error('[HealthConnect] Open settings error:', error);
    }
  }

  async showInPlayStore(): Promise<void> {
    try {
      await Health.showHealthConnectInPlayStore();
    } catch (error) {
      console.error('[HealthConnect] Show in store error:', error);
    }
  }

  // ========================================================================
  // READ BIOMETRICS
  // ========================================================================

  async readTodayBiometrics(): Promise<HCBiometrics> {
    return this.readBiometricsRange(
      new Date(new Date().setHours(0, 0, 0, 0)),
      new Date()
    );
  }

  async readBiometricsRange(startDate: Date, endDate: Date): Promise<HCBiometrics> {
    if (!this.available) {
      return getFallbackBiometrics();
    }

    try {
      // Queries en paralelo para eficiencia
      const [stepsData, heartRateData, caloriesData, sleepData] = await Promise.allSettled([
        this.readSteps(startDate, endDate),
        this.readHeartRate(startDate, endDate),
        this.readCalories(startDate, endDate),
        this.readSleep(startDate, endDate),
      ]);

      // Steps (agregado por día)
      let steps: number | null = null;
      if (stepsData.status === 'fulfilled' && stepsData.value.length > 0) {
        steps = stepsData.value.reduce((sum, d) => sum + d.value, 0);
      }

      // Heart rate (último valor del día)
      let heartRate: number | null = null;
      if (heartRateData.status === 'fulfilled' && heartRateData.value.length > 0) {
        heartRate = heartRateData.value[heartRateData.value.length - 1].bpm;
      }

      // Calories (suma total)
      let calories: number | null = null;
      if (caloriesData.status === 'fulfilled' && caloriesData.value.length > 0) {
        calories = caloriesData.value.reduce((sum, d) => sum + d.value, 0);
      }

      // Sleep (horas totales)
      let sleepHours: number | null = null;
      let sleepSeconds: number | null = null;
      if (sleepData.status === 'fulfilled' && sleepData.value > 0) {
        sleepHours = sleepData.value;
        sleepSeconds = sleepData.value * 3600;
      }

      return {
        heartRate,
        restingHeartRate: null,
        hrv: null,
        steps,
        sleepSeconds,
        sleepHours,
        calories,
        activeCalories: calories,
        spo2: null,
        weight: null,
        bodyFat: null,
        source: 'health_connect',
        date: startDate.toISOString().split('T')[0],
      };
    } catch (error) {
      console.error('[HealthConnect] Read biometrics error:', error);
      return getFallbackBiometrics();
    }
  }

  async readWeeklyBiometrics(): Promise<HCBiometrics[]> {
    const result: HCBiometrics[] = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const nextDate = new Date(date);
      nextDate.setDate(nextDate.getDate() + 1);

      const biometrics = await this.readBiometricsRange(date, nextDate);
      result.push(biometrics);
    }

    return result;
  }

  // ========================================================================
  // READ DATA HELPERS
  // ========================================================================

  async readSteps(startDate: Date, endDate: Date): Promise<{ startDate: string; endDate: string; value: number }[]> {
    try {
      // Usar queryAggregated para steps
      const result = await Health.queryAggregated({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'steps',
        bucket: 'DAILY',
      });

      return result.aggregatedData.map(d => ({
        startDate: d.startDate,
        endDate: d.endDate,
        value: d.value,
      }));
    } catch (error) {
      console.error('[HealthConnect] Read steps error:', error);
      return [];
    }
  }

  async readHeartRate(startDate: Date, endDate: Date): Promise<{ timestamp: string; bpm: number }[]> {
    try {
      // Usar queryRecords (solo soporta 'steps' según tipos, pero el plugin debería soportar heart rate)
      // Como el plugin solo define 'steps' para queryRecords, usamos queryWorkouts para obtener HR
      const workouts = await this.readWorkouts(startDate, endDate);
      
      // Extraer heart rate samples de workouts
      const samples: { timestamp: string; bpm: number }[] = [];
      for (const workout of workouts) {
        if (workout.heartRate) {
          samples.push(...workout.heartRate);
        }
      }
      
      return samples;
    } catch (error) {
      console.error('[HealthConnect] Read heart rate error:', error);
      return [];
    }
  }

  async readCalories(startDate: Date, endDate: Date): Promise<{ startDate: string; endDate: string; value: number }[]> {
    try {
      const result = await Health.queryAggregated({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'active-calories',
        bucket: 'DAILY',
      });

      return result.aggregatedData.map(d => ({
        startDate: d.startDate,
        endDate: d.endDate,
        value: d.value,
      }));
    } catch (error) {
      console.error('[HealthConnect] Read calories error:', error);
      return [];
    }
  }

  async readSleep(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'sleep',
        bucket: 'DAILY',
      });
      // Suma total en segundos y convierte a horas
      const totalSeconds = result.aggregatedData.reduce((s, d) => s + (d.value || 0), 0);
      return totalSeconds > 0 ? totalSeconds / 3600 : 0;
    } catch (error) {
      // 'sleep' puede no estar soportado en todos los dispositivos o versiones del plugin
      console.warn('[HealthConnect] Sleep data not available:', error);
      return 0;
    }
  }

  async readWorkouts(startDate: Date, endDate: Date): Promise<HCWorkout[]> {
    try {
      const result = await Health.queryWorkouts({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        includeHeartRate: true,
        includeRoute: false,
        includeSteps: true,
      });

      return result.workouts.map(w => ({
        id: w.id || '',
        title: this.mapWorkoutType(w.workoutType),
        startTime: new Date(w.startDate),
        endTime: new Date(w.endDate),
        exerciseType: w.workoutType,
        calories: w.calories,
        duration: w.duration,
        steps: w.steps,
        distance: w.distance,
        source: w.sourceBundleId,
        heartRate: w.heartRate,
      }));
    } catch (error) {
      console.error('[HealthConnect] Read workouts error:', error);
      return [];
    }
  }

  async readTodayWorkouts(): Promise<HCWorkout[]> {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    return this.readWorkouts(today, tomorrow);
  }

  async readWeeklyWorkouts(): Promise<HCWorkout[]> {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 6);

    return this.readWorkouts(weekAgo, today);
  }

  // ========================================================================
  // WRITE WORKOUTS
  // ========================================================================

  // NOTA: El plugin capacitor-health no soporta escribir workouts directamente.
  // La escritura de workouts en Health Connect requiere usar la API de forma nativa.
  // Para escribir, necesitamos crear un intent con ExerciseSession.

  async writeWorkout(workout: {
    title: string;
    exerciseType: string;
    startTime: Date;
    endTime: Date;
    calories?: number;
  }): Promise<{ success: boolean; id: string; error?: string }> {
    // El plugin actual no soporta escritura de workouts.
    // Esto requeriría integración directa con Health Connect Client API.
    console.warn('[HealthConnect] Write workout not fully implemented in plugin');
    
    return {
      success: false,
      id: '',
      error: 'Write workout requires native Health Connect integration. Use Garmin for now.',
    };
  }

  // ========================================================================
  // UTILITY METHODS
  // ========================================================================

  private mapWorkoutType(type: string): string {
    const map: { [key: string]: string } = {
      'STRENGTH_TRAINING': 'Strength Training',
      'RUNNING': 'Running',
      'CYCLING': 'Cycling',
      'SWIMMING': 'Swimming',
      'HIGH_INTENSITY_INTERVAL_TRAINING': 'HIIT',
      'CROSS_TRAINING': 'CrossFit',
      'YOGA': 'Yoga',
      'WALKING': 'Walking',
      'OTHER': 'Workout',
    };

    return map[type] || type;
  }
}

// ============================================================================
// FALLBACK DATA
// ============================================================================

function getFallbackBiometrics(): HCBiometrics {
  return {
    heartRate: null,
    restingHeartRate: null,
    hrv: null,
    steps: null,
    sleepSeconds: null,
    sleepHours: null,
    calories: null,
    activeCalories: null,
    spo2: null,
    weight: null,
    bodyFat: null,
    source: 'demo',
    date: new Date().toISOString().split('T')[0],
  };
}

// ============================================================================
// EXPORT
// ============================================================================

export const healthConnectService = new HealthConnectServiceClass();
export default healthConnectService;