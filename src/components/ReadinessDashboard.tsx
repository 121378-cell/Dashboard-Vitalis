import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Battery, Heart, Moon, Zap } from 'lucide-react';
import { useDailyReadiness, useRunDailyLoop } from '../hooks/useDashboardData';
import type { DailyReadinessInsight } from '../types';

const PRIORITY_COLORS: Record<string, string> = {
  high: 'text-[var(--color-danger)]',
  medium: 'text-[var(--color-warning)]',
  low: 'text-[var(--color-success)]',
};

const PRIORITY_BG: Record<string, string> = {
  high: 'bg-[var(--color-danger)]/10 border-[var(--color-danger)]/20',
  medium: 'bg-[var(--color-warning)]/10 border-[var(--color-warning)]/20',
  low: 'bg-[var(--color-success)]/10 border-[var(--color-success)]/20',
};

const COLOR_MAP: Record<string, string> = {
  green: '#4ADE80',
  blue: '#60A5FA',
  yellow: '#FB923C',
  red: '#F87171',
};

const CATEGORY_BG: Record<string, string> = {
  green: 'bg-emerald-500/10 border-emerald-500/30',
  blue: 'bg-blue-500/10 border-blue-500/30',
  yellow: 'bg-orange-500/10 border-orange-500/30',
  red: 'bg-red-500/10 border-red-500/30',
};

const SUGGESTION_LABELS: Record<string, string> = {
  mantener: 'Sin cambios',
  subir_intensidad: 'Subir intensidad',
  bajar_intensidad: 'Bajar intensidad',
  descanso_recomendado: 'Descanso recomendado',
};

const INTENSITY_COLORS: Record<string, string> = {
  low: 'text-[var(--color-success)]',
  medium: 'text-[var(--color-primary)]',
  high: 'text-[var(--color-danger)]',
};

function AnimatedCounter({ target, duration = 800 }: { target: number; duration?: number }) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const start = current;
    const diff = target - start;
    const startTime = performance.now();

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(start + diff * eased));
      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [target, duration]);

  return <>{current}</>;
}

function ComponentCard({
  icon: Icon,
  label,
  value,
  unit,
  score,
  maxScore,
}: {
  icon: React.ElementType;
  label: string;
  value: number | null;
  unit: string;
  score: number;
  maxScore: number;
}) {
  const displayValue = value !== null && value !== undefined ? value : '—';
  return (
    <div className="flex flex-col items-center gap-1 p-3 rounded-lg bg-[var(--color-surface)]/50">
      <Icon className="w-4 h-4 text-[var(--color-text-muted)]" />
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className="text-lg font-display font-bold text-[var(--color-text)]">
        {displayValue}
        <span className="text-xs font-body text-[var(--color-text-muted)]">{unit}</span>
      </span>
      <span className="text-xs text-[var(--color-text-muted)]">
        +{score !== null && score !== undefined ? score.toFixed(0) : '—'}/{maxScore}
      </span>
    </div>
  );
}

