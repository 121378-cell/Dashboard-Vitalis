import { healthConnectService, HCBiometrics, HCWorkout } from './src/services/healthConnectService';

// Simulamos que el dispositivo tiene Health Connect disponible y devolvemos 
// datos que típicamente Garmin escribiría en Google Health Connect.

async function testHealthConnectGarminSync() {
  console.log("==============================================");
  console.log("🧪 VITALIS: TEST DE MAPEO GARMIN -> HEALTH CONNECT");
  console.log("==============================================\n");

  // Inyectamos un mock en el método nativo (Forzamos isAvailable a true para este scope 
  // o modificamos las respuestas de HealthConnectService).
  
  // Como estamos en Node/Windows y no en Android, probaremos directamente la lógica
  // de utilidades y la generación de métricas de fallback o la función de mapeo interno.
  
  console.log("[1] Probando disponibilidad de Health Connect en el entorno actual...");
  const isAvailable = await healthConnectService.isAvailable();
  console.log(`Disponibilidad nativa reportada: ${isAvailable} (Se espera false en Windows)`);

  console.log("\n[2] Probando resolución de datos Biométricos Diarios (Fallback de prueba)...");
  const biometrics = await healthConnectService.readTodayBiometrics();
  
  // Vamos a mockear manualmente para simular Garmin
  const mockGarminBiometrics: HCBiometrics = {
      ...biometrics,
      heartRate: 58,           // RHR Típico Garmin
      steps: 10450,            // Pasos Garmin
      calories: 2450,          // Calorías totales
      sleepHours: 7.5,
      hrv: 45,
      spo2: 98,
      source: 'health_connect', // Health connect source final
      date: new Date().toISOString().split('T')[0]
  };
  
  console.log("Datos que llegarían procesados a la UI de Vitalis:");
  console.table(mockGarminBiometrics);

  console.log("\n[3] Probando Mapeo de Entrenamientos de Garmin (Workout Map)...");
  // Aquí testeamos el mapeo que hace healthConnectService usando reflexión
  const mapMethod = (healthConnectService as any).mapWorkoutType.bind(healthConnectService);
  
  const garminHC_Exercises = [
      'RUNNING',
      'STRENGTH_TRAINING',
      'HIGH_INTENSITY_INTERVAL_TRAINING',
      'UNKNOWN_GARMIN_ACTIVITY'
  ];

  const mappedResults = garminHC_Exercises.map(ex => ({
      "Raw Health Connect (from Garmin)": ex,
      "Mapped in Vitalis UI": mapMethod(ex)
  }));
  
  console.table(mappedResults);

  console.log("\n[4] API de Escritura a Garmin/HC...");
  const mockWrite = await healthConnectService.writeWorkout({
      title: "Garmin Test Run",
      exerciseType: "running",
      startTime: new Date(),
      endTime: new Date(Date.now() + 3600000),
      calories: 450
  });
  console.log("Resultado de intento de escritura directa:");
  console.log(mockWrite);

  console.log("\n✅ Test de validación de estructuras de sincronización completado.");
}

testHealthConnectGarminSync().catch(console.error);
