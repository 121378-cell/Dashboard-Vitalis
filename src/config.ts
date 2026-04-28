// ATLAS Configuration
// ===================

export const BACKEND_URL = 
  import.meta.env.VITE_BACKEND_URL || 
  "https://atlas-vitalis-backend.fly.dev/api/v1";

export const WS_URL = BACKEND_URL.replace(/^http/, 'ws').replace('/api/v1', '') + '/api/v1/ws/readiness';

// Timeouts
export const API_TIMEOUT = 8000; // 8 seconds
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
