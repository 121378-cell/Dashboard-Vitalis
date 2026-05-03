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