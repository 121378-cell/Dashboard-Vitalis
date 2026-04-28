// ATLAS Session Service
// =====================
// Training sessions, weekly reports, session generation

import api from './api';
import { 
  TrainingSessionFull, 
  GenerateSessionResponse, 
  WeeklyReport,
  ShouldTrainToday 
} from '../types';

export const sessionService = {
  // Get today's session
  async getTodaySession(): Promise<TrainingSessionFull | null> {
    try {
      const response = await api.get('/sessions/today');
      return response.data;
    } catch (error) {
      console.error('[Session] Fetch today failed:', error);
      return null;
    }
  },

  // Generate new session for today
  async generateSession(forceType?: string): Promise<GenerateSessionResponse | null> {
    try {
      const response = await api.post('/sessions/generate', null, {
        params: { force_type: forceType }
      });
      return response.data;
    } catch (error) {
      console.error('[Session] Generate failed:', error);
      return null;
    }
  },

  // Get session history
  async getHistory(days: number = 30): Promise<TrainingSessionFull[]> {
    try {
      const response = await api.get('/sessions/history', {
        params: { days }
      });
      return response.data || [];
    } catch (error) {
      console.error('[Session] History fetch failed:', error);
      return [];
    }
  },

  // Save completed session
  async saveSession(sessionId: string, actualData: any): Promise<boolean> {
    try {
      await api.post(`/sessions/${sessionId}/save`, { actual_data: actualData });
      return true;
    } catch (error) {
      console.error('[Session] Save failed:', error);
      return false;
    }
  },

  // Analyze session
  async analyzeSession(sessionId: string): Promise<{ report: string } | null> {
    try {
      const response = await api.post(`/sessions/${sessionId}/analyze`);
      return response.data;
    } catch (error) {
      console.error('[Session] Analyze failed:', error);
      return null;
    }
  },

  // Get should train today recommendation
  async shouldTrainToday(): Promise<ShouldTrainToday | null> {
    try {
      const response = await api.get('/sessions/should-train/today');
      return response.data;
    } catch (error) {
      console.error('[Session] Should train fetch failed:', error);
      return null;
    }
  },

  // Get latest weekly report
  async getWeeklyReport(): Promise<WeeklyReport | null> {
    try {
      const response = await api.get('/sessions/weekly-report/latest');
      return response.data;
    } catch (error) {
      console.error('[Session] Weekly report fetch failed:', error);
      return null;
    }
  },

  // Generate weekly report
  async generateWeeklyReport(): Promise<WeeklyReport | null> {
    try {
      const response = await api.post('/sessions/weekly-report/generate');
      return response.data;
    } catch (error) {
      console.error('[Session] Weekly report generation failed:', error);
      return null;
    }
  },
};

export default sessionService;
