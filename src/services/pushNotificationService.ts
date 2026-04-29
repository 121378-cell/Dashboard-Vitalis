import { PushNotifications } from '@capacitor/push-notifications';
import { LocalNotifications } from '@capacitor/local-notifications';
import { apiService } from './apiService';

export class PushNotificationService {
  private initialized = false;

  async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      // Request permission for push notifications
      const permissionStatus = await PushNotifications.requestPermissions();
      if (permissionStatus.receive === 'granted') {
        // Register with FCM to get the token
        await PushNotifications.register();

        // Add listeners for push notifications
        this.setupListeners();

        this.initialized = true;
        console.log('[PushNotificationService] Initialized successfully');
      } else {
        console.warn('[PushNotificationService] Permission to receive push notifications denied');
      }
    } catch (error) {
      console.error('[PushNotificationService] Failed to initialize', error);
    }
  }

  private setupListeners() {
    // Listen for registration (token)
    PushNotifications.addListener('registration', async (token) => {
      console.log('[PushNotificationService] Registration token:', token.value);
      // Send token to backend
      await this.registerToken(token.value);
    });

    // Listen for incoming push notifications
    PushNotifications.addListener('pushNotificationReceived', async (notification) => {
      console.log('[PushNotificationService] Push notification received:', notification);
      // Show local notification so user sees it immediately if app is in foreground
      await this.showLocalNotification(notification.title, notification.body, notification.data);
    });

    // Listen for when user taps on a notification
    PushNotifications.addListener('pushNotificationActionPerformed', async (notification) => {
      console.log('[PushNotificationService] Push notification action performed:', notification);
      // Handle action if needed (e.g., navigate to specific screen)
    });

    // Handle registration errors
    PushNotifications.addListener('registrationError', async (error) => {
      console.error('[PushNotificationService] Registration error:', error);
    });
  }

  private async registerToken(fcmToken: string) {
    try {
      // Send token to backend
      await apiService.post('/notifications/register', { fcm_token: fcmToken });
      console.log('[PushNotificationService] FCM token registered with backend');
    } catch (error) {
      console.error('[PushNotificationService] Failed to register FCM token with backend:', error);
    }
  }

  private async showLocalNotification(title: string, body: string, data: any = {}) {
    try {
      // Create a unique ID for the notification
      const id = Math.floor(Math.random() * 10000);

      await LocalNotifications.schedule({
        notifications: [
          {
            id,
            title,
            body,
            // Add data if needed
            extra: data,
          }
        ]
      });

      console.log('[PushNotificationService] Local notification shown:', { id, title, body });
    } catch (error) {
      console.error('[PushNotificationService] Failed to show local notification:', error);
    }
  }

  // Method to manually trigger token refresh (if needed)
  async refreshToken() {
    try {
      await PushNotifications.unregister();
      await PushNotifications.register();
      console.log('[PushNotificationService] Token refresh initiated');
    } catch (error) {
      console.error('[PushNotificationService] Failed to refresh token:', error);
    }
  }

  // Method to remove all pending local notifications (if needed)
  async clearLocalNotifications() {
    try {
      await LocalNotifications.cancelAll();
      console.log('[PushNotificationService] Cleared all local notifications');
    } catch (error) {
      console.error('[PushNotificationService] Failed to clear local notifications:', error);
    }
  }
}

// Export singleton instance
export const pushNotificationService = new PushNotificationService();