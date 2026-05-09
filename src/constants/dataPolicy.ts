export const DATA_POLICY = {
  NEVER_USE_MOCK_IN_PROD: true,
  ALWAYS_FETCH_FROM_API: true,
  SHOW_LOADING_SKELETONS: true,
  SHOW_EMPTY_STATES: true,
  NO_HRV_FR245: true,
  SUPPORTED_BIOMETRICS: ['restingHr', 'sleep', 'stress', 'steps', 'bodyBattery'] as const,
  UNSUPPORTED_BIOMETRICS: ['hrv'] as const,
  FR245_NOTE: 'Forerunner 245 does not provide HRV or Body Battery data',
} as const;

export const API_STALE_TIMES = {
  BIOMETRICS_TODAY: 5 * 60 * 1000,
  BIOMETRICS_HISTORY: 10 * 60 * 1000,
  WORKOUTS: 10 * 60 * 1000,
  READINESS: 5 * 60 * 1000,
  DAILY_STATUS: 5 * 60 * 1000,
  KPI_DASHBOARD: 5 * 60 * 1000,
  HEATMAP: 30 * 60 * 1000,
  DISTRIBUTION: 30 * 60 * 1000,
  PERSONAL_RECORDS: 30 * 60 * 1000,
  INSIGHTS: 30 * 60 * 1000,
} as const;

export const EMPTY_STATES = {
  NO_BIOMETRICS: 'Sync your Garmin device to see biometric trends',
  NO_WORKOUTS: 'No workout data available yet',
  NO_READINESS: 'Run the daily loop to generate readiness scores',
  NO_PRS: 'No personal records logged yet',
  NO_INSIGHTS: 'Acumulando datos para generar insights...',
} as const;
