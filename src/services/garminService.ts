// ATLAS Garmin Service
// ======================
// Garmin authentication, sync, status

import api from './api';
import { GarminAuthStatus, GarminLoginRequest, SyncResult } from '../types';

export const garminService = {
  // Check auth status
  async getAuthStatus(): Promise<GarminAuthStatus> {
    try {
      const response = await api.get('/auth/status');
      return response.data;
    } catch (error) {
      console.error('[Garmin] Auth status failed:', error);
      return { authenticated: false };
    }
  },

  // Login to Garmin
  async login(credentials: GarminLoginRequest): Promise<boolean> {
    try {
      await api.post('/auth/garmin/login', credentials);
      return true;
    } catch (error) {
      console.error('[Garmin] Login failed:', error);
      return false;
    }
  },

  // Disconnect Garmin
  async disconnect(): Promise<boolean> {
    try {
      await api.post('/auth/disconnect');
      return true;
    } catch (error) {
      console.error('[Garmin] Disconnect failed:', error);
      return false;
    }
  },

  // Sync Garmin data
  async sync(): Promise<boolean> {
    try {
      await api.post('/sync/garmin');
      return true;
    } catch (error) {
      console.error('[Garmin] Sync failed:', error);
      return false;
    }
  },

  // Sync all services
  async syncAll(): Promise<SyncResult> {
    const result: SyncResult = { errors: [] };
    
    try {
      await api.post('/sync/garmin');
      result.garmin = true;
    } catch (e) {
      result.garmin = false;
      result.errors?.push('Garmin sync failed');
    }
    
    try {
      await api.post('/sync/wger');
      result.wger = true;
    } catch (e) {
      result.wger = false;
      result.errors?.push('Wger sync failed');
    }
    
    try {
      await api.post('/sync/hevy');
      result.hevy = true;
    } catch (e) {
      result.hevy = false;
      result.errors?.push('Hevy sync failed');
    }
    
    return result;
  },
};

export default garminService;