export const ReadinessDashboard = () => {
  const navigate = useNavigate();
  const { data: status, isLoading } = useDailyReadiness();
  const runLoop = useRunDailyLoop();
  const [isRunning, setIsRunning] = useState(false);

  const handleRunNow = async () => {
    setIsRunning(true);
    try {
      await runLoop.mutateAsync();
    } finally {
      setIsRunning(false);
    }
  };

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6"
      >
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-[var(--color-surface-variant)] rounded w-1/3" />
          <div className="h-20 bg-[var(--color-surface-variant)] rounded" />
          <div className="grid grid-cols-3 gap-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-[var(--color-surface-variant)] rounded" />
            ))}
          </div>
        </div>
      </motion.div>
    );
  }

  if (!status?.has_data) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
            Readiness Hoy
          </h3>
        </div>
        <div className="flex flex-col items-center gap-4 py-6">
          <p className="text-sm text-[var(--color-text-muted)]">
            No hay datos de readiness para hoy
          </p>
          <button
            onClick={handleRunNow}
            disabled={isRunning}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-[var(--color-on-primary)] font-semibold text-sm disabled:opacity-50 hover:brightness-110 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
            {isRunning ? 'Calculando...' : 'Actualizar datos'}
          </button>
        </div>
      </motion.div>
    );
  }

  const score = status.readiness_score ?? 0;
  const color = status.readiness_color ?? 'blue';
  const category = status.readiness_category ?? '—';
  const barColor = COLOR_MAP[color] || COLOR_MAP.blue;
  const components = status.components;
  const insights = status.insights ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-[var(--color-outline-variant)]/20 bg-[var(--color-surface-container)] p-6 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-display font-bold text-[var(--color-text)]">
          Readiness Hoy
        </h3>
        <button
          onClick={handleRunNow}
          disabled={isRunning}
          className="p-1.5 rounded-lg hover:bg-[var(--color-surface-variant)] transition-colors disabled:opacity-50"
          title="Recalcular readiness"
        >
          <RefreshCw className={`w-4 h-4 text-[var(--color-text-muted)] ${isRunning ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className={`flex items-center justify-between p-4 rounded-lg border ${CATEGORY_BG[color] || ''}`}>
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-display font-bold" style={{ color: barColor }}>
              <AnimatedCounter target={score} />
            </span>
            <span className="text-lg text-[var(--color-text-muted)]">/100</span>
          </div>
          <span className="text-sm font-semibold" style={{ color: barColor }}>
            {category}
          </span>
        </div>
        <div className="w-24 h-24 relative">
          <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--color-outline)" strokeWidth="3" />
            <motion.circle
              cx="18" cy="18" r="15.9" fill="none"
              stroke={barColor}
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={`${score} ${100 - score}`}
              initial={{ strokeDasharray: '0 100' }}
              animate={{ strokeDasharray: `${score} ${100 - score}` }}
              transition={{ duration: 1, ease: 'easeOut' }}
              style={{ filter: `drop-shadow(0 0 6px ${barColor}40)` }}
            />
          </svg>
        </div>
      </div>

      <div className="w-full h-2 rounded-full bg-[var(--color-surface-variant)] overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ backgroundColor: barColor }}
        />
      </div>

      {components && (
        <div className="grid grid-cols-4 gap-2">
          <ComponentCard
            icon={Battery}
            label="BB"
            value={components.body_battery.value}
            unit="%"
            score={components.body_battery.score}
            maxScore={35}
          />
          <ComponentCard
            icon={Heart}
            label="RHR"
            value={components.resting_hr.value}
            unit=" bpm"
            score={components.resting_hr.score}
            maxScore={30}
          />
          <ComponentCard
            icon={Moon}
            label="Sueño"
            value={components.sleep.value}
            unit="h"
            score={components.sleep.score}
            maxScore={25}
          />
          <ComponentCard
            icon={Zap}
            label="Stress"
            value={components.stress.value}
            unit=""
            score={components.stress.score}
            maxScore={10}
          />
        </div>
      )}

      {status.adaptation && status.adaptation.suggestion && status.adaptation.suggestion !== 'mantener' && (
        <div className="p-3 rounded-lg bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/20">
          <p className="text-sm font-semibold text-[var(--color-warning)]">
            Adaptación: {SUGGESTION_LABELS[status.adaptation.suggestion] || status.adaptation.suggestion}
          </p>
          {status.adaptation.note && (
            <p className="text-xs text-[var(--color-text-muted)] mt-1">{status.adaptation.note}</p>
          )}
        </div>
      )}

      {insights.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-[var(--color-text-muted)]">Insights</h4>
          {insights.map((insight: DailyReadinessInsight) => (
            <div
              key={insight.id}
              className={`p-3 rounded-lg border ${PRIORITY_BG[insight.priority] || ''}`}
            >
              <p className={`text-sm font-semibold ${PRIORITY_COLORS[insight.priority] || ''}`}>
                {insight.title}
              </p>
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{insight.message}</p>
            </div>
          ))}
        </div>
      )}

      {status.summary_message && (
        <p className="text-xs text-[var(--color-text-muted)] italic">
          {status.summary_message}
        </p>
      )}

      <button
        onClick={() => navigate('/plan')}
        className="text-xs text-[var(--color-primary)] hover:underline"
      >
        Ver plan de entrenamiento →
      </button>
    </motion.div>
  );
};

export default ReadinessDashboard;
