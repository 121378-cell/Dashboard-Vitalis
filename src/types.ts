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