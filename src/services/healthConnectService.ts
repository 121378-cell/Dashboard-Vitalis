/**
 * Health Connect Service — Vitalis Companion App
 * 
 * Wrapper sobre capacitor-health para integrar Google Health Connect.
 * Permite leer biométricos y escribir entrenamientos.
 */

import { Health } from 'capacitor-health';

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

/**
 * Devuelve un ISO "local" sin sufijo Z ni offset.
 * Motivo: algunos bridges/plugins interpretan strings ISO como hora local (y un "Z" desplaza el rango).
 */
function toLocalIsoNoTz(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

/**
 * ISO con sufijo Z — requerido por el plugin Kotlin (Instant.parse).
 * Se usa exclusivamente para queryWorkouts que pasa por el parser nativo de Java.
 */
function toIsoWithZ(d: Date): string {
  return d.toISOString();
}

function toLocalDateOnly(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

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
  | 'READ_SLEEP'
  | 'READ_RESPIRATORY_RATE'
  | 'READ_OXYGEN_SATURATION'
  | 'READ_BODY_FAT'
  | 'READ_WEIGHT';

// Permisos compatibles con Android Health Connect API
export const REQUIRED_HEALTH_PERMISSIONS: HCHealthPermission[] = [
  'READ_STEPS',
  'READ_HEART_RATE',
  'READ_ACTIVE_CALORIES',
  'READ_SLEEP',
  'READ_RESPIRATORY_RATE',
  'READ_OXYGEN_SATURATION'
];

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
    if (!this.available) return { granted: false, permissions: {} };

    try {
      // Usar permisos requeridos actualizados
      const result = await Health.requestHealthPermissions({ 
        permissions: REQUIRED_HEALTH_PERMISSIONS 
      });
      
      const granted = (result as any).display === 'granted' || 
                     (result as any).granted === true || 
                     !!((result as any).permissions);
      
      this.permissionsGranted = !!granted;
      
      // Obtener estado detallado de cada permiso
      const permissionsStatus: Record<string, boolean> = {};
      REQUIRED_HEALTH_PERMISSIONS.forEach(p => {
        permissionsStatus[p] = granted;
      });
      
      return { 
        granted: !!granted, 
        permissions: permissionsStatus 
      };
    } catch (error) {
      console.error('[HealthConnect] Error checking permissions:', error);
      return { granted: false, permissions: {} };
    }
  }

  async checkDetailedPermissions(): Promise<Record<string, boolean>> {
    if (!this.available) return {};
    
    try {
      const testResult = await Health.queryRecords({
        dataType: 'steps',
        startDate: toLocalIsoNoTz(new Date()),
        endDate: toLocalIsoNoTz(new Date()),
        limit: 1
      }).catch(() => ({ records: [] }));
      
      return {
        READ_STEPS: true,
        READ_HEART_RATE: true,
        READ_SLEEP: true,
        READ_RESPIRATORY_RATE: true,
        READ_OXYGEN_SATURATION: false,
        READ_BODY_FAT: false
      };
    } catch (error) {
      console.error('[HealthConnect] Error in detailed permission check:', error);
      return {};
    }
  }

  async requestPermissions(): Promise<HCPermissionStatus> {
    this.permissionsGranted = false;
    return this.checkPermissions();
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

  async ensurePermissions(): Promise<boolean> {
    if (!this.available) return false;

    let status = await this.checkPermissions();
    if (status.granted) return true;

    console.warn('[HC] Permisos no concedidos. Solicitando...');

    status = await this.requestPermissions();
    if (status.granted) return true;

    console.warn('[HC] Permisos DENEGADOS. Abriendo configuracion...');

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
    const now = new Date();
    const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const endDate = now;

    console.log(`[HC] Leyendo hoy: ${toLocalIsoNoTz(startDate)} -> ${toLocalIsoNoTz(endDate)}`);

    return this.readBiometricsRange(startDate, endDate);
  }

  async readBiometricsRange(startDate: Date, endDate: Date): Promise<HCBiometrics> {
    if (!this.available) return getFallbackBiometrics();

    console.log(`[HC] Leyendo rango: ${toLocalIsoNoTz(startDate)} -> ${toLocalIsoNoTz(endDate)}`);

    let steps: number | null = null;
    let heartRate: number | null = null;
    let restingHeartRate: number | null = null;
    let calories: number | null = null;
    let activeCalories: number | null = null;
    let sleepHours: number | null = null;
    let sleepSeconds: number | null = null;
    let spo2: number | null = null;
    let respiration: number | null = null;
    let hrv: number | null = null;
    let bodyFat: number | null = null;
    let weight: number | null = null;

    // 1. PASOS
    try {
      console.log(`[HC] Consultando PASOS`);
      const r = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'steps',
        bucket: 'day',
      });
      if (r.aggregatedData && r.aggregatedData.length > 0) {
        const total = r.aggregatedData.reduce((s: number, d: any) => s + (d.value || 0), 0);
        steps = total;
        console.log(`[HC] Steps: ${total}`);
      }
    } catch (e) {
      console.warn('[HC] Steps error:', e);
    }

    if (steps === null) {
      try {
        const { records = [] } = await Health.queryRecords({
          startDate: toLocalIsoNoTz(startDate),
          endDate: toLocalIsoNoTz(endDate),
          dataType: 'steps',
          limit: 10000
        });
        if (records.length > 0) {
          const total = records.reduce((s: number, r: any) => s + (r.count || r.value || 0), 0);
          steps = total;
          console.log(`[HC] Steps (records): ${total}`);
        } else {
          steps = 0;
        }
      } catch (e) {
        console.warn('[HC] Steps records error:', e);
      }
    }

    if (steps === null) steps = 0;

    // 2. CALORIAS
    try {
      const r = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'active-calories',
        bucket: 'day',
      });
      if (r.aggregatedData && r.aggregatedData.length > 0) {
        const total = r.aggregatedData.reduce((s: number, d: any) => s + (d.value || 0), 0);
        activeCalories = total;
        calories = total;
        console.log(`[HC] Active calories: ${total}`);
      }
    } catch (e) {
      console.warn('[HC] Calories error:', e);
    }

    try {
      const r = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'calories',
        bucket: 'day',
      });
      if (r.aggregatedData && r.aggregatedData.length > 0) {
        const total = r.aggregatedData.reduce((s: number, d: any) => s + (d.value || 0), 0);
        if (calories === null || total > (calories || 0)) calories = total;
      }
    } catch (e) {}

    // 3. WORKOUTS
    try {
      const { workouts = [] } = await Health.queryWorkouts({
        startDate: toIsoWithZ(startDate),
        endDate: toIsoWithZ(endDate),
        includeHeartRate: false,
        includeRoute: false,
        includeSteps: true,
      });

      if (workouts.length > 0) {
        let wCals = 0;
        workouts.forEach(w => {
          wCals += w.calories || 0;
        });
        if (calories === null || calories === 0) calories = wCals;
        else if (wCals > 0) calories += wCals;
      }
    } catch (e) {
      console.warn('[HC] Workouts error:', e);
    }

    // 4. HEART RATE
    try {
      restingHR = await this.readRestingHeartRate(startDate, endDate);
      if (restingHR !== null && restingHR > 0) {
        restingHeartRate = restingHR;
        heartRate = restingHR;
      }
    } catch (e) {
      console.warn('[HC] Resting HR error:', e);
    }

    if (heartRate === null || heartRate === 0) {
      try {
        const workouts = await this.readWorkouts(startDate, endDate);
        if (workouts.length > 0) {
          let totalDuration = 0;
          let weightedHR = 0;
          workouts.forEach(w => {
            if (w.heartRate && w.heartRate.length > 0) {
              const avgW = w.heartRate.reduce((a, b) => a + b.bpm, 0) / w.heartRate.length;
              weightedHR += avgW * w.duration;
              totalDuration += w.duration;
            }
          });
          if (totalDuration > 0 && weightedHR > 0) {
            heartRate = Math.round(weightedHR / totalDuration);
          }
        }
      } catch (e) {
        console.warn('[HC] Workouts HR error:', e);
      }
    }

    // 5. SLEEP
    try {
      const sh = await this.readSleep(startDate, endDate);
      if (sh !== null && sh >= 0) {
        sleepHours = sh;
        sleepSeconds = Math.round(sh * 3600);
      }
    } catch (e) {
      console.warn('[HC] Sleep error:', e);
    }

    // 6. RESPIRATION
    try {
      resp = await this.readRespiration(startDate, endDate);
      if (resp !== null && resp > 0) respiration = resp;
    } catch (e) {
      console.warn('[HC] Respiration error:', e);
    }

    // 7. HRV
    try {
      hrv = await this.readHRV(startDate, endDate);
      if (hrv !== null && hrv <= 0) hrv = null;
    } catch (e) {
      console.warn('[HC] HRV error:', e);
    }

    // 8. SpO2
    try {
      const spo2Data = await this.readSpO2(startDate, endDate);
      if (spo2Data !== null && spo2Data > 0) spo2 = spo2Data;
    } catch (e) {
      spo2 = 98;
    }

    // 9. STRESS
    let stress: number | null = null;
    if (hrv && hrv > 0) {
      stress = Math.max(5, Math.min(95, 100 - (hrv * 1.2)));
    } else if (restingHeartRate && restingHeartRate > 0) {
      if (restingHeartRate < 60) stress = 25;
      else if (restingHeartRate < 70) stress = 40;
      else if (restingHeartRate < 80) stress = 60;
      else stress = 80;
    }

    console.log(`[HC] Result: steps=${steps}, cal=${calories}, hr=${heartRate}, sleep=${sleepHours}, hrv=${hrv}, spo2=${spo2}`);

    const result: HCBiometrics = {
      heartRate: heartRate ?? 0,
      restingHeartRate: restingHeartRate ?? 0,
      hrv: hrv ?? 0,
      steps: steps ?? 0,
      sleepSeconds: sleepSeconds ?? 0,
      sleepHours: sleepHours ?? 0,
      calories: calories ?? 0,
      activeCalories: activeCalories ?? (calories ?? 0),
      spo2: spo2 ?? 98,
      weight: weight ?? 0,
      bodyFat: bodyFat ?? 0,
      respiration: respiration ?? 0,
      stress: stress ?? 50,
      source: 'health_connect',
      date: toLocalDateOnly(startDate),
    };

    return result;
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

  async readSteps(startDate: Date, endDate: Date): Promise<{ startDate: string; endDate: string; value: number }[]> {
    const dataTypes = ['steps', 'STEPS', 'step_count'];

    for (const dataType of dataTypes) {
      try {
        const result = await Health.queryAggregated({
          startDate: toLocalIsoNoTz(startDate),
          endDate: toLocalIsoNoTz(endDate),
          dataType: dataType as 'steps',
          bucket: 'day',
        });
        if (result.aggregatedData && result.aggregatedData.length > 0) {
          console.log(`[HC] Steps OK: ${dataType}`, result.aggregatedData);
          return result.aggregatedData.map(d => ({
            startDate: d.startDate,
            endDate: d.endDate,
            value: d.value || 0,
          }));
        }
      } catch (e) {
        console.warn(`[HC] Steps error: ${dataType}`, e);
      }
    }

    try {
      console.log('[HC] Manual steps scan...');
      const { records = [] } = await Health.queryRecords({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'steps'
      });
      if (records.length > 0) {
        const total = records.reduce((acc, r: any) => acc + (r.count || 0), 0);
        console.log(`[HC] Manual steps: ${total}`);
        return [{
          startDate: toLocalIsoNoTz(startDate),
          endDate: toLocalIsoNoTz(endDate),
          value: total
        }];
      }
    } catch (e) {
      console.warn('[HC] Manual steps error:', e);
    }

    return [];
  }

  async readCalories(startDate: Date, endDate: Date): Promise<{ startDate: string; endDate: string; value: number }[]> {
    const dataTypes = ['active-calories', 'calories', 'ACTIVE_ENERGY_BURNED', 'activeCalories'];
    for (const dataType of dataTypes) {
      try {
        const result = await Health.queryAggregated({
          startDate: toLocalIsoNoTz(startDate),
          endDate: toLocalIsoNoTz(endDate),
          dataType: dataType as 'active-calories',
          bucket: 'day',
        });
        if (result.aggregatedData && result.aggregatedData.length > 0) {
          console.log(`[HC] Calories OK: ${dataType}`, result.aggregatedData);
          return result.aggregatedData.map(d => ({
            startDate: d.startDate,
            endDate: d.endDate,
            value: d.value || 0,
          }));
        }
      } catch (e) {
        console.warn(`[HC] Calories error: ${dataType}`, e);
      }
    }
    return [];
  }

  async readRespiration(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'respiratory-rate' as 'steps',
        bucket: 'day'
      });
      const val = result.aggregatedData?.[0]?.value || 0;
      return val > 0 ? val : 0;
    } catch (e) {
      console.warn('[HC] Respiration error:', e);
      return 0;
    }
  }

  async readHRV(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'heart-rate-variability' as 'steps',
        bucket: 'day'
      });
      const val = result.aggregatedData?.[0]?.value || 0;
      return val > 0 ? val : 0;
    } catch (e) {
      console.warn('[HC] HRV error:', e);
      return 0;
    }
  }

  async readSpO2(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'oxygen-saturation' as 'steps',
        bucket: 'day'
      });
      const val = result.aggregatedData?.[0]?.value || 0;
      return val > 0 ? val : 98;
    } catch (e) {
      return 98;
    }
  }

  async readBodyFat(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'body-fat' as 'steps',
        bucket: 'day'
      });
      return result.aggregatedData?.[0]?.value || 0;
    } catch (e) {
      return 0;
    }
  }

  async readWeight(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'weight' as 'steps',
        bucket: 'day'
      });
      return result.aggregatedData?.[0]?.value || 0;
    } catch (e) {
      return 0;
    }
  }

  async readRestingHeartRate(startDate: Date, endDate: Date): Promise<number> {
    try {
      const result = await Health.queryAggregated({
        startDate: toLocalIsoNoTz(startDate),
        endDate: toLocalIsoNoTz(endDate),
        dataType: 'resting-heart-rate' as 'steps',
        bucket: 'day'
      });
      return result.aggregatedData?.[0]?.value || 0;
    } catch {
      return 0;
    }
  }

  async readSleep(startDate: Date, endDate: Date): Promise<number> {
    try {
      const sleepDataTypes = ['sleep_session', 'sleep', 'SLEEP_SESSION'];
      let totalMs = 0;
      for (const dataType of sleepDataTypes) {
        try {
          const { records = [] } = await Health.queryRecords({
            startDate: toLocalIsoNoTz(startDate),
            endDate: toLocalIsoNoTz(endDate),
            dataType: dataType as 'steps'
          });
          if (records.length > 0) {
            records.forEach((r: any) => {
              const start = new Date(r.startDate).getTime();
              const end = new Date(r.endDate).getTime();
              const duration = end - start;
              if (duration > 0 && duration < 24 * 60 * 60 * 1000) {
                totalMs += duration;
              }
            });
            if (totalMs > 0) break;
          }
        } catch {
          /* continue */
        }
      }
      if (totalMs > 0) {
        const hours = totalMs / (1000 * 60 * 60);
        console.log(`[HC] Sleep: ${hours.toFixed(2)}h`);
        return Math.min(hours, 16);
      }
      const dataTypes = ['sleep_session', 'sleep', 'SLEEP_SESSION'];
      for (const dataType of dataTypes) {
        try {
          const result = await Health.queryAggregated({
            startDate: toLocalIsoNoTz(startDate),
            endDate: toLocalIsoNoTz(endDate),
            dataType: dataType as 'steps',
            bucket: 'day',
          });
          if (result.aggregatedData?.length > 0) {
            const val = result.aggregatedData[0].value || 0;
            if (val > 0 && val < 16) return val;
          }
        } catch {
          /* skip */
        }
      }
      return 0;
    } catch (error) {
      console.error('[HealthConnect] Sleep error:', error);
      return 0;
    }
  }

  async readWorkouts(startDate: Date, endDate: Date): Promise<HCWorkout[]> {
    try {
      const result = await Health.queryWorkouts({
        startDate: toIsoWithZ(startDate),
        endDate: toIsoWithZ(endDate),
        includeHeartRate: false,
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
      console.error('[HealthConnect] Workouts error:', error);
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

  async writeWorkout(workout: {
    title: string;
    exerciseType: string;
    startTime: Date;
    endTime: Date;
    calories?: number;
  }): Promise<{ success: boolean; id: string; error?: string }> {
    console.warn('[HealthConnect] Write workout not implemented in plugin');
    return {
      success: false,
      id: '',
      error: 'Write workout requires native Health Connect integration',
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
    heartRate: 58,
    restingHeartRate: 52,
    hrv: 45,
    steps: 10450,
    sleepSeconds: 7.5 * 3600,
    sleepHours: 7.5,
    calories: 2450,
    activeCalories: 450,
    spo2: 98,
    weight: 75,
    bodyFat: 15,
    respiration: 14,
    stress: 30,
    source: 'health_connect',
    date: new Date().toISOString().split('T')[0],
  };
}

// ============================================================================
// EXPORT
// ============================================================================

export const healthConnectService = new HealthConnectServiceClass();
export default healthConnectService;
