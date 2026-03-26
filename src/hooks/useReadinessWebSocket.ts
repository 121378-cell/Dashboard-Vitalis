import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Tipos de eventos WebSocket para Readiness Score
 */
export interface ReadinessFactors {
  sleep: number;
  recovery: number;
  strain: number;
  activity_balance: number;
  hr_baseline: number;
}

export interface OverreachingInfo {
  detected: boolean;
  message: string;
  severity: number;
  signals: string[];
}

export interface ReadinessData {
  readiness_score: number;
  status: 'low' | 'medium' | 'high';
  factors: ReadinessFactors;
  recommendation: string;
  overreaching: OverreachingInfo | null;
  timestamp: string;
  user_id: string;
  version: string;
}

export interface WebSocketMessage {
  type: 'initial' | 'readiness_update' | 'status_change' | 'pong' | 'error';
  timestamp?: string;
  data?: ReadinessData;
  change?: number;
  from?: string;
  to?: string;
  message?: string;
}

export interface UseReadinessWebSocketOptions {
  userId?: string;
  token?: string;
  onUpdate?: (data: ReadinessData, change?: number) => void;
  onStatusChange?: (from: string, to: string) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  maxReconnectDelay?: number;
  heartbeatInterval?: number;
}

export interface UseReadinessWebSocketReturn {
  data: ReadinessData | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastUpdate: Date | null;
  reconnectAttempt: number;
  sendMessage: (message: object) => void;
  reconnect: () => void;
  disconnect: () => void;
}

/**
 * Hook para conectar al WebSocket de Readiness Score en tiempo real.
 * 
 * @example
 * ```tsx
 * function BiometricsWidget() {
 *   const { data, isConnected, error, lastUpdate } = useReadinessWebSocket({
 *     userId: 'default_user',
 *     onUpdate: (newData, change) => {
 *       console.log(`Score cambió ${change > 0 ? '+' : ''}${change} puntos`);
 *     },
 *     onStatusChange: (from, to) => {
 *       if (to === 'low') alert('Readiness bajo - considera descansar');
 *     }
 *   });
 * 
 *   return (
 *     <div>
 *       {isConnected ? '🟢' : '🔴'}
 *       {data && <ReadinessBar score={data.readiness_score} />}
 *     </div>
 *   );
 * }
 * ```
 * 
 * Características:
 * - Reconexión automática con backoff exponencial
 * - Heartbeat (ping/pong) para mantener conexión viva
 * - Manejo de errores y estados de conexión
 * - Eventos: initial, readiness_update, status_change, pong
 * 
 * @param options - Configuración del WebSocket
 * @returns Estado de la conexión y datos de readiness
 */
