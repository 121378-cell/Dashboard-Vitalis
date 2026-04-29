import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { Biometrics, ReadinessScore } from '../types';

export const useBiometrics = (dateStr?: string) => {
  return useQuery({
    queryKey: ['biometrics', dateStr],
    queryFn: async () => {
      const response = await api.get('/biometrics/', {
        params: { date_str: dateStr }
      });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
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

export const useMemoryEntries = (days: number = 90, types?: string) => {
  return useQuery({
    queryKey: ['memory', days, types],
    queryFn: async () => {
      const response = await api.get('/memory/summary', {
        params: { days, types }
      });
      return response.data;
    },
    staleTime: 30 * 60 * 1000,
  });
};

export const useAnalytics = (startDate: string, endDate: string) => {
  return useQuery({
    queryKey: ['analytics', startDate, endDate],
    queryFn: async () => {
      const response = await api.get('/analytics/biometrics-range', {
        params: { start_date: startDate, end_date: endDate }
      });
      return response.data;
    },
    staleTime: 10 * 60 * 1000,
  });
};
