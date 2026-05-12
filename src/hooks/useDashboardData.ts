import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { DailyReadinessStatus, DailyReadinessResult, DailyReadinessHistoryEntry, CreateMasterPlanRequest } from '../types';

export const useBiometrics = (dateStr?: string) => {
  return useQuery({
    queryKey: ['biometrics', dateStr],
    queryFn: async () => {
      const response = await api.get('/biometrics/', {
        params: { date_str: dateStr }
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useReadiness = () => {
  return useQuery({
    queryKey: ['readiness'],
    queryFn: async () => {
      const response = await api.get('/readiness/score');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useReadinessTrend = (days: number = 30) => {
  return useQuery({
    queryKey: ['readiness-trend', days],
    queryFn: async () => {
      const response = await api.get('/readiness/trend', {
        params: { days }
      });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const useReadinessForecast = (days: number = 3) => {
  return useQuery({
    queryKey: ['readiness-forecast', days],
    queryFn: async () => {
      const response = await api.get('/readiness/forecast', {
        params: { days }
      });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const useWorkouts = (limit: number = 20) => {
  return useQuery({
    queryKey: ['workouts', limit],
    queryFn: async () => {
      const response = await api.get('/workouts/', {
        params: { limit }
      });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const useDailyReadiness = () => {
  return useQuery<DailyReadinessStatus>({
    queryKey: ['daily-readiness'],
    queryFn: async () => {
      const response = await api.get('/daily/status');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useRunDailyLoop = () => {
  const queryClient = useQueryClient();
  return useMutation<DailyReadinessResult>({
    mutationFn: async () => {
      const response = await api.post('/daily/run-now');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daily-readiness'] });
    },
  });
};

export const useDailyReadinessHistory = (days: number = 30) => {
  return useQuery<DailyReadinessHistoryEntry[]>({
    queryKey: ['daily-readiness-history', days],
    queryFn: async () => {
      const response = await api.get('/daily/history', { params: { days } });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const useDashboardKpis = () => {
  return useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: async () => {
      const response = await api.get('/dashboard/kpis');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useActivityHeatmap = (weeks: number = 52) => {
  return useQuery({
    queryKey: ['activity-heatmap', weeks],
    queryFn: async () => {
      const response = await api.get('/dashboard/activity-heatmap', { params: { weeks } });
      return response.data;
    },
    staleTime: 30 * 60 * 1000,
  });
};

export const useTrainingDistribution = (days: number = 90) => {
  return useQuery({
    queryKey: ['training-distribution', days],
    queryFn: async () => {
      const response = await api.get('/dashboard/training-distribution', { params: { days } });
      return response.data;
    },
    staleTime: 30 * 60 * 1000,
  });
};

export const useReadinessTrendLine = (days: number = 90) => {
  return useQuery({
    queryKey: ['readiness-trend-line', days],
    queryFn: async () => {
      const response = await api.get('/dashboard/readiness-trend-line', { params: { days } });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const useMuscleVolume = (weeks: number = 12) => {
  return useQuery({
    queryKey: ['muscle-volume', weeks],
    queryFn: async () => {
      const response = await api.get('/dashboard/muscle-volume', { params: { weeks } });
      return response.data;
    },
    staleTime: 30 * 60 * 1000,
  });
};

export const useBiometricsHistory = (days: number = 30, metric?: string) => {
  return useQuery({
    queryKey: ['biometrics-history', days, metric],
    queryFn: async () => {
      const response = await api.get('/biometrics/history', {
        params: { days, metric }
      });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const useRecentWorkouts = (limit: number = 20, activityType?: string) => {
  return useQuery({
    queryKey: ['recent-workouts', limit, activityType],
    queryFn: async () => {
      const response = await api.get('/workouts/recent', {
        params: { limit, activity_type: activityType }
      });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};

export const usePersonalRecords = (exercise?: string) => {
  return useQuery({
    queryKey: ['personal-records', exercise],
    queryFn: async () => {
      const response = await api.get('/workouts/personal-records', {
        params: { exercise }
      });
      return response.data;
    },
    staleTime: 30 * 60 * 1000,
  });
};

export const useCurrentPlan = () => {
  return useQuery({
    queryKey: ['current-plan'],
    queryFn: async () => {
      const response = await api.get('/plans/current');
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useGeneratePlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: Record<string, unknown>) => {
      const response = await api.post('/plans/generate', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['current-plan'] });
    },
  });
};

export const useAdaptSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sessionId, request }: { sessionId: number; request: { user_request: string } }) => {
      const response = await api.post(`/plans/sessions/${sessionId}/adapt`, request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['current-plan'] });
    },
  });
};

export const useCompleteSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sessionId, request }: { sessionId: number; request: { completed: boolean; garmin_activity_id?: string } }) => {
      const response = await api.put(`/plans/sessions/${sessionId}/complete`, request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['current-plan'] });
    },
  });
};

export const useSessionProgression = (sessionId: number | null) => {
  return useQuery({
    queryKey: ['session-progression', sessionId],
    queryFn: async () => {
      const response = await api.get(`/plans/sessions/${sessionId}/progression`);
      return response.data.data.progressions;
    },
    enabled: sessionId !== null,
    staleTime: 10 * 60 * 1000,
  });
};

export const usePlanHistory = (limit: number = 10) => {
  return useQuery({
    queryKey: ['plan-history', limit],
    queryFn: async () => {
      const response = await api.get('/plans/history', { params: { limit } });
      return response.data.data.plans;
    },
    staleTime: 30 * 60 * 1000,
  });
};

export const useActiveMasterPlan = () => {
  return useQuery({
    queryKey: ['active-master-plan'],
    queryFn: async () => {
      const response = await api.get('/master-plan/active');
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useMasterPlanProgress = (masterPlanId: number | null) => {
  return useQuery({
    queryKey: ['master-plan-progress', masterPlanId],
    queryFn: async () => {
      const response = await api.get(`/master-plan/${masterPlanId}/progress`);
      return response.data.data;
    },
    enabled: masterPlanId !== null,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateMasterPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: CreateMasterPlanRequest) => {
      const response = await api.post('/master-plan/create', request);
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-master-plan'] });
    },
  });
};

export const useProposeNextWeek = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (masterPlanId: number) => {
      const response = await api.post(`/master-plan/${masterPlanId}/propose-next-week`);
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-master-plan'] });
      queryClient.invalidateQueries({ queryKey: ['master-plan-progress'] });
    },
  });
};

export const useConfirmWeek = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (weeklyPlanId: number) => {
      const response = await api.post(`/master-plan/weeks/${weeklyPlanId}/confirm`);
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-master-plan'] });
      queryClient.invalidateQueries({ queryKey: ['master-plan-progress'] });
      queryClient.invalidateQueries({ queryKey: ['current-plan'] });
    },
  });
};

export const useCancelMasterPlan = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (masterPlanId: number) => {
      const response = await api.delete(`/master-plan/${masterPlanId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-master-plan'] });
      queryClient.invalidateQueries({ queryKey: ['master-plan-progress'] });
    },
  });
};
