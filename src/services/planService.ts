import api from './api';
import {
  AdaptiveWeeklyPlan,
  GeneratePlanRequest,
  AdaptSessionRequest,
  CompleteSessionRequest,
  ExerciseProgression,
  PlanHistoryEntry,
} from '../types';

const PLAN_BASE = '/plans';

export const planApi = {
  getCurrent: async (): Promise<{ has_plan: boolean; data?: AdaptiveWeeklyPlan }> => {
    const res = await api.get(`${PLAN_BASE}/current`);
    return res.data;
  },

  generate: async (request: GeneratePlanRequest): Promise<AdaptiveWeeklyPlan> => {
    const res = await api.post(`${PLAN_BASE}/generate`, request);
    return res.data.data;
  },

  updateSession: async (sessionId: number, updates: Record<string, unknown>) => {
    const res = await api.put(`${PLAN_BASE}/sessions/${sessionId}`, updates);
    return res.data.data;
  },

  completeSession: async (sessionId: number, request: CompleteSessionRequest) => {
    const res = await api.put(`${PLAN_BASE}/sessions/${sessionId}/complete`, request);
    return res.data.data;
  },

  adaptSession: async (sessionId: number, request: AdaptSessionRequest) => {
    const res = await api.post(`${PLAN_BASE}/sessions/${sessionId}/adapt`, request);
    return res.data.data;
  },

  getSessionProgression: async (sessionId: number): Promise<ExerciseProgression[]> => {
    const res = await api.get(`${PLAN_BASE}/sessions/${sessionId}/progression`);
    return res.data.data.progressions;
  },

  detectCompleted: async (): Promise<number> => {
    const res = await api.post(`${PLAN_BASE}/detect-completed`);
    return res.data.data.detected_count;
  },

  getHistory: async (limit: number = 10): Promise<PlanHistoryEntry[]> => {
    const res = await api.get(`${PLAN_BASE}/history`, { params: { limit } });
    return res.data.data.plans;
  },

  cancelPlan: async (planId: number) => {
    const res = await api.delete(`${PLAN_BASE}/${planId}`);
    return res.data;
  },
};
