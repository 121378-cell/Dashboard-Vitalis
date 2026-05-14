// ATLAS Configuration
// ===================

export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  "http://localhost:8005/api/v1";

export const WS_URL = BACKEND_URL.replace(/^http/, 'ws').replace('/api/v1', '') + '/api/v1/ws/readiness';
export const WS_NOTIFICATIONS_URL = BACKEND_URL.replace(/^http/, 'ws').replace('/api/v1', '') + '/api/v1/ws/notifications';

// Timeouts
export const API_TIMEOUT = 45000; // 45 seconds (allows AI generations)
export const HEALTH_CONNECT_TIMEOUT = 10000;

// Cache keys
export const CACHE_KEYS = {
  BIOMETRICS: 'atlas_biometrics_cache',
  BRIEFING: 'atlas_briefing_cache',
  CHAT_HISTORY: 'atlas_chat_history',
  SESSION_TODAY: 'atlas_session_today',
  USER_PROFILE: 'atlas_user_profile',
} as const;

// Design tokens (CSS variables mirrored for JS use)
export const TOKENS = {
  color: {
    primary: '#E8FF47',
    background: '#0A0A0F',
    surface: '#13131A',
    surfaceHigh: '#1C1C26',
    onPrimary: '#0A0A0F',
    text: '#F0F0FF',
    textMuted: '#6B6B8A',
    success: '#4ADE80',
    warning: '#FB923C',
    danger: '#F87171',
  },
  font: {
    display: "'Orbitron', sans-serif",
    body: "'DM Sans', sans-serif",
    mono: "'JetBrains Mono', monospace",
  },
} as const;

// Auth token management (JWT)
const AUTH_TOKEN_KEY = 'ATLAS_JWT_TOKEN';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  try {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } catch {
    console.warn('[Auth] No se pudo guardar el token en localStorage');
  }
}

export function clearAuthToken(): void {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch {
    console.warn('[Auth] No se pudo limpiar el token');
  }
}

// Readiness score thresholds
export const READINESS_THRESHOLDS = {
  excellent: 85,
  good: 70,
  moderate: 50,
  poor: 30,
} as const;

// Tab configuration
export const TABS = [
  { id: 'home', label: 'Inicio', icon: '🏠' },
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'train', label: 'Entrenar', icon: '⚡' },
  { id: 'progress', label: 'Progreso', icon: '📊' },
  { id: 'setup', label: 'Setup', icon: '⚙️' },
] as const;
