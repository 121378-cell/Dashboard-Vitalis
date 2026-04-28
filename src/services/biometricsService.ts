// ATLAS Biometrics Service
// ==========================
// Handles all biometrics data: fetch from backend, post from Health Connect

import api from './api';
import { Biometrics, ReadinessScore, HCBiometrics } from '../types';

export const biometricsService = {
  // Fetch biometrics for a specific date (default: today)
  async getBiometrics(dateStr?: string): Promise<Biometrics | null> {
    try {
      const targetDate = dateStr || new Date().toISOString().split('T')[0];
      const response = await api.get('/biometrics/', {
        params: { date_str: targetDate }
      });
      return response.data;
    } catch (error) {
      console.error('[Biometrics] Fetch failed:', error);
      return null;
    }
  },

  // Post biometrics data (from Health Connect)
  async postBiometrics(data: HCBiometrics): Promise<boolean> {
    try {
      await api.post('/biometrics/', {
        steps: data.steps,
        heart_rate: data.heartRate,
        hrv: data.hrv,
        calories: data.calories,
        sleep_hours: data.sleepHours,
        sleep_seconds: data.sleepSeconds,
        respiration: data.respiration,
        spo2: data.spo2,
        weight: data.weight,
        body_fat: data.bodyFat,
        resting_hr: data.restingHeartRate,
        source: 'health_connect',
        date: data.date,
      });
      return true;
    } catch (error) {
      console.error('[Biometrics] Post failed:', error);
      return false;
    }
  },

  // Get readiness score
  async getReadiness(): Promise<ReadinessScore | null> {
    try {
      const response = await api.get('/readiness/');
      return response.data;
    } catch (error) {
      console.error('[Readiness] Fetch failed:', error);
      return null;
    }
  },
};

export default biometricsService;
