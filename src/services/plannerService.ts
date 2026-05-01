import api from "./api";
import type { WeeklyPlan, TrainingSession, WeeklyStats } from "../types";

export interface CompleteSessionRequest {
  session_id: number;
  actual_data: {
    exercises: Array<{
      name: string;
      sets: Array<{ setNumber: number; weight: number; reps: number; rpe: number; completed: boolean }>;
      totalSets: number;
      avgWeight: number;
      totalReps: number;
    }>;
    completedAt: string;
  };
}

export interface SkipSessionRequest {
  session_id: number;
  reason?: string;
}

export interface UpdatePRRequest {
  exercise_name: string;
  weight: number;
  reps: number;
  rpe?: number;
  notes?: string;
}

export interface RescheduleSessionRequest {
  session_id: number;
  new_date: string;
}

export const plannerService = {
  generateWeek: () =>
    api.post<{ status: string; data: WeeklyPlan; message: string }>(
      "/planner/generate-week"
    ),

  getCurrentWeek: () =>
    api.get<{ status: string; data: WeeklyPlan }>("/planner/current-week"),

  completeSession: (request: CompleteSessionRequest) =>
    api.post<{
      status: string;
      data: { session_id: number; completed: boolean; new_personal_records: Array<Record<string, unknown>> };
    }>("/planner/complete-session", request),

  skipSession: (request: SkipSessionRequest) =>
    api.post<{
      status: string;
      data: { session_id: number; skipped: boolean; notes: string };
    }>("/planner/skip-session", request),

  rescheduleSession: (request: RescheduleSessionRequest) =>
    api.post<{
      status: string;
      data: { session_id: number; old_date: string; new_date: string };
    }>("/planner/reschedule-session", request),

  getPersonalRecords: () =>
    api.get<{
      status: string;
      data: {
        personal_records: Record<string, { id: number; weight: number; reps: number; date: string }>;
        total_exercises: number;
      };
    }>("/planner/personal-records"),

  updatePR: (request: UpdatePRRequest) =>
    api.post<{
      status: string;
      data: {
        id: number;
        exercise_name: string;
        weight: number;
        reps: number;
        rpe: number | null;
        date: string;
        source: string;
      };
    }>("/planner/update-pr", request),

  getWeeklyStats: () =>
    api.get<{ status: string; data: WeeklyStats }>("/planner/weekly-stats"),
};