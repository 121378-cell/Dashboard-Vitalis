import Dexie, { Table } from 'dexie';

export interface SyncQueueItem {
  id?: number;
  type: 'biometrics' | 'workouts' | 'plans';
  data: any;
  createdAt: number;
}

export class OfflineStorageDb extends Dexie {
  biometrics!: Table<any, number>;
  workouts!: Table<any, number>;
  plans!: Table<any, number>;
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

  async saveBiometricsLocally(data: any) {
    await this.biometrics.add({ ...data, synced: false });
    await this.syncQueue.add({ type: 'biometrics', data, createdAt: Date.now() });
  }
  
  async saveWorkoutLocally(data: any) {
    await this.workouts.add({ ...data, synced: false });
    await this.syncQueue.add({ type: 'workouts', data, createdAt: Date.now() });
  }

  async getUnsyncedData(): Promise<SyncQueueItem[]> {
    return await this.syncQueue.toArray();
  }

  async markAsSynced(id: number) {
    await this.syncQueue.delete(id);
  }
}

export const offlineStorage = new OfflineStorageDb();
