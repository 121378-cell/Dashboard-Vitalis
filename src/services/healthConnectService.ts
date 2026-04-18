import { HealthConnect } from '@capacitor-community/health-connect';

export class HealthConnectService {

  // Verificar disponibilidad
  async isAvailable(): Promise<boolean> {
    try {
      return await HealthConnect.isAvailable();
    } catch {
      return false;
    }
  }

  // Solicitar permisos
  async requestPermissions(readTypes: string[], writeTypes: string[]) {
    return await HealthConnect.requestPermissions({
      readPermissions: readTypes,
      writePermissions: writeTypes,
    });
  }

  // Leer biométricos de hoy
  async readTodayBiometrics() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const [heartRate, hrv, steps, sleep, calories, oxygen] = await Promise.all([
      this.readHeartRate(today, tomorrow),
      this.readHRV(today, tomorrow),
      this.readSteps(today, tomorrow),
      this.readSleep(today, tomorrow),
      this.readCalories(today, tomorrow),
      this.readOxygen(today, tomorrow),
    ]);

    return {
      heartRate,
      hrv,
      steps,
      sleep,
      calories,
      oxygen,
    };
  }

  // Escribir entrenamiento completado
  async writeWorkout(workout: {
    title: string;
    startTime: Date;
    endTime: Date;
    exerciseType: string;
    calories?: number;
  }) {
    return await HealthConnect.writeExercise({
      title: workout.title,
      startTime: workout.startTime.toISOString(),
      endTime: workout.endTime.toISOString(),
      exerciseType: workout.exerciseType,
      calories: workout.calories || 0,
    });
  }

  // Leer historial de últimos 7 días
  async readWeeklyHistory() { 
      return []; 
  }
  
  async readMonthlyHistory() { 
      return []; 
  }

  // Dummies para que compile
  async readHeartRate(start: Date, end: Date) { return null; }
  async readHRV(start: Date, end: Date) { return null; }
  async readSteps(start: Date, end: Date) { return null; }
  async readSleep(start: Date, end: Date) { return null; }
  async readCalories(start: Date, end: Date) { return null; }
  async readOxygen(start: Date, end: Date) { return null; }
}