// Weekly Training Plan Types
export interface WeeklyPlan {
  id: number;
  user_id: string;
  week_start: string;
  week_end: string;
  generated_at: string;
  status: 'active' | 'completed' | 'skipped' | 'archived';
  objective: string;
  structure_name?: string;
  week_number?: number;
  plan_data?: any;
  sessions: TrainingSession[];
}

export interface TrainingSession {
  id: number;
  plan_id?: number;
  day: number;
  day_index?: number;
  day_name: string;
  scheduled_date: string;
  exercises: PlanExercise[];
  exercises_data?: PlanExercise[];
  completed: boolean;
  actual_data?: any;
  skipped?: boolean;
  notes?: string;
  readiness_score?: number | null;
  mcgill_warmup?: {
    name: string;
    exercises: Array<Record<string, unknown>>;
    notes: string;
  };
}

export interface PlanExercise {
  name: string;
  sets: number;
  reps: number | string;
  target_weight: number;
  target_reps: number;
  rpe_target?: number;
  intensity_percentage?: number;
  progression_note?: string;
  rest?: string;
  tempo?: string;
  notes?: string;
  superset_with?: string;
  drop_set?: boolean;
  drop_set_note?: string;
  week_number?: number;
}

export interface PersonalRecord {
  id: number;
  user_id: string;
  exercise_name: string;
  weight: number;
  reps: number;
  rpe?: number;
  date: string;
  source: 'auto' | 'manual' | 'workout';
  notes?: string;
}

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

export interface WeeklyStats {
  week_start: string;
  week_end: string;
  total_sessions: number;
  completed_sessions: number;
  skipped_sessions: number;
  completion_rate: number;
  total_duration_minutes: number;
  total_exercises: number;
}

// Recovery & Injury Prevention Types
export type AlertLevelType = 'optimal' | 'caution' | 'warning' | 'stop';

export interface RecoveryAlert {
  level: AlertLevelType;
  reason: string;
  indicator: string;
  value?: number | string | null;
  threshold?: number | string | null;
  action_required: string;
}

export interface RecoveryStatus {
  alert_level: AlertLevelType;
  alerts: RecoveryAlert[];
  readiness_penalty: number;
  active_injuries: InjuryRecord[];
  zones_to_avoid: string[];
  recommendations: string[];
  forecast_risk: number;
}

export interface RecoverySessionData {
  type: string;
  duration_min: number;
  exercises: string[];
  message?: string | null;
  optional: string[];
  alert_level: AlertLevelType;
}

export interface InjuryRecord {
  id: number;
  date: string;
  zone?: string | null;
  content: string;
  pain_level: number;
  type: string;
  importance: number;
  is_active: boolean;
  tags: string[];
}

export interface InjuryPattern {
  zone: string;
  recurrence_gap_days: number;
  first_date: string;
  last_date: string;
}

export interface InjuryPatternsResponse {
  zone_frequency: Record<string, number>;
  patterns: InjuryPattern[];
  insights: string[];
  total_injuries: number;
}

export interface PainReport {
  zone: string;
  pain_level: number;
  pain_type: 'agudo' | 'sordo' | 'ardor' | 'fatiga';
  notes?: string;
}

// Analytics Types
export interface CorrelationData {
  r: number | null;
  label: string;
  strength: string;
}

export interface RestImpactData {
  optimal_rest_days: number;
  average_readiness_after: number;
  breakdown: Record<string, number>;
}

export interface BestTrainingTime {
  best_hour: number | null;
  best_hour_label?: string;
  avg_rpe_at_best?: number;
  message?: string;
  all_hours?: Record<string, number>;
}

export interface CorrelationsResponse {
  status: 'ok' | 'accumulating';
  days_available?: number;
  days_required?: number;
  days_analyzed?: number;
  message?: string;
  correlations: {
    sleep_to_hrv: CorrelationData;
    hrv_to_performance: CorrelationData;
    rest_days_to_readiness: RestImpactData;
    best_training_time: BestTrainingTime;
  };
  insights: InsightItem[];
}

export interface InsightItem {
  id: string;
  importance: 'alta' | 'media' | 'baja';
  text: string;
  correlation_r?: number | null;
  suggestion?: string;
}

export interface ReadinessForecastDay {
  date: string;
  weekday: string;
  predicted_score: number;
  confidence: number;
}

export interface ReadinessForecastResponse {
  status: 'ok' | 'accumulating';
  days_available?: number;
  days_analyzed?: number;
  message?: string;
  forecasts: ReadinessForecastDay[];
}

export interface PlateauEntry {
  exercise: string;
  weeks_stagnant: number;
  current_weight: number;
  slope_per_week: number;
  suggestion: string;
}

export interface PlateausResponse {
  status: 'ok' | 'no_data' | 'progressing';
  message?: string;
  plateaus: PlateauEntry[];
}

