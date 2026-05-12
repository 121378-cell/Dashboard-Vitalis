import api from './api';
import {
  MasterPlan,
  MasterPlanProgress,
  CreateMasterPlanRequest,
  AdaptiveWeeklyPlan,
} from '../types';

const MP_BASE = '/master-plan';

export const masterPlanApi = {
  create: async (request: CreateMasterPlanRequest): Promise<{ master_plan: MasterPlan; first_week: AdaptiveWeeklyPlan }> => {
    const res = await api.post(`${MP_BASE}/create`, request);
    return res.data.data;
  },

  getActive: async (): Promise<{ has_plan: boolean; data?: MasterPlan; message?: string }> => {
    const res = await api.get(`${MP_BASE}/active`);
    return res.data;
  },

  getProgress: async (masterPlanId: number): Promise<MasterPlanProgress> => {
    const res = await api.get(`${MP_BASE}/${masterPlanId}/progress`);
    return res.data.data;
  },

  proposeNextWeek: async (masterPlanId: number): Promise<AdaptiveWeeklyPlan> => {
    const res = await api.post(`${MP_BASE}/${masterPlanId}/propose-next-week`);
    return res.data.data;
  },

  confirmWeek: async (weeklyPlanId: number): Promise<{
    id: number;
    week_start: string;
    week_end: string;
    goal: string;
    status: string;
    week_number: number;
    phase_number: number;
    confirmed_by_user: boolean;
    master_plan_current_week: number | null;
  }> => {
    const res = await api.post(`${MP_BASE}/weeks/${weeklyPlanId}/confirm`);
    return res.data.data;
  },

  cancel: async (masterPlanId: number): Promise<void> => {
    await api.delete(`${MP_BASE}/${masterPlanId}`);
  },
};
