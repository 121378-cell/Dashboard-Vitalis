import { useState, useEffect, useRef, useCallback } from 'react';
import { getData, postData } from '../services/api';

export interface AtlasNotification {
  id: number;
  created_at: string | null;
  notification_type: string;
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  channel_app: boolean;
  channel_telegram: boolean;
  channel_system: boolean;
  sent_app: boolean;
  sent_telegram: boolean;
  sent_system: boolean;
  read_at: string | null;
  action_url: string | null;
  metadata: Record<string, unknown> | null;
}

export type NotificationFilter = 'all' | 'unread' | 'training' | 'recovery' | 'reminders';

export interface UseNotificationsOptions {
  pollingInterval?: number;
  onNewNotification?: (notification: AtlasNotification) => void;
}

export interface UseNotificationsReturn {
  notifications: AtlasNotification[];
  unreadCount: number;
  isConnected: boolean;
  filter: NotificationFilter;
  setFilter: (f: NotificationFilter) => void;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
  refetch: () => Promise<void>;
  latestToast: AtlasNotification | null;
  dismissToast: () => void;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'https://atlas-vitalis-backend.fly.dev/api/v1';
const WS_BASE = BACKEND_URL.replace(/^http/, 'ws').replace('/api/v1', '');
const WS_URL = `${WS_BASE}/api/v1/ws/notifications`;

export function useNotifications(options: UseNotificationsOptions = {}): UseNotificationsReturn {
  const { onNewNotification } = options;

  const [notifications, setNotifications] = useState<AtlasNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [filter, setFilter] = useState<NotificationFilter>('all');
  const [latestToast, setLatestToast] = useState<AtlasNotification | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnect = 5;
  const reconnectInterval = 3000;
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchUnread = useCallback(async () => {
    try {
      const data = await getData<AtlasNotification[]>('/notifications/unread?limit=50');
      setNotifications(data);
      setUnreadCount(data.filter((n: AtlasNotification) => !n.read_at).length);
    } catch {
      console.warn('[useNotifications] Error fetching unread');
    }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await getData<{ count: number }>('/notifications/unread-count');
      setUnreadCount(data.count);
    } catch {
      console.warn('[useNotifications] Error fetching unread count');
    }
  }, []);

  const markRead = useCallback(async (id: number) => {
    try {
      await postData('/notifications/mark-read', { id });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      console.warn('[useNotifications] Error marking read');
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await postData('/notifications/mark-read', { all: true });
      setNotifications(prev => prev.map(n => ({ ...n, read_at: n.read_at || new Date().toISOString() })));
      setUnreadCount(0);
    } catch {
      console.warn('[useNotifications] Error marking all read');
    }
  }, []);

  const dismissToast = useCallback(() => {
    setLatestToast(null);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'initial' && Array.isArray(msg.data)) {
            setNotifications(msg.data);
            setUnreadCount(msg.data.filter((n: AtlasNotification) => !n.read_at).length);
          } else if (msg.type === 'notification' && msg.data) {
            const newNotif = msg.data as AtlasNotification;
            setNotifications(prev => [newNotif, ...prev]);
            if (!newNotif.read_at) {
              setUnreadCount(prev => prev + 1);
              setLatestToast(newNotif);
              setTimeout(() => setLatestToast(null), 4000);
            }
            onNewNotification?.(newNotif);
          } else if (msg.type === 'marked_read' && msg.id) {
            setNotifications(prev =>
              prev.map(n => n.id === msg.id ? { ...n, read_at: new Date().toISOString() } : n)
            );
            setUnreadCount(prev => Math.max(0, prev - 1));
          }
        } catch {
          console.warn('[useNotifications] Error parsing WS message');
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (reconnectAttemptsRef.current < maxReconnect) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch {
      setIsConnected(false);
    }
  }, [onNewNotification]);

  useEffect(() => {
    fetchUnread();
    connect();

    const pollInterval = setInterval(fetchUnreadCount, 30000);

    return () => {
      clearInterval(pollInterval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [fetchUnread, fetchUnreadCount, connect]);

  const filteredNotifications = notifications.filter(n => {
    switch (filter) {
      case 'unread': return !n.read_at;
      case 'training': return ['insight', 'plan'].includes(n.notification_type);
      case 'recovery': return ['daily_readiness', 'insight'].includes(n.notification_type);
      case 'reminders': return ['hydration', 'achievement'].includes(n.notification_type);
      default: return true;
    }
  });

  return {
    notifications: filteredNotifications,
    unreadCount,
    isConnected,
    filter,
    setFilter,
    markRead,
    markAllRead,
    refetch: fetchUnread,
    latestToast,
    dismissToast,
  };
}

export default useNotifications;
