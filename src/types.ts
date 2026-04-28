export interface Biometrics {
  heartRate: number;
  resting_hr?: number;
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
  source: 'garmin_api' | 'garmin' | 'cache' | 'demo' | 'none' | 'health_connect';
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
  startTime: Date;
  endTime: Date;
  duration: number;
  calories: number;
  steps?: number;
  distance?: number;
  heartRate?: Array<{ bpm: number; time: string }>;
}

// Readiness Score
export interface ReadinessScore {
  score: number | null;
  status: 'excellent' | 'good' | 'moderate' | 'poor' | 'rest' | 'no_data';
  components: {
    hrv?: { value: number; score: number; weight: number; baseline?: number };
    sleep?: { value: number; score: number; weight: number };
    stress?: { value: number; score: number; weight: number };
    resting_hr?: { value: number; score: number; weight: number; baseline?: number };
  };
  baseline_days: number;
  date: string;
}

// Daily Briefing
export interface DailyBriefing {
  briefing: string;
  generated_at?: string;
}

// Memory Entry (LTM)
export interface MemoryEntry {
  id: number;
  type: 'injury' | 'achievement' | 'pattern' | 'preference' | 'milestone';
  content: string;
  date: string;
  importance: number;
  source: string;
}

// Training Session Full
export interface TrainingSessionFull {
  id: string;
  user_id: string;
  date: string;
  status: 'planned' | 'active' | 'completed' | 'cancelled';
  generated_by: string;
  plan?: SessionPlan;
  actual?: {
    exercises: Array<{
      name: string;
      muscle_group: string;
      sets: ExerciseSet[];
    }>;
  };
  session_report?: string;
  garmin_activity_id?: string;
  garmin_hr_avg?: number;
  garmin_hr_max?: number;
  garmin_calories?: number;
  garmin_duration_min?: number;
  created_at: string;
  updated_at: string;
}

// Generate Session Response
export interface GenerateSessionResponse {
  session_id: string;
  date: string;
  status: string;
  plan: SessionPlan;
  should_train: ShouldTrainToday;
  message: string;
}

// Weekly Report
export interface WeeklyReport {
  id: string;
  week_start: string;
  week_end: string;
  report_text?: string;
  metrics?: Record<string, number>;
  next_week_plan?: {
    focus: string;
    sessions: number;
    notes: string;
  };
  created_at: string;
}

// Should Train Today
export interface ShouldTrainToday {
  train: boolean;
  reason: string;
  suggested_type: string;
  readiness: number;
}

// App Tab
export type AppTab = 'home' | 'chat' | 'train' | 'progress' | 'setup';

// Health Connect Types
export interface HCBiometrics {
  steps: number;
  heartRate: number | null;
  hrv: number | null;
  calories: number | null;
  sleepHours: number;
  sleepSeconds: number | null;
  respiration: number | null;
  spo2: number | null;
  weight: number | null;
  bodyFat: number | null;
  restingHeartRate: number | null;
  date: string;
  source: 'health_connect';
}

export interface HCWorkout {
  id: string;
  title: string;
  exerciseType: string;
  startTime: Date;
  endTime: Date;
  duration: number;
  calories: number;
  steps?: number;
  distance?: number;
  heartRate?: Array<{ bpm: number; time: string }>;
}

// Chat Types
export interface ChatRequest {
  messages: Message[];
  system_prompt?: string;
}

export interface ChatResponse {
  content: string;
  provider: string;
  error?: string;
}

// Garmin Types
export interface GarminAuthStatus {
  authenticated: boolean;
}

export interface GarminLoginRequest {
  email: string;
  password: string;
  userId?: string;
}

export interface SyncResult {
  garmin?: boolean;
  wger?: boolean;
  hevy?: boolean;
  errors?: string[];
}

// Readiness Thresholds
export const READINESS_THRESHOLDS = {
  excellent: 85,
  good: 70,
  moderate: 50,
  poor: 30,
} as const;
