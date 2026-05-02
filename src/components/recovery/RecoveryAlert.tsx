import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { RecoveryStatus, RecoverySessionData, AlertLevelType } from '../../types';
import { recoveryService } from '../../services/recoveryService';

interface RecoveryAlertProps {
  status: RecoveryStatus | null;
  session: RecoverySessionData | null;
  isLoading?: boolean;
  onAcknowledge?: () => void;
}

const ALERT_COLORS: Record<AlertLevelType, { bg: string; border: string; text: string; icon: string; pulse: string }> = {
  optimal: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', icon: '✓', pulse: '' },
  caution: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/40', text: 'text-yellow-400', icon: '⚠', pulse: 'animate-pulse' },
  warning: { bg: 'bg-orange-500/10', border: 'border-orange-500/40', text: 'text-orange-400', icon: '🔶', pulse: 'animate-pulse' },
  stop: { bg: 'bg-red-500/10', border: 'border-red-500/40', text: 'text-red-400', icon: '🛑', pulse: 'animate-pulse' },
};

const ALERT_LABELS: Record<AlertLevelType, string> = {
  optimal: 'Estado Óptimo',
  caution: 'Precaución',
  warning: 'Alerta Naranja',
  stop: 'Alerta Roja — Descanso Obligatorio',
};

export const RecoveryAlert = ({ status, session, isLoading, onAcknowledge }: RecoveryAlertProps) => {
  const [showSession, setShowSession] = useState(false);
  const [acknowledging, setAcknowledging] = useState(false);
  const [ackAction, setAckAction] = useState('');
  const [showAckForm, setShowAckForm] = useState(false);

  if (!status || status.alert_level === 'optimal') return null;

  const colors = ALERT_COLORS[status.alert_level];
  const isHigh = status.alert_level === 'warning' || status.alert_level === 'stop';

  const handleAcknowledge = async (alertIndicator: string, alertReason: string) => {
    if (!ackAction.trim()) return;
    setAcknowledging(true);
    try {
      await recoveryService.acknowledgeAlert({
        alert_indicator: alertIndicator,
        alert_reason: alertReason,
        user_action: ackAction.trim(),
      });
      setShowAckForm(false);
      setAckAction('');
      onAcknowledge?.();
    } catch {
      // silent
    } finally {
      setAcknowledging(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        transition={{ duration: 0.3 }}
        className={`rounded-2xl border-2 ${colors.border} ${colors.bg} backdrop-blur-md overflow-hidden ${isHigh ? 'shadow-lg' : ''}`}
      >
        {/* Header */}
        <div className="px-4 py-3 flex items-center gap-3 border-b border-white/5">
          <span className={`text-2xl ${colors.pulse}`}>{colors.icon}</span>
          <div className="flex-1 min-w-0">
            <h3 className={`font-display font-bold ${colors.text} text-lg`}>
              {ALERT_LABELS[status.alert_level]}
            </h3>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              Riesgo estimado: {Math.round(status.forecast_risk * 100)}%
              {status.readiness_penalty > 0 && (
                <span className="ml-2 text-red-400">
                  −{Math.round(status.readiness_penalty)} readiness
                </span>
              )}
            </p>
          </div>
          {isHigh && (
            <div className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
          )}
        </div>

        {/* Alerts list */}
        <div className="px-4 py-3 space-y-2">
          {status.alerts.map((alert, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className={`text-xs mt-0.5 ${colors.text}`}>
                {alert.level === 'stop' ? '🔴' : alert.level === 'warning' ? '🟠' : '🟡'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--color-text)]">{alert.reason}</p>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {alert.action_required}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowAckForm(true);
                  setAckAction('');
                }}
                className="text-xs px-2 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors shrink-0"
              >
                OK
              </button>
            </div>
          ))}

          {/* Acknowledge form */}
          <AnimatePresence>
            {showAckForm && status.alerts.length > 0 && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-2 border-t border-white/5">
                  <p className="text-xs text-[var(--color-text-muted)] mb-2">
                    ¿Qué vas a hacer al respecto? (requerido)
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={ackAction}
                      onChange={(e) => setAckAction(e.target.value)}
                      placeholder="Ej: Tomaré un día de descanso..."
                      className="flex-1 text-sm px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-[var(--color-text)] placeholder:text-[var(--color-text-subtle)] focus:outline-none focus:border-[var(--color-primary)]"
                    />
                    <button
                      onClick={() => handleAcknowledge(status.alerts[0].indicator, status.alerts[0].reason)}
                      disabled={!ackAction.trim() || acknowledging}
                      className="px-3 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium disabled:opacity-40 hover:brightness-110 transition-all"
                    >
                      {acknowledging ? '...' : 'Confirmar'}
                    </button>
                  </div>
                  {status.alert_level === 'stop' && (
                    <p className="text-xs text-red-400 mt-2">
                      ATLAS no diagnostica — si el dolor persiste, consulta a un profesional médico.
                    </p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Recommendations */}
        {status.recommendations.length > 0 && (
          <div className="px-4 py-3 border-t border-white/5">
            <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
              Recomendaciones
            </p>
            <ul className="space-y-1">
              {status.recommendations.map((rec, i) => (
                <li key={i} className="text-xs text-[var(--color-text-muted)] flex items-start gap-1.5">
                  <span className="mt-0.5">•</span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recovery session button */}
        {isHigh && session && (
          <div className="px-4 py-3 border-t border-white/5">
            <button
              onClick={() => setShowSession(!showSession)}
              className="w-full py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-medium text-[var(--color-text)] transition-colors flex items-center justify-center gap-2"
            >
              <span>🧘</span>
              {showSession ? 'Ocultar sesión de recuperación' : 'Ver sesión de recuperación'}
            </button>

            <AnimatePresence>
              {showSession && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 space-y-3">
                    {session.message && (
                      <p className="text-sm text-[var(--color-primary)] font-medium">
                        {session.message}
                      </p>
                    )}
                    {session.duration_min > 0 && (
                      <p className="text-xs text-[var(--color-text-muted)]">
                        Duración: {session.duration_min} min
                      </p>
                    )}
                    {session.exercises.length > 0 && (
                      <ul className="space-y-1.5">
                        {session.exercises.map((ex, i) => (
                          <li key={i} className="text-sm text-[var(--color-text)] flex items-start gap-2">
                            <span className="text-[var(--color-primary)] mt-0.5">›</span>
                            {ex}
                          </li>
                        ))}
                      </ul>
                    )}
                    {session.optional.length > 0 && (
                      <div className="pt-2 border-t border-white/5">
                        <p className="text-xs text-[var(--color-text-muted)] mb-1">Opcional:</p>
                        <ul className="space-y-1">
                          {session.optional.map((opt, i) => (
                            <li key={i} className="text-xs text-[var(--color-text-muted)] flex items-start gap-1.5">
                              <span>◦</span>
                              {opt}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Active injuries */}
        {status.active_injuries.length > 0 && (
          <div className="px-4 py-3 border-t border-white/5">
            <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
              Lesiones activas
            </p>
            {status.active_injuries.map((inj, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-[var(--color-text)]">
                <span className="text-red-400">●</span>
                <span>{inj.zone?.replace(/_/g, ' ')}</span>
                <span className="text-xs text-[var(--color-text-muted)]">
                  {inj.pain_level}/10
                </span>
              </div>
            ))}
            {status.zones_to_avoid.length > 0 && (
              <p className="text-xs text-orange-400 mt-2">
                Zonas a evitar: {status.zones_to_avoid.map(z => z.replace(/_/g, ' ')).join(', ')}
              </p>
            )}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default RecoveryAlert;
