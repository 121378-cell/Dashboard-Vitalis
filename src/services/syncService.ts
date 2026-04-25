import axios from 'axios';
import { offlineStorage, SyncQueueItem } from './offlineStorage';
import { HCBiometrics, HCWorkout } from './healthConnectService';

// URL única del backend (misma que usa App.tsx)
const RAW_BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.VITE_API_URL ||
  '/api/v1';

const BACKEND_URL = String(RAW_BACKEND_URL).replace(/\/+$/, '');

export class SyncService {
  
  // Sincronizar biométricos locales → backend
  async syncBiometricsToBackend(biometrics: HCBiometrics | any) {
    try {
      const response = await axios.post(`${BACKEND_URL}/biometrics/`, biometrics, {
        headers: { 'x-user-id': 'default_user' }
      });
      return response.data;
    } catch (error) {
      console.warn("[SyncService] API Inaccesible. Fallback a IndexedDB guardando biométricos.");
      await offlineStorage.saveBiometricsLocally(biometrics);
      throw error;
    }
  }

  // Obtener plan de entrenamiento del backend
  async fetchTodayPlan() {
    try {
      const response = await axios.get(`${BACKEND_URL}/sessions/today`, {
        headers: { 'x-user-id': 'default_user' }
      });
      return response.data;
    } catch (error) {
      console.warn("[SyncService] No se pudo descargar el plan de Vitalis Hoy.");
      throw error;
    }
  }

  // Enviar workout completado al backend
  async syncWorkoutCompleted(workout: HCWorkout | any) {
    try {
      const response = await axios.post(`${BACKEND_URL}/workouts/`, workout, {
        headers: { 'x-user-id': 'default_user' }
      });
      return response.data;
    } catch (error) {
      console.warn("[SyncService] API Inaccesible. Fallback a IndexedDB guardando workout.");
      await offlineStorage.saveWorkoutLocally(workout);
      throw error;
    }
  }

  // Sincronización inteligente
  // 1. Si offline → guardar en IndexedDB (manejado en los catch arriba)
  // 2. Si online → hacer sync incremental (este método se invocaría, ej. al volver la conexión)
  async syncAll() {
    if (!navigator.onLine) {
      console.log('[SyncService] Sistema Offline. Sincronización evadida.');
      return;
    }

    const pending = await offlineStorage.getUnsyncedData();
    if (pending.length > 0) {
      console.log(`[SyncService] Iniciando sincronización de ${pending.length} ítems pendientes...`);
    }

    for (const item of pending) {
      try {
        await this.syncItem(item);
        if (item.id) {
          await offlineStorage.markAsSynced(item.id);
        }
      } catch (e) {
        console.error('[SyncService] Fallo sincronizando ítem:', item.id, e);
      }
    }
  }

  private async syncItem(item: SyncQueueItem) {
    if (item.type === 'biometrics') {
      await axios.post(`${BACKEND_URL}/biometrics/`, item.data, {
        headers: { 'x-user-id': 'default_user' }
      });
    } else if (item.type === 'workouts') {
      await axios.post(`${BACKEND_URL}/workouts/`, item.data, {
        headers: { 'x-user-id': 'default_user' }
      });
    }
  }
}

export const syncService = new SyncService();