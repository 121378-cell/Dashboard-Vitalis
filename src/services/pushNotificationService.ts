import { LocalNotifications } from '@capacitor/local-notifications';
import { postData } from './api';

export class PushNotificationService {
  private initialized = false;

  async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      const { display } = await LocalNotifications.requestPermissions();
      if (display === 'granted') {
        this.setupListeners();
        this.initialized = true;
        console.log('[PushNotificationService] Initialized successfully');
      } else {
        console.warn('[PushNotificationService] Permission to receive notifications denied');
      }
    } catch (error) {
      console.error('[PushNotificationService] Failed to initialize', error);
    }
  }

  private setupListeners() {
    LocalNotifications.addListener('localNotificationReceived', async (notification) => {
      console.log('[PushNotificationService] Local notification received:', notification);
    });

    LocalNotifications.addListener('localNotificationActionPerformed', async (notification) => {
      console.log('[PushNotificationService] Local notification action performed:', notification);
    });
  }

  private async registerToken(fcmToken: string) {
    try {
      await postData('/notifications/register', { fcm_token: fcmToken });
      console.log('[PushNotificationService] FCM token registered with backend');
    } catch (error) {
      console.error('[PushNotificationService] Failed to register FCM token with backend:', error);
    }
  }

  private async showLocalNotification(title: string, body: string, data: any = {}) {
    try {
      const id = Math.floor(Math.random() * 10000);

      await LocalNotifications.schedule({
        notifications: [
          {
            id,
            title,
            body,
            extra: data,
          }
        ]
      });

      console.log('[PushNotificationService] Local notification shown:', { id, title, body });
    } catch (error) {
      console.error('[PushNotificationService] Failed to show local notification:', error);
    }
  }

  async clearLocalNotifications() {
    try {
      const pending = await LocalNotifications.getPending();
      if (pending.notifications.length > 0) {
        await LocalNotifications.cancel({ notifications: pending.notifications });
      }
      console.log('[PushNotificationService] Cleared all local notifications');
    } catch (error) {
      console.error('[PushNotificationService] Failed to clear local notifications:', error);
    }
  }
}

export const pushNotificationService = new PushNotificationService();