export interface OptimalVolumeResponse {
  status: 'ok' | 'accumulating' | 'insufficient_variation';
  optimal_volume_min?: number | null;
  optimal_sessions_per_week?: number;
  message?: string;
  weeks_available?: number;
  data_points?: number;
}

export interface MonthlyInsightsResponse {
  status: 'ok' | 'accumulating';
  generated_at: string;
  insights: InsightItem[];
  correlations_summary: Record<string, unknown>;
  plateaus: PlateauEntry[];
  optimal_volume: OptimalVolumeResponse;
}

// Biometrics Types
export interface Biometrics {
  id?: number;
  user_id?: string;
  date?: string;
  source?: string;
  readiness?: number;
  status?: string;
  overtraining?: boolean;
  training_status?: string;
  recovery_time?: number;
  hrv_status?: string;
  hrv?: number | null;
  hrv_baseline?: number;
  heartRate?: number | null;
  heart_rate?: number | null;
  resting_hr?: number | null;
  rhr_baseline?: number;
  sleep?: number | null;
  stress?: number | null;
  steps?: number | null;
  calories?: number | null;
  calories_total?: number | null;
  calories_workouts?: number | null;
  spo2?: number | null;
  respiration?: number | null;
  weight?: number | null;
  body_fat?: number | null;
  sleep_seconds?: number | null;
}

export interface ReadinessScore {
  score: number;
  status: 'excellent' | 'good' | 'moderate' | 'poor' | 'rest' | 'no_data';
  recommendation?: string;
  baseline_days?: number;
  component_scores?: Record<string, number>;
  overtraining_risk?: boolean;
}

export const READINESS_THRESHOLDS = {
  excellent: 80,
  good: 65,
  moderate: 50,
  poor: 35,
} as const;

// Chat Types
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  provider?: string;
  timestamp?: string;
}

// Session Plan Types (for Chat session generation)
export interface SessionPlan {
  session_id?: string;
  session_name: string;
  date?: string;
  readiness?: number;
  estimated_duration_min?: number;
  coach_notes?: string;
  warmup?: string;
  cooldown?: string;
  exercises: SessionExercise[];
}

export interface SessionExercise {
  name: string;
  muscle_group: string;
  sets: ExerciseSet[];
}

export interface ExerciseSet {
  set_number: number;
  reps: number;
  weight_kg: number;
  rpe_target?: number;
  rest_seconds?: number;
  tempo?: string;
  actual_reps?: number;
  actual_weight_kg?: number;
  actual_rpe?: number;
  status?: 'pending' | 'completed' | 'partial' | 'failed';
}

// Exercise selector type
export interface Exercise {
  id: string;
  name: string;
  muscle_group: string;
  type: string;
}

// Daily Briefing
export interface DailyBriefing {
  briefing: string;
  generated_at?: string;
}

// PDF Document
export interface PDFDocument {
  id: string;
  name: string;
  summary: string;
  analyzing?: boolean;
  uploaded_at?: string;
}

// Athlete Profile
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

// Health Connect Biometrics (from native plugin)
export interface HCBiometrics {
  heartRate: number | null;
  restingHeartRate: number | null;
  hrv: number | null;
  steps: number | null;
  sleepSeconds: number | null;
  sleepHours: number | null;
  calories: number | null;
  activeCalories?: number | null;
  bodyFat: number | null;
  respiration: number | null;
  stress: number | null;
  spo2: number | null;
  weight: number | null;
  source: 'health_connect' | 'cache' | 'demo';
  date: string;
}

// Garmin Auth Types
export interface GarminAuthStatus {
  authenticated: boolean;
  last_sync?: string;
}

export interface GarminLoginRequest {
  email: string;
  password: string;
  user_id?: string;
}

// Sync Result
export interface SyncResult {
  garmin?: boolean;
  wger?: boolean;
  hevy?: boolean;
  errors?: string[];
}

// Memory Entry
export interface MemoryEntry {
  id: number;
  type: string;
  content: string;
  date: string;
  importance: number;
  tags?: string[];
  source?: string;
  created_at?: string;
}

// App Tab
export type AppTab = 'home' | 'chat' | 'train' | 'progress' | 'setup';

// Session Service Types
export interface TrainingSessionFull extends TrainingSession {
  session_name?: string;
  estimated_duration_min?: number;
  coach_notes?: string;
  warmup?: string;
  cooldown?: string;
}

export interface GenerateSessionResponse {
  session_id: string;
  session: TrainingSessionFull;
  message?: string;
}

export interface ShouldTrainToday {
  should_train: boolean;
  reason: string;
  readiness_score?: number;
  recommendation?: string;
}

// Workout Type
export interface Workout {
  id: number;
  source?: string;
  external_id?: string;
  name?: string;
  description?: string;
  date?: string;
  duration?: number;
  calories?: number;
}