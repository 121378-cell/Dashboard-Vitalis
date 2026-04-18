/**
 * Sync Service — Vitalis Companion App
 * 
 * Sincronización bidireccional entre:
 * - Health Connect (móvil) ↔ Backend Vitalis
 * - IndexedDB (offline) ↔ Backend Vitalis
 */

import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001/api/v1';

// ============================================================================
// TYPES
// ============================================================================

export interface SyncQueueItem {
  id?: number;
  type: 'biometrics' | 'workout' | 'plan';
  action: 'create' | 'update' | 'delete';
  data: any;
  createdAt: string;
  synced: boolean;
  retryCount: number;
}

export interface SyncStatus {
  lastSyncBiometrics: string | null;
  lastSyncWorkouts: string | null;
  pendingItems: number;
  isOnline: boolean;
}

// ============================================================================
// OFFLINE STORAGE (IndexedDB via localStorage simulation)
// ============================================================================

class OfflineStorage {
  private prefix = 'vitalis_offline_';

  async save(key: string, data: any): Promise<void> {
    try {
      localStorage.setItem(
        `${this.prefix}${key}`,
        JSON.stringify({ data, timestamp: Date.now() })
      );
    } catch (error) {
      console.error('[OfflineStorage] Save error:', error);
    }
  }

  async get(key: string): Promise<any | null> {
    try {
      const item = localStorage.getItem(`${this.prefix}${key}`);
      if (!item) return null;
      return JSON.parse(item).data;
    } catch (error) {
      console.error('[OfflineStorage] Get error:', error);
      return null;
    }
  }

  async saveQueueItem(item: SyncQueueItem): Promise<void> {
    const queue = await this.getQueue();
    queue.push(item);
    await this.save('sync_queue', queue);
  }

  async getQueue(): Promise<SyncQueueItem[]> {
    return (await this.get('sync_queue')) || [];
  }

  async removeFromQueue(id: number): Promise<void> {
    const queue = await this.getQueue();
    const filtered = queue.filter(item => item.id !== id);
    await this.save('sync_queue', filtered);
  }

  async updateQueueItem(id: number, updates: Partial<SyncQueueItem>): Promise<void> {
    const queue = await this.getQueue();
    const index = queue.findIndex(item => item.id === id);
    if (index !== -1) {
      queue[index] = { ...queue[index], ...updates };
      await this.save('sync_queue', queue);
    }
  }

  async clearQueue(): Promise<void> {
    await this.save('sync_queue', []);
  }
}

// ============================================================================
// SYNC SERVICE
// ============================================================================

class SyncServiceClass {
  private offlineStorage: OfflineStorage;
  private isOnline: boolean = navigator.onLine;
  private syncInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.offlineStorage = new OfflineStorage();

    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.syncAll();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  // ========================================================================
  // STATUS
  // ========================================================================

  async getSyncStatus(): Promise<SyncStatus> {
    const queue = await this.offlineStorage.getQueue();
    return {
      lastSyncBiometrics: await this.offlineStorage.get('last_sync_biometrics'),
      lastSyncWorkouts: await this.offlineStorage.get('last_sync_workouts'),
      pendingItems: queue.filter(item => !item.synced).length,
      isOnline: this.isOnline,
    };
  }

  // ========================================================================
  // BIOMETRICS SYNC (Health Connect → Backend)
  // ========================================================================