export function useReadinessWebSocket(
  options: UseReadinessWebSocketOptions = {}
): UseReadinessWebSocketReturn {
  const {
    userId = 'default_user',
    token,
    onUpdate,
    onStatusChange,
    onError,
    onConnect,
    onDisconnect,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    maxReconnectDelay = 30000,
    heartbeatInterval = 30000,
  } = options;

  const [data, setData] = useState<ReadinessData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentAttemptRef = useRef(0);

  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001';
  const WS_URL = BACKEND_URL.replace(/^http/, 'ws').replace('/api/v1', '') + '/api/v1/ws/readiness';

  /**
   * Calcula el delay de reconexión con backoff exponencial
   */
  const getReconnectDelay = useCallback(() => {
    const delay = Math.min(
      reconnectInterval * Math.pow(2, currentAttemptRef.current),
      maxReconnectDelay
    );
    return delay;
  }, [reconnectInterval, maxReconnectDelay]);

  /**
   * Envía mensaje al servidor si la conexión está abierta
   */
  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[useReadinessWebSocket] No se puede enviar mensaje - WS no conectado');
    }
  }, []);

  /**
   * Envía ping de heartbeat
   */
  const sendHeartbeat = useCallback(() => {
    sendMessage({ action: 'ping', timestamp: new Date().toISOString() });
  }, [sendMessage]);

  /**
   * Maneja la apertura de conexión
   */
  const handleOpen = useCallback(() => {
    console.log('[useReadinessWebSocket] Conexión establecida');
    setIsConnected(true);
    setIsConnecting(false);
    setError(null);
    currentAttemptRef.current = 0;
    setReconnectAttempt(0);

    // Solicitar datos iniciales
    sendMessage({ action: 'get_current', user_id: userId });

    // Iniciar heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    heartbeatIntervalRef.current = setInterval(sendHeartbeat, heartbeatInterval);

    onConnect?.();
  }, [userId, sendMessage, sendHeartbeat, heartbeatInterval, onConnect]);

  /**
   * Maneja mensajes recibidos del servidor
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'initial':
        case 'readiness_update':
          if (message.data) {
            setData(message.data);
            setLastUpdate(new Date());
            onUpdate?.(message.data, message.change);
          }
          break;

        case 'status_change':
          if (message.from && message.to) {
            onStatusChange?.(message.from, message.to);
            
            // Actualizar status local si hay datos
            if (data) {
              setData(prev => prev ? { ...prev, status: message.to as 'low' | 'medium' | 'high' } : null);
            }
          }
          break;

        case 'pong':
          // Heartbeat recibido, conexión viva
          break;

        case 'error':
          console.error('[useReadinessWebSocket] Error del servidor:', message.message);
          setError(message.message || 'Error del servidor');
          break;

        default:
          console.log('[useReadinessWebSocket] Mensaje desconocido:', message);
      }
    } catch (err) {
      console.error('[useReadinessWebSocket] Error parseando mensaje:', err);
    }
  }, [onUpdate, onStatusChange, data]);

  /**
   * Maneja errores de conexión
   */
  const handleError = useCallback((event: Event) => {
    console.error('[useReadinessWebSocket] Error de conexión:', event);
    setError('Error de conexión WebSocket');
    setIsConnected(false);
    onError?.(event);
  }, [onError]);

  /**
   * Maneja cierre de conexión e inicia reconexión
   */
  const handleClose = useCallback(() => {
    console.log('[useReadinessWebSocket] Conexión cerrada');
    setIsConnected(false);
    
    // Limpiar heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    onDisconnect?.();

    // Intentar reconexión si no alcanzamos el límite
    if (currentAttemptRef.current < reconnectAttempts) {
      const delay = getReconnectDelay();
      currentAttemptRef.current += 1;
      setReconnectAttempt(currentAttemptRef.current);
      
      console.log(`[useReadinessWebSocket] Reconectando en ${delay}ms (intento ${currentAttemptRef.current}/${reconnectAttempts})`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, delay);
    } else {
      setError(`No se pudo reconectar después de ${reconnectAttempts} intentos`);
    }
  }, [reconnectAttempts, getReconnectDelay, onDisconnect]);

  /**
   * Establece la conexión WebSocket
   */
  const connect = useCallback(() => {
    // Cerrar conexión existente si hay
    if (wsRef.current) {
      wsRef.current.close();
    }

    setIsConnecting(true);
    setError(null);

    try {
      // Construir URL con query params
      const url = new URL(WS_URL);
      if (token) url.searchParams.append('token', token);
      
      console.log('[useReadinessWebSocket] Conectando a:', url.toString());
      
      const ws = new WebSocket(url.toString());
      wsRef.current = ws;

      ws.onopen = handleOpen;
      ws.onmessage = handleMessage;
      ws.onerror = handleError;
      ws.onclose = handleClose;
    } catch (err) {
      console.error('[useReadinessWebSocket] Error creando WebSocket:', err);
      setError('Error iniciando conexión WebSocket');
      setIsConnecting(false);
    }
  }, [WS_URL, token, handleOpen, handleMessage, handleError, handleClose]);

  /**
   * Fuerza reconexión manual
   */
  const reconnect = useCallback(() => {
    currentAttemptRef.current = 0;
    setReconnectAttempt(0);
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    connect();
  }, [connect]);

  /**
   * Desconecta manualmente
   */
  const disconnect = useCallback(() => {
    // Limpiar timeout de reconexión
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Limpiar heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    // Cerrar WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  // Conectar al montar el componente
  useEffect(() => {
    connect();

    // Cleanup al desmontar
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Reconectar si cambia el userId
  useEffect(() => {
    if (isConnected) {
      reconnect();
    }
  }, [userId]);

  return {
    data,
    isConnected,
    isConnecting,
    error,
    lastUpdate,
    reconnectAttempt,
    sendMessage,
    reconnect,
    disconnect,
  };
}

export default useReadinessWebSocket;
