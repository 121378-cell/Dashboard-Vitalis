import { useState, FormEvent } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { BACKEND_URL, setAuthToken, getAuthToken } from '../config';

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
}

async function loginRequest(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${BACKEND_URL}/auth/jwt/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const errorBody = await res.text();
    let message: string;
    try {
      const parsed = JSON.parse(errorBody);
      message = parsed.detail || parsed.message || `Error ${res.status}`;
    } catch {
      message = errorBody || `Error ${res.status}: ${res.statusText}`;
    }
    throw new Error(message);
  }

  return res.json();
}

export const LoginPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // If already logged in, redirect to dashboard
  const existingToken = getAuthToken();
  if (existingToken) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError('Introduce tu email de usuario');
      return;
    }
    if (!password) {
      setError('Introduce tu contraseña');
      return;
    }

    setLoading(true);
    try {
      const data = await loginRequest(email, password);
      setAuthToken(data.access_token);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión al servidor');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background decoration - neon grid */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] bg-[radial-gradient(ellipse_at_center,_rgba(232,255,71,0.03)_0%,_transparent_60%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(232,255,71,0.02)_1px,_transparent_1px),linear-gradient(90deg,rgba(232,255,71,0.02)_1px,_transparent_1px)] bg-[size:60px_60px]" />
        {/* Glow orbs */}
        <div className="absolute top-20 left-1/4 w-64 h-64 bg-[var(--color-primary)]/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-20 right-1/4 w-80 h-80 bg-[var(--color-info)]/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-[var(--color-primary)] rounded-2xl shadow-2xl shadow-[var(--color-primary)]/20 mb-4">
            <span className="text-3xl">⚡</span>
          </div>
          <h1 className="text-3xl font-[Orbitron] font-bold tracking-tighter text-[var(--color-text)]">
            ATLAS <span className="text-[var(--color-primary)]">AI</span>
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1 font-medium">
            Personal Trainer Inteligente
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-outline)] rounded-2xl p-8 shadow-2xl shadow-black/40">
          <h2 className="text-xl font-bold text-[var(--color-text)] mb-1">
            Iniciar Sesión
          </h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-6">
            Accede a tu panel de entrenamiento
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[var(--color-text)] mb-1.5">
                Email / Usuario
              </label>
              <input
                id="email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@email.com"
                autoComplete="username"
                autoFocus
                disabled={loading}
                className="w-full px-4 py-3 bg-[var(--color-background)] border border-[var(--color-outline)] rounded-xl text-[var(--color-text)] placeholder-[var(--color-text-subtle)] hover:border-[var(--color-outline-strong)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50 focus:border-[var(--color-primary)] transition-all duration-200 disabled:opacity-50"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[var(--color-text)] mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                disabled={loading}
                className="w-full px-4 py-3 pr-12 bg-[var(--color-background)] border border-[var(--color-outline)] rounded-xl text-[var(--color-text)] placeholder-[var(--color-text-subtle)] hover:border-[var(--color-outline-strong)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50 focus:border-[var(--color-primary)] transition-all duration-200 disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors p-1"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/30 rounded-xl px-4 py-3 flex items-start gap-3 animate-[fadeIn_0.3s_ease]">
                <span className="text-lg flex-shrink-0 mt-0.5">⚠️</span>
                <p className="text-sm text-[var(--color-danger)] font-medium">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-[var(--color-primary)] text-[var(--color-on-primary)] font-bold rounded-xl hover:bg-[var(--color-primary-dim)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="inline-block w-5 h-5 border-2 border-[var(--color-on-primary)]/30 border-t-[var(--color-on-primary)] rounded-full animate-spin" />
                  <span>Autenticando...</span>
                </>
              ) : (
                <>
                  <span>🔐</span>
                  <span>Acceder al Panel</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center mt-6 text-xs text-[var(--color-text-subtle)]">
          ATLAS AI Personal Trainer v2.0 &mdash; {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