  async syncBiometricsToBackend(biometrics: {
    date: string;
    heartRate?: number;
    hrv?: number;
    steps?: number;
    sleep?: number;
    calories?: number;
    spo2?: number;
    weight?: number;
  }): Promise<{ success: boolean; error?: string }> {
    if (!this.isOnline) {
      // Queue for later
      await this.offlineStorage.saveQueueItem({
        type: 'biometrics',
        action: 'create',
        data: biometrics,
        createdAt: new Date().toISOString(),
        synced: false,
        retryCount: 0,
      });
      return { success: false, error: 'Offline - queued for sync' };
    }

    try {
      await axios.post(`${BACKEND_URL}/biometrics/`, biometrics, {
        headers: { 'x-user-id': 'default_user' },
        timeout: 10000,
      });

      await this.offlineStorage.save('last_sync_biometrics', new Date().toISOString());
      return { success: true };
    } catch (error) {
      console.error('[SyncService] Sync biometrics error:', error);
      
      // Queue for retry
      await this.offlineStorage.saveQueueItem({
        type: 'biometrics',
        action: 'create',
        data: biometrics,
        createdAt: new Date().toISOString(),
        synced: false,
        retryCount: 0,
      });

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Sync failed',
      };
    }
  }

  // ========================================================================
  // WORKOUTS SYNC (Vitalis → Backend)
  // ========================================================================

  async syncWorkoutCompleted(workout: {
    sessionName: string;
    date: string;
    duration: number;
    calories: number;
    exercises: { name: string; sets: number; reps: number; weight: number }[];
  }): Promise<{ success: boolean; error?: string }> {
    if (!this.isOnline) {
      await this.offlineStorage.saveQueueItem({
        type: 'workout',
        action: 'create',
        data: workout,
        createdAt: new Date().toISOString(),
        synced: false,
        retryCount: 0,
      });
      return { success: false, error: 'Offline - queued for sync' };
    }

    try {
      await axios.post(`${BACKEND_URL}/workouts/`, workout, {
        headers: { 'x-user-id': 'default_user' },
        timeout: 10000,
      });

      await this.offlineStorage.save('last_sync_workouts', new Date().toISOString());
      return { success: true };
    } catch (error) {
      console.error('[SyncService] Sync workout error:', error);
      
      await this.offlineStorage.saveQueueItem({
        type: 'workout',
        action: 'create',
        data: workout,
        createdAt: new Date().toISOString(),
        synced: false,
        retryCount: 0,
      });

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Sync failed',
      };
    }
  }

  // ========================================================================
  // FETCH PLAN FROM BACKEND
  // ========================================================================

  async fetchTodayPlan(): Promise<any | null> {
    if (!this.isOnline) {
      return this.offlineStorage.get('cached_plan');
    }

    try {
      const response = await axios.get(`${BACKEND_URL}/vitalis/today`, {
        headers: { 'x-user-id': 'default_user' },
        timeout: 15000,
      });

      // Cache for offline
      await this.offlineStorage.save('cached_plan', response.data);
      
      return response.data;
    } catch (error) {
      console.error('[SyncService] Fetch plan error:', error);
      
      // Return cached if available
      const cached = await this.offlineStorage.get('cached_plan');
      return cached || null;
    }
  }

  async fetchWeeklyPlan(): Promise<any | null> {
    if (!this.isOnline) {
      return this.offlineStorage.get('cached_weekly_plan');
    }

    try {
      const response = await axios.get(`${BACKEND_URL}/vitalis/weekly`, {
        headers: { 'x-user-id': 'default_user' },
        timeout: 15000,
      });

      await this.offlineStorage.save('cached_weekly_plan', response.data);
      return response.data;
    } catch (error) {
      console.error('[SyncService] Fetch weekly plan error:', error);
      
      const cached = await this.offlineStorage.get('cached_weekly_plan');
      return cached || null;
    }
  }

  // ========================================================================
  // SYNC QUEUE PROCESSOR
  // ========================================================================

  async syncAll(): Promise<{ synced: number; failed: number }> {
    if (!this.isOnline) {
      return { synced: 0, failed: 0 };
    }

    const queue = await this.offlineStorage.getQueue();
    const pending = queue.filter(item => !item.synced);

    let synced = 0;
    let failed = 0;

    for (const item of pending) {
      try {
        let success = false;

        if (item.type === 'biometrics') {
          const result = await axios.post(`${BACKEND_URL}/biometrics/`, item.data, {
            headers: { 'x-user-id': 'default_user' },
            timeout: 10000,
          });
          success = result.status === 200 || result.status === 201;
        } else if (item.type === 'workout') {
          const result = await axios.post(`${BACKEND_URL}/workouts/`, item.data, {
            headers: { 'x-user-id': 'default_user' },
            timeout: 10000,
          });
          success = result.status === 200 || result.status === 201;
        }

        if (success && item.id) {
          await this.offlineStorage.removeFromQueue(item.id);
          synced++;
        } else if (item.id) {
          await this.offlineStorage.updateQueueItem(item.id, {
            retryCount: item.retryCount + 1,
          });
          failed++;
        }
      } catch (error) {
        console.error('[SyncService] Sync item error:', error);
        if (item.id) {
          await this.offlineStorage.updateQueueItem(item.id, {
            retryCount: item.retryCount + 1,
          });
        }
        failed++;
      }
    }

    return { synced, failed };
  }

  // ========================================================================
  // BACKGROUND SYNC
  // ========================================================================

  startBackgroundSync(intervalMs: number = 5 * 60 * 1000): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }

    this.syncInterval = setInterval(() => {
      if (this.isOnline) {
        this.syncAll();
      }
    }, intervalMs);
  }

  stopBackgroundSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  // ========================================================================
  // CLEAR CACHE
  // ========================================================================

  async clearAllData(): Promise<void> {
    await this.offlineStorage.clearQueue();
    localStorage.removeItem('vitalis_offline_last_sync_biometrics');
    localStorage.removeItem('vitalis_offline_last_sync_workouts');
    localStorage.removeItem('vitalis_offline_cached_plan');
    localStorage.removeItem('vitalis_offline_cached_weekly_plan');
  }
}

// ============================================================================
// EXPORT
// ============================================================================

export const syncService = new SyncServiceClass();
export default syncService;