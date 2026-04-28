// ATLAS Data Hook
// =================
// Main hook for fetching and managing all app data

import { useEffect, useCallback } from 'react';
import { useAtlasStore } from '../store/atlasStore';
import { biometricsService } from '../services/biometricsService';
import { sessionService } from '../services/sessionService';
import { Biometrics, ReadinessScore, DailyBriefing } from '../types';

export const useAtlasData = () => {
  const {
    biometrics,
    readiness,
    briefing,
    todaySession,
    setBiometrics,
    setReadiness,
    setBriefing,
    setTodaySession,
    setLoading,
    setOffline,
  } = useAtlasStore();

  // Load biometrics and readiness
  const loadBiometrics = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    try {
      const [bioData, readyData] = await Promise.all([
        biometricsService.getBiometrics(),
        biometricsService.getReadiness(),
      ]);
      
      if (bioData) setBiometrics(bioData);
      if (readyData) setReadiness(readyData);
      setOffline(false);
    } catch (error) {
      console.error('[useAtlasData] Load biometrics failed:', error);
      setOffline(true);
    } finally {
      setLoading(false);
    }
  }, [setBiometrics, setReadiness, setLoading, setOffline]);

  // Load today's session
  const loadTodaySession = useCallback(async () => {
    try {
      const session = await sessionService.getTodaySession();
      if (session) setTodaySession(session);
    } catch (error) {
      console.error('[useAtlasData] Load session failed:', error);
    }
  }, [setTodaySession]);

  // Load briefing
  const loadBriefing = useCallback(async () => {
    try {
      // Try to get from cache first if offline
      const cached = localStorage.getItem('atlas_briefing_cache');
      if (cached) {
        const parsed = JSON.parse(cached);
        setBriefing(parsed);
      }
      
      // Fetch fresh from backend
      const response = await fetch('/api/v1/ai/daily-briefing');
      if (response.ok) {
        const data = await response.json();
        setBriefing(data);
        localStorage.setItem('atlas_briefing_cache', JSON.stringify(data));
      }
    } catch (error) {
      console.error('[useAtlasData] Load briefing failed:', error);
    }
  }, [setBriefing]);

  // Initial load
  useEffect(() => {
    loadBiometrics();
    loadTodaySession();
    loadBriefing();
  }, [loadBiometrics, loadTodaySession, loadBriefing]);

  return {
    biometrics,
    readiness,
    briefing,
    todaySession,
    loadBiometrics,
    loadTodaySession,
    loadBriefing,
    refreshAll: async () => {
      await Promise.all([loadBiometrics(true), loadTodaySession(), loadBriefing()]);
    },
  };
};

export default useAtlasData;
