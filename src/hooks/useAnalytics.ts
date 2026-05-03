import { useState, useEffect, useCallback } from 'react';
import { analyticsService } from '../services/analyticsService';
import type {
  MonthlyInsightsResponse,
  ReadinessForecastResponse,
  CorrelationsResponse,
} from '../types';

interface AnalyticsData {
  insights: MonthlyInsightsResponse | null;
  forecast: ReadinessForecastResponse | null;
  correlations: CorrelationsResponse | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useAnalytics = (): AnalyticsData => {
  const [insights, setInsights] = useState<MonthlyInsightsResponse | null>(null);
  const [forecast, setForecast] = useState<ReadinessForecastResponse | null>(null);
  const [correlations, setCorrelations] = useState<CorrelationsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [insightsData, forecastData, corrData] = await Promise.allSettled([
        analyticsService.getInsights(),
        analyticsService.getReadinessForecast(),
        analyticsService.getCorrelations(),
      ]);

      if (insightsData.status === 'fulfilled') setInsights(insightsData.value);
      if (forecastData.status === 'fulfilled') setForecast(forecastData.value);
      if (corrData.status === 'fulfilled') setCorrelations(corrData.value);

      const failed = [insightsData, forecastData, corrData].find(
        r => r.status === 'rejected'
      );
      if (failed && failed.status === 'rejected') {
        setError(failed.reason?.message || 'Error loading analytics');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { insights, forecast, correlations, isLoading, error, refresh: fetchAll };
};

export default useAnalytics;
