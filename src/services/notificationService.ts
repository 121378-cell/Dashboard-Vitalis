import { LocalNotifications } from '@capacitor/local-notifications';

export class NotificationService {
  async initialize() {
    console.log('[NotificationService] Iniciando servicio de notificaciones...');
    try {
      const isGranted = await this.checkPermissions();
      if (!isGranted) {
        await this.requestPermissions();
      }
    } catch (e) {
      console.warn('[NotificationService] Notificaciones nativas no soportadas o emuladas en este entorno (Windows/Web).');
    }
  }

  async checkPermissions() {
    const { display } = await LocalNotifications.checkPermissions();
    return display === 'granted';
  }

  async requestPermissions() {
    const { display } = await LocalNotifications.requestPermissions();
    return display === 'granted';
  }

  // Briefing matutino a una hora específica diaria
  async scheduleMorningBriefing(hour: number = 8, minute: number = 0) {
    try {
      // Configuramos el canal si estamos en Android 8.0+ para personalización de prioridad
      await LocalNotifications.createChannel({
        id: 'morning_briefing',
        name: 'Morning Briefing',
        description: 'Notificaciones sobre tu plan diario',
        importance: 4,
        vibration: true
      });

      // Usamos schedule para programar la alarma diaria (repetitiva)
      await LocalNotifications.schedule({
        notifications: [
          {
            id: 1, // ID reservado para el Briefing 
            title: "☀️ Vitalis Morning Briefing",
            body: "Tu reporte de Readiness y el plan de entrenamiento óptimo para hoy están listos.",
            channelId: 'morning_briefing',
            schedule: {
              // Se repetirá todos los días a esta hora
              on: {
                hour,
                minute
              },
              allowWhileIdle: true
            },
            actionTypeId: "",
            extra: null
          }
        ]
      });
      console.log(`[NotificationService] Briefing matutino agendado (Diario a las ${hour}:${minute.toString().padStart(2, '0')})`);
    } catch (e) {
      console.error('[NotificationService] Fallo al agendar el Morning Briefing', e);
    }
  }

  // Recordatorio antes de entrenar
  async scheduleWorkoutReminder(workoutName: string, scheduledTime: Date) {
    try {
      // Restamos 15 minutos para el aviso temprano
      const notificationTime = new Date(scheduledTime.getTime() - 15 * 60000);
      
      // Si la hora del aviso ya pasó momentáneamente, no agendamos (o disparamos inmediato si es en los próximos 15min)
      if (notificationTime.getTime() < Date.now()) {
         console.log('[NotificationService] La hora del recordatorio ya ha pasado. Omitiendo.');
         return;
      }

      const exactId = Math.floor(Math.random() * 10000) + 2;

      await LocalNotifications.schedule({
        notifications: [
          {
            id: exactId, 
            title: "🏃‍♂️ Es hora de entrenar",
            body: `Prepárate para darlo todo. Tu sesión: "${workoutName}" arranca en 15 minutos.`,
            schedule: {
              at: notificationTime,
              allowWhileIdle: true
            }
          }
        ]
      });
      console.log(`[NotificationService] Recordatorio de session "${workoutName}" agendado exitosamente para: ${notificationTime.toLocaleTimeString()}`);
    } catch (e) {
      console.error('[NotificationService] Fallo al agendar el recordatorio de Workout', e);
    }
  }

  // Capacidad para cancelar notificaciones o limpiar colas pasadas
  async cancelAllPending() {
    const pending = await LocalNotifications.getPending();
    if (pending.notifications.length > 0) {
      await LocalNotifications.cancel({ notifications: pending.notifications });
      console.log(`[NotificationService] Canceladas ${pending.notifications.length} notificaciones pendientes.`);
    }
  }
}

export const notificationService = new NotificationService();
