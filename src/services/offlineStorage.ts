import Dexie, { Table } from 'dexie';
import type { Biometrics, Workout } from '../types';

export interface SyncQueueItem {
  id?: number;
  type: 'biometrics' | 'workouts' | 'plans';
  data: Record<string, unknown>;
  createdAt: number;
}

export class OfflineStorageDb extends Dexie {
  biometrics!: Table<Biometrics, number>;
  workouts!: Table<Workout, number>;
  plans!: Table<Record<string, unknown>, number>;
  syncQueue!: Table<SyncQueueItem, number>;

  constructor() {
    super('vitalis_offline');

    this.version(1).stores({
      biometrics: '++id, date, synced',
      workouts: '++id, date, synced',
      plans: '++id, date, synced',
      syncQueue: '++id, type, createdAt',
    });
  }

  async saveBiometricsLocally(data: Biometrics) {
    await this.biometrics.add({ ...data, synced: false });
    await this.syncQueue.add({ type: 'biometrics', data: data as unknown as Record<string, unknown>, createdAt: Date.now() });
  }

  async saveWorkoutLocally(data: Workout) {
    await this.workouts.add({ ...data, synced: false });
    await this.syncQueue.add({ type: 'workouts', data: data as unknown as Record<string, unknown>, createdAt: Date.now() });
  }

  async getUnsyncedData(): Promise<SyncQueueItem[]> {
    return await this.syncQueue.toArray();
  }

  async markAsSynced(id: number) {
    await this.syncQueue.delete(id);
  }
}

export const offlineStorage = new OfflineStorageDb();
