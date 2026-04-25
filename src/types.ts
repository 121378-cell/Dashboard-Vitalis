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
  status: 'excellent' | 'good' | 'poor' | 'high' | 'medium' | 'low';
  overtraining: boolean;
  source: 'garmin_api' | 'garmin' | 'cache' | 'demo' | 'none';
  // Optional fields from backend
  training_status?: string;
  recovery_time?: number;
  hrv_status?: string;
  rhr_baseline?: number;
  hrv_baseline?: number;
  // Cumulative totals (workouts + baseline)
  calories_baseline?: number;
  calories_workouts?: number;
  calories_total?: number;
  workout_duration?: number;
  workout_count?: number;
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

// Session Plan Types for ATLAS Training
export interface ExerciseSet {
  set_number: number;
  reps: number;
  weight_kg: number;
  rpe_target: number;
  rest_seconds: number;
  tempo: string;
  notes: string;
  // Editable fields by user:
  actual_reps?: number;
  actual_weight_kg?: number;
  actual_rpe?: number;
  status?: 'completed' | 'partial' | 'failed' | 'pending';
}

export interface Exercise {
  name: string;
  muscle_group: string;
  sets: ExerciseSet[];
}

export interface SessionPlan {
  session_id?: string;
  session_name: string;
  date?: string;
  estimated_duration_min: number;
  warmup: string;
  exercises: Exercise[];
  cooldown: string;
  coach_notes: string;
  readiness: number;
}
