// Weekly Training Plan Types
export interface WeeklyPlan {
  id: number;
  user_id: string;
  week_start: string;
  week_end: string;
  generated_at: string;
  status: 'active' | 'completed' | 'skipped' | 'archived';
  objective: string;
  plan_data: any;
}

export interface TrainingSession {
  id: number;
  plan_id: number;
  day_index: number;
  day_name: string;
  scheduled_date: string;
  exercises_data: PlanExercise[];
  completed: boolean;
  actual_data?: any;
  skipped: boolean;
  notes?: string;
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