// Health Connect Hook
// ===================
// Hook for managing Health Connect permissions and data

import { useState, useEffect, useCallback } from 'react';
import { useAtlasStore } from '../store/atlasStore';
import healthConnectService from '../services/healthConnectService';
import { biometricsService } from '../services/biometricsService';

export const useHealthConnect = () => {
  const { 
    hcAvailable, 
    hcPermissionsGranted,
    setHcAvailable, 
    setHcPermissionsGranted,
    setBiometrics,
  } = useAtlasStore();
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if Health Connect is available
  const checkAvailability = useCallback(async () => {
    const available = await healthConnectService.initialize();
    setHcAvailable(available);
    return available;
  }, [setHcAvailable]);

  // Request permissions
  const requestPermissions = useCallback(async () => {
    if (!hcAvailable) return false;
    
    setIsLoading(true);
    try {
      const granted = await healthConnectService.ensurePermissions();
      setHcPermissionsGranted(granted);
      return granted;
    } catch (err) {
      setError('Failed to request permissions');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [hcAvailable, setHcPermissionsGranted]);

  // Sync Health Connect data to backend
  const syncData = useCallback(async () => {
    if (!hcAvailable || !hcPermissionsGranted) return false;
    
    setIsLoading(true);
    try {
      const data = await healthConnectService.readTodayBiometrics();
      if (data) {
        // Post to backend
        await biometricsService.postBiometrics(data);
        // Update local state
        setBiometrics({
          steps: data.steps,
          heart_rate: data.heartRate,
          hrv: data.hrv,
          calories: data.calories,
          sleep: data.sleepHours,
          sleep_seconds: data.sleepSeconds,
          respiration: data.respiration,
          spo2: data.spo2,
          weight: data.weight,
          body_fat: data.bodyFat,
          resting_hr: data.restingHeartRate,
          date: data.date,
          source: 'health_connect',
        });
        return true;
      }
      return false;
    } catch (err) {
      setError('Failed to sync Health Connect data');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [hcAvailable, hcPermissionsGranted, setBiometrics]);

  // Initialize on mount
  useEffect(() => {
    checkAvailability();
  }, [checkAvailability]);

  return {
    isAvailable: hcAvailable,
    hasPermissions: hcPermissionsGranted,
    isLoading,
    error,
    checkAvailability,
    requestPermissions,
    syncData,
  };
};

export default useHealthConnect;
