import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useReadinessWebSocket } from '../useReadinessWebSocket';

// Mock WebSocket
const mockWebSocket = {
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1,
};

describe('useReadinessWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.WebSocket = vi.fn(() => mockWebSocket) as any;
  });

  it('initializes with disconnected state', () => {
    const { result } = renderHook(() => useReadinessWebSocket());
    
    expect(result.current.isConnected).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('connects to WebSocket with correct URL', async () => {
    renderHook(() => useReadinessWebSocket({ userId: 'test-user' }));
    
    await waitFor(() => {
      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('ws://localhost:8001/api/v1/ws/readiness')
      );
    });
  });

  it('calls onConnect when connected', async () => {
    const onConnect = vi.fn();
    
    renderHook(() => useReadinessWebSocket({ 
      userId: 'test-user',
      onConnect 
    }));

    // Simulate open
    mockWebSocket.onopen?.(new Event('open'));
    
    await waitFor(() => expect(onConnect).toHaveBeenCalled());
  });

  it('receives and processes readiness data', async () => {
    const onUpdate = vi.fn();
    
    const { result } = renderHook(() => useReadinessWebSocket({ 
      userId: 'test-user',
      onUpdate 
    }));

    // Simulate connection
    mockWebSocket.onopen?.(new Event('open'));
    
    // Simulate data message
    const mockData = {
      readiness_score: 75,
      status: 'high',
      factors: { sleep: 80, recovery: 70, strain: 85, activity_balance: 75, hr_baseline: 90 },
      recommendation: 'Preparado',
      overreaching: null,
      timestamp: new Date().toISOString(),
      user_id: 'test-user',
      version: '2.0'
    };

    mockWebSocket.onmessage?.(new MessageEvent('message', {
      data: JSON.stringify({ type: 'readiness_update', data: mockData, change: 5 })
    }));

    await waitFor(() => {
      expect(result.current.data?.readiness_score).toBe(75);
      expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ readiness_score: 75 }), 5);
    });
  });

  it('handles status change events', async () => {
    const onStatusChange = vi.fn();
    
    renderHook(() => useReadinessWebSocket({ 
      userId: 'test-user',
      onStatusChange 
    }));

    mockWebSocket.onopen?.(new Event('open'));
    
    mockWebSocket.onmessage?.(new MessageEvent('message', {
      data: JSON.stringify({ type: 'status_change', from: 'high', to: 'low' })
    }));

    await waitFor(() => {
      expect(onStatusChange).toHaveBeenCalledWith('high', 'low');
    });
  });

  it('handles connection errors', async () => {
    const onError = vi.fn();
    
    const { result } = renderHook(() => useReadinessWebSocket({ 
      userId: 'test-user',
      onError 
    }));

    mockWebSocket.onerror?.(new Event('error'));

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
      expect(onError).toHaveBeenCalled();
    });
  });

  it('sends heartbeat ping', async () => {
    renderHook(() => useReadinessWebSocket({ 
      userId: 'test-user',
      heartbeatInterval: 100
    }));

    mockWebSocket.onopen?.(new Event('open'));

    await waitFor(() => {
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.stringContaining('"action":"ping"')
      );
    });
  });

  it('allows manual reconnect', async () => {
    const { result } = renderHook(() => useReadinessWebSocket({ userId: 'test-user' }));

    mockWebSocket.onopen?.(new Event('open'));
    
    await waitFor(() => expect(result.current.isConnected).toBe(true));

    result.current.disconnect();
    expect(result.current.isConnected).toBe(false);

    result.current.reconnect();
    
    mockWebSocket.onopen?.(new Event('open'));
    
    await waitFor(() => expect(result.current.isConnected).toBe(true));
  });

  it('updates lastUpdate timestamp on data receive', async () => {
    const { result } = renderHook(() => useReadinessWebSocket({ userId: 'test-user' }));

    mockWebSocket.onopen?.(new Event('open'));
    
    const beforeUpdate = result.current.lastUpdate;

    mockWebSocket.onmessage?.(new MessageEvent('message', {
      data: JSON.stringify({ 
        type: 'readiness_update', 
        data: { readiness_score: 80, status: 'high' } 
      })
    }));

    await waitFor(() => {
      expect(result.current.lastUpdate).not.toEqual(beforeUpdate);
    });
  });
});
