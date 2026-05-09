import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { DailyReadinessStatus, DailyReadinessResult, DailyReadinessHistoryEntry } from '../types';

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
