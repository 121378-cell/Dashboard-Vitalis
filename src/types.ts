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

// Daily Loop / Readiness Dashboard Types
export interface DailyReadinessComponents {
  body_battery: { value: number | null; score: number; weight: string };
  resting_hr: { value: number | null; score: number; weight: string; vs_baseline: number | null };
  sleep: { value: number | null; score: number; weight: string };
  stress: { value: number | null; score: number; weight: string };
}

export interface DailyReadinessInsight {
  id: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  message: string;
}

export interface DailyReadinessSession {
  planned: {
    session_type: string;
    title: string;
    duration_minutes: number | null;
    intensity: string;
  };
  adaptation: {
    suggestion: 'mantener' | 'subir_intensidad' | 'bajar_intensidad' | 'descanso_recomendado';
    note: string;
  };
}

export interface DailyReadinessStatus {
  has_data: boolean;
  date?: string;
  readiness_score?: number;
  readiness_category?: string;
  readiness_color?: 'green' | 'blue' | 'yellow' | 'red';
  components?: DailyReadinessComponents;
  biometrics_source?: string;
  adaptation?: {
    made: boolean;
    suggestion?: string | null;
    note?: string | null;
  };
  insights?: DailyReadinessInsight[];
  summary_message?: string;
  created_at?: string;
  error?: string;
}

export interface DailyReadinessResult extends DailyReadinessStatus {
  today_session?: DailyReadinessSession | null;
}

export interface DailyReadinessHistoryEntry {
  date: string;
  readiness_score: number;
  readiness_category: string;
  readiness_color: string;
  body_battery: number | null;
  resting_heart_rate: number | null;
  sleep_hours: number | null;
  stress_level: number | null;
  components: {
    bb_score: number;
    rhr_score: number;
    sleep_score: number;
    stress_score: number;
  };
  adaptation_made: boolean;
  adaptation_suggestion: string | null;
  adaptation_note: string | null;
  insights: DailyReadinessInsight[];
  biometrics_source: string | null;
  created_at: string;
}

// Chat Context Types
export interface ChatContextMeta {
  data_freshness: string | null;
  plan_active: boolean;
  plan_progress: string | null;
  unread_insights: number;
  readiness_score: number | null;
  readiness_color: 'green' | 'blue' | 'yellow' | 'red' | 'gray';
}

export interface ChatResponse {
  content: string;
  provider: string;
  mode?: string;
  type?: string;
  session_id?: number;
  plan_id?: number;
  context_meta?: ChatContextMeta;
}

export interface WelcomeMessage {
  message: string;
  generated_at: string;
}

// Notification Types
export interface AtlasNotification {
  id: number;
  created_at: string | null;
  notification_type: string;
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  channel_app: boolean;
  channel_telegram: boolean;
  channel_system: boolean;
  sent_app: boolean;
  sent_telegram: boolean;
  sent_system: boolean;
  read_at: string | null;
  action_url: string | null;
  metadata: Record<string, unknown> | null;
}

// Adaptive Training Plan Types
export interface AdaptivePlanSession {
  id: number;
  date: string;
  day_of_week: string;
  session_type: 'strength' | 'running' | 'trail_running' | 'mobility' | 'hiit' | 'rest' | 'active_recovery';
  title: string;
  description: string;
  duration_minutes?: number;
  intensity?: 'low' | 'medium' | 'high';
  exercises?: PlanSessionExercise[];
  running_details?: PlanRunningDetails;
  mobility_details?: PlanMobilityDetails;
  completed: boolean;
  garmin_activity_id?: string;
  user_notes?: string;
  modified_by_user?: boolean;
  adaptation_reason?: string;
}

export interface PlanSessionExercise {
  name: string;
  sets: number;
  reps: string;
  weight_kg: number;
  rest_seconds: number;
  muscle_group: string;
  notes: string;
}

export interface PlanRunningDetails {
  type: string;
  distance_km: number;
  target_pace_min_km: string;
  heart_rate_zone: string;
  structure: string;
}

