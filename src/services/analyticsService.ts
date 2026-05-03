import { getData } from './api';
import type {
  CorrelationsResponse,
  ReadinessForecastResponse,
  PlateausResponse,
  OptimalVolumeResponse,
  MonthlyInsightsResponse,
} from '../types';

const BASE = '/api/v1/analytics';

export const analyticsService = {
  getCorrelations: (days = 90) =>
    getData<CorrelationsResponse>(`${BASE}/correlations`, { days }),

  getReadinessForecast: (daysAhead = 3) =>
    getData<ReadinessForecastResponse>(`${BASE}/readiness-forecast`, { days_ahead: daysAhead }),

  getPlateaus: (exercise?: string, weeks = 6) =>
    getData<PlateausResponse>(`${BASE}/plateaus`, { exercise, weeks }),

  getOptimalVolume: () =>
    getData<OptimalVolumeResponse>(`${BASE}/optimal-volume`),

  getInsights: () =>
    getData<MonthlyInsightsResponse>(`${BASE}/insights`),
};
