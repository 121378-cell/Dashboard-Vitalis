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
  bodyFat: number | null;
  respiration: number | null;
  stress: number | null;
  spo2: number | null;
  weight: number | null;
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
      const allPermissions: HCHealthPermission[] = ['READ_STEPS', 'READ_HEART_RATE', 'READ_ACTIVE_CALORIES', 'READ_WORKOUTS', 'READ_MINDFULNESS'];
      const result = await Health.requestHealthPermissions({ permissions: allPermissions });
      
      const permMap: { [key: string]: boolean } = {};
      let allGranted = true;

      // El plugin devuelve un array de objetos o un objeto dependiendo de la versión
      const permissionsArray = Array.isArray(result.permissions) ? result.permissions : [result.permissions];

      for (const item of permissionsArray) {
        for (const [key, value] of Object.entries(item)) {
          permMap[key] = !!value;
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
      const allPermissions: HCHealthPermission[] = ['READ_STEPS', 'READ_HEART_RATE', 'READ_ACTIVE_CALORIES', 'READ_WORKOUTS', 'READ_MINDFULNESS'];
      const result = await Health.requestHealthPermissions({ permissions: allPermissions });
      
      const permMap: { [key: string]: boolean } = {};
      let allGranted = true;

      const permissionsArray = Array.isArray(result.permissions) ? result.permissions : [result.permissions];

      for (const item of permissionsArray) {
        for (const [key, value] of Object.entries(item)) {
          permMap[key] = !!value;
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

  /**
   * Verifica permisos; si no estan concedidos, los solicita.
   * Si la solicitud falla, abre la configuracion de Health Connect.
   * Devuelve true si los permisos estan concedidos al final.
   */
  async ensurePermissions(): Promise<boolean> {
    if (!this.available) return false;

    // 1. Verificar actuales
    let status = await this.checkPermissions();
    if (status.granted) return true;

    console.warn('[HC] Permisos no concedidos. Solicitando...');

    // 2. Solicitar permisos
    status = await this.requestPermissions();
    if (status.granted) return true;

    console.warn('[HC] Permisos DENEGADOS. Abriendo configuracion de Health Connect...');

    // 3. Abrir settings para que el usuario los active manualmente
    try {
      await this.openSettings();
    } catch (e) {
      console.error('[HC] No se pudo abrir settings:', e);
    }

    return false;
  }

  // ========================================================================
  // READ BIOMETRICS
  // ========================================================================

  async readTodayBiometrics(): Promise<HCBiometrics> {
    // Leer solo el día actual (desde las 00:00 local) para evitar duplicar pasos
    const now = new Date();
    // Crear fecha de inicio a las 00:00:00 del día actual en hora LOCAL
    const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const endDate = now;

    console.log(`[HC] FIX ACTIVO: Leyendo hoy desde ${startDate.toISOString()} (local midnight) hasta ${endDate.toISOString()}`);

    return this.readBiometricsRange(startDate, endDate);
  }

  async readBiometricsRange(startDate: Date, endDate: Date): Promise<HCBiometrics> {
    if (!this.available) return getFallbackBiometrics();

    console.log(`[HC] Leyendo rango: ${startDate.toISOString()} -> ${endDate.toISOString()}`);

    let steps: number | null = null;
    let heartRate: number | null = null;
    let calories: number | null = null;
    let sleepHours: number | null = null;
    let sleepSeconds: number | null = null;

    // 1. WORKOUTS: obtener HR, calories y steps (pero steps de workouts puede duplicar)
    try {
      const { workouts = [] } = await Health.queryWorkouts({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        includeHeartRate: true,
        includeSteps: false, // No sumar steps de workouts para evitar duplicación
        includeRoute: false,
      });
      
      if (workouts.length > 0) {
        let wCals = 0, wHR = 0;
        workouts.forEach(w => {
          wCals += w.calories || 0;
          if (w.heartRate?.length) wHR = w.heartRate[w.heartRate.length-1].bpm;
        });
        calories = wCals || null;
        heartRate = wHR || null;
        console.log(`[HC] Datos de Workouts: cals=${calories}, hr=${heartRate}`);
      }
    } catch (e) { console.warn("[HC] Workouts err", e); }

    // 2. PASOS: queryRecords primero (suma manual de registros individuales - más fiable)
    try {
      const { records = [] } = await Health.queryRecords({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'steps',
      });
      if (records.length > 0) {
        const total = records.reduce((s: number, r: any) => s + (r.count || 0), 0);
        steps = total;
        console.log(`[HC] Steps records: ${records.length} registros, total=${total}`);
      } else {
        console.log('[HC] Steps records: 0 registros encontrados');
      }
    } catch (e) { console.warn('[HC] Steps records falló:', e); }

    // Fallback: queryAggregated si queryRecords no devolvió nada
    if (steps === null || steps === 0) {
      try {
        const r = await Health.queryAggregated({
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          dataType: 'steps',
          bucket: 'day',
        });
        const total = r.aggregatedData?.reduce((s: number, d: any) => s + (d.value || 0), 0) ?? 0;
        if (total > 0) { steps = total; console.log(`[HC] Steps agg fallback: ${total}`); }
      } catch (e) { console.warn('[HC] Steps agg fallback falló:', e); }
    }

    // 3. CALORÍAS: queryAggregated (sin bucket - original funcionaba así)
    if (calories === null) {
      try {
        const r = await Health.queryAggregated({
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          dataType: 'active-calories',
          bucket: 'day',
        });
        const total = r.aggregatedData?.reduce((s: number, d: any) => s + (d.value || 0), 0) ?? 0;
        if (total > 0) { calories = total; console.log(`[HC] Calories agg: ${total}`); }
      } catch (e) { console.warn('[HC] Calories agg falló:', e); }
    }

    // Sleep
    try {
      const sh = await this.readSleep(startDate, endDate);
      if (sh > 0) { sleepHours = sh; sleepSeconds = sh * 3600; }
    } catch { /* intentional */ }

    // Respiration & HRV
    let resp: number | null = null;
    let hrv: number | null = null;
    try {
      resp = await this.readRespiration(startDate, endDate);
      hrv = await this.readHRV(startDate, endDate);
    } catch { /* skip */ }

    // Estimación de Stress (HRV inverso)
    // El estrés de Garmin no está en HC, pero se estima: 
    // HRV alto (70+) -> Estrés bajo (10-25)
    // HRV bajo (20-30) -> Estrés alto (70-90)
    let stress: number | null = null;
    if (hrv && hrv > 0) {
      stress = Math.max(5, Math.min(95, 100 - (hrv * 1.2)));
    }

    console.log(`[HC] TOTAL → steps=${steps} cal=${calories} hr=${heartRate} sleep=${sleepHours} resp=${resp} hrv=${hrv}`);

    return {
      heartRate, restingHeartRate: null, hrv,
      steps, sleepSeconds, sleepHours,
      calories, activeCalories: calories,
      spo2: null, weight: null, bodyFat: null,
      respiration: resp,
      stress,
      source: 'health_connect',
      date: startDate.toISOString().split('T')[0],
    };
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
    // Probamos distintos dataType strings por compatibilidad entre versiones del plugin
    const dataTypes = ['steps', 'STEPS', 'step_count'];
    
    for (const dataType of dataTypes) {
      try {
        const result = await Health.queryAggregated({
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          dataType: dataType as 'steps',
          bucket: 'day',
        });
        if (result.aggregatedData && result.aggregatedData.length > 0) {
          console.log(`[HC] Steps OK con dataType: ${dataType}`, result.aggregatedData);
          return result.aggregatedData.map(d => ({
            startDate: d.startDate,
            endDate: d.endDate,
            value: d.value || 0,
          }));
        }
      } catch (e) {
        console.warn(`[HC] Steps fallo con dataType '${dataType}':`, e);
      }
    }

    // FALLBACK: Escaneo manual de registros (más lento pero infalible)
    try {
      console.log('[HC] Intentando escaneo manual de registros de pasos...');
      const { records = [] } = await Health.queryRecords({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'steps'
      });
      if (records.length > 0) {
        const total = records.reduce((acc, r: any) => acc + (r.count || 0), 0);
        console.log(`[HC] Pasos manuales encontrados: ${total}`);
        return [{
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          value: total
        }];
      }
    } catch (e) {
      console.warn('[HC] Fallo también el escaneo manual:', e);
    }

    return [];
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
    // Probamos distintos dataType strings por compatibilidad
    const dataTypes = ['active-calories', 'calories', 'ACTIVE_ENERGY_BURNED', 'activeCalories'];
    
    for (const dataType of dataTypes) {
      try {
        const result = await Health.queryAggregated({
          startDate: startDate.toISOString(),
          endDate: endDate.toISOString(),
          dataType: dataType as 'active-calories',
          bucket: 'day',
        });
        if (result.aggregatedData && result.aggregatedData.length > 0) {
          console.log(`[HC] Calories OK con dataType: ${dataType}`, result.aggregatedData);
          return result.aggregatedData.map(d => ({
            startDate: d.startDate,
            endDate: d.endDate,
            value: d.value || 0,
          }));
        }
      } catch (e) {
        console.warn(`[HC] Calories fallo con dataType '${dataType}':`, e);
      }
    }
    return [];
  }

  async readRespiration(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'respiratory-rate' as 'steps',
        bucket: 'day'
      });
      return result.aggregatedData?.[0]?.value || 0;
    } catch { return 0; }
  }

  async readHRV(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        dataType: 'heart-rate-variability' as 'steps',
        bucket: 'day'
      });
      return result.aggregatedData?.[0]?.value || 0;
    } catch { return 0; }
  }

  async readSleep(startDate: Date, endDate: Date): Promise<number> {
    try {
      // 1. Intentar escaneo de sesiones de sueño (Más robusto para Garmin)
      // Probamos los tipos de datos correctos para sleep
      const sleepDataTypes = ['sleep_session', 'sleep', 'SLEEP_SESSION'];
      let totalMs = 0;
      
      for (const dataType of sleepDataTypes) {
        try {
          const { records = [] } = await Health.queryRecords({
            startDate: startDate.toISOString(),
            endDate: endDate.toISOString(),
            dataType: dataType as 'steps'
          });

          if (records.length > 0) {
            records.forEach((r: any) => {
              const start = new Date(r.startDate).getTime();
              const end = new Date(r.endDate).getTime();
              const duration = end - start;
              
              // Validación: No aceptar sesiones de > 24h (evitar datos corruptos)
              if (duration > 0 && duration < 24 * 60 * 60 * 1000) {
                totalMs += duration;
              }
            });
            
            if (totalMs > 0) break;
          }
        } catch { /* continue to next dataType */ }
      }

      if (totalMs > 0) {
        const hours = totalMs / (1000 * 60 * 60);
        console.log(`[HC] Horas de sueño encontradas (scan): ${hours.toFixed(2)}`);
        // Segunda validación: Limitar máximo 16h por día (valor fisiológicamente imposible de superar)
        return Math.min(hours, 16);
      }

      // 2. Fallback a agregados
      const dataTypes = ['sleep_session', 'sleep', 'SLEEP_SESSION'];
      for (const dataType of dataTypes) {
        try {
          const result = await Health.queryAggregated({
            startDate: startDate.toISOString(),
            endDate: endDate.toISOString(),
            dataType: dataType as 'steps',
            bucket: 'day',
          });
          if (result.aggregatedData?.length > 0) {
            const val = result.aggregatedData[0].value || 0;
            if (val > 0 && val < 16) return val;
          }
        } catch { /* skip */ }
      }
      return 0;
    } catch (error) {
      console.error('[HealthConnect] Read sleep error:', error);
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
    respiration: null,
    stress: null,
    source: 'demo',
    date: new Date().toISOString().split('T')[0],
  };
}

// ============================================================================
// EXPORT
// ============================================================================

export const healthConnectService = new HealthConnectServiceClass();
export default healthConnectService;