export interface PlanMobilityDetails {
  focus: string;
  techniques: string[];
  key_exercises: string[];
}

export interface AdaptiveWeeklyPlan {
  plan_id: number;
  week_start: string;
  week_end: string;
  goal: string;
  status: string;
  created_at: string;
  ai_reasoning: string;
  progress: {
    completed: number;
    total: number;
    percentage: number;
  };
  plan: {
    weekly_goal: string;
    reasoning: string;
    total_planned_minutes: number;
    sessions: AdaptivePlanSession[];
    weekly_notes: string;
    nutrition_focus: string;
    sleep_reminder: string;
  };
}

export interface GeneratePlanRequest {
  goal: string;
  week_start?: string;
  training_days?: string[];
  time_available?: Record<string, number>;
  session_types?: string[];
  intensity_preference?: string;
  consider_readiness?: boolean;
  restrictions?: string;
}

export interface AdaptSessionRequest {
  user_request: string;
}

export interface CompleteSessionRequest {
  completed: boolean;
  garmin_activity_id?: string;
}

export interface ExerciseProgression {
  exercise_name: string;
  last_session: {
    date: string | null;
    weight: number | null;
    reps: string | null;
    sets: number | null;
  } | null;
  suggested_weight: number | null;
  suggested_reps: string | null;
  progression_note: string;
  pr_potential: boolean;
  pr_current: number | null;
}

export interface PlanHistoryEntry {
  plan_id: number;
  week_start: string;
  week_end: string;
  goal: string;
  status: string;
  created_at: string;
  completed_sessions: number;
  total_sessions: number;
  completion_percentage: number;
}

// Master Plan Types
export interface MasterPlanPhase {
  phase_number: number;
  name: string;
  description: string;
  start_week: number;
  end_week: number;
  focus: string[];
  intensity: string;
  weekly_volume_hours?: number;
}

export interface MasterPlanMilestone {
  week: number;
  description: string;
  metric: string;
  target: string;
  achieved?: boolean;
}

export interface MasterPlanPreferences {
  preferred_days: string[];
  time_per_session_minutes: number;
  intensity_preference: string;
  restrictions: string | null;
}

export interface MasterPlanWeeklyPlanSummary {
  id: number;
  week_start: string;
  week_end: string;
  goal: string;
  status: string;
  week_number: number;
  phase_number: number;
  confirmed_by_user: boolean;
}

export interface MasterPlan {
  id: number;
  title: string;
  goal: string;
  status: 'active' | 'completed' | 'cancelled';
  start_date: string;
  target_date: string | null;
  total_weeks: number;
  current_week: number;
  completed_weeks: number;
  phases: MasterPlanPhase[];
  current_phase: MasterPlanPhase | null;
  milestones: MasterPlanMilestone[];
  strategy: string;
  preferences: MasterPlanPreferences;
  days_remaining: number | null;
  current_weekly_plan: MasterPlanWeeklyPlanSummary | null;
  next_unconfirmed_week: { id: number; week_number: number; phase_number: number; goal: string } | null;
}

export interface MasterPlanProgress {
  id: number;
  title: string;
  goal: string;
  status: string;
  current_week: number;
  total_weeks: number;
  completed_weeks: number;
  completion_pct: number;
  phase_timeline: MasterPlanPhaseTimeline[];
  milestones: MasterPlanMilestone[];
  days_remaining: number | null;
  start_date: string | null;
  target_date: string | null;
}

export interface MasterPlanPhaseTimeline {
  phase_number: number;
  name: string;
  description: string;
  start_week: number;
  end_week: number;
  focus: string[];
  intensity: string;
  status: 'completed' | 'current' | 'pending';
}

export interface CreateMasterPlanRequest {
  goal: string;
  target_date?: string | null;
  preferred_days?: string[];
  time_per_session_minutes?: number;
  intensity_preference?: string | null;
  restrictions?: string | null;
}