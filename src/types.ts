export interface Biometrics {
  heartRate: number;
  hrv: number;
  spo2: number;
  stress: number;
  steps: number;
  sleep: number;
  calories: number;
  respiration: number;
  readiness: number;
  status: 'excellent' | 'good' | 'poor';
  overtraining: boolean;
  source: 'garmin_api' | 'cache' | 'demo';
}

export interface AthleteProfile {
  name: string;
  age: number;
  weight: number;
  height: number;
  goal: string;
  experience: 'principiante' | 'intermedio' | 'avanzado' | 'élite';
  daysPerWeek: number;
  medicalHistory: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  provider?: string;
}

export interface PDFDocument {
  id: string;
  name: string;
  summary: string;
  analyzing: boolean;
}

export interface Workout {
  id: number;
  source: string;
  external_id: string;
  name: string;
  description: string;
  date: string;
  duration: number;
  calories: number;
}
