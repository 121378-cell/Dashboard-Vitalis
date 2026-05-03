import { motion } from 'framer-motion';
import type { ReadinessForecastDay } from '../../types';

interface ForecastWidgetProps {
  forecasts: ReadinessForecastDay[];
  isLoading?: boolean;
}

const SCORE_COLORS: Record<string, { bar: string; text: string; bg: string }> = {
  high: { bar: 'bg-emerald-400', text: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  medium: { bar: 'bg-yellow-400', text: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  low: { bar: 'bg-red-400', text: 'text-red-400', bg: 'bg-red-400/10' },
};

function getScoreLevel(score: number): string {
  if (score >= 65) return 'high';
  if (score >= 40) return 'medium';
  return 'low';
}

export const ForecastWidget = ({ forecasts, isLoading }: ForecastWidgetProps) => {
  if (isLoading) {
    return (
      <div className="rounded-xl bg-white/5 border border-white/10 p-4 space-y-3">
        <div className="h-4 w-32 bg-white/10 rounded animate-pulse" />
        <div className="flex gap-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex-1 h-20 bg-white/5 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!forecasts.length) {
    return (
      <div className="rounded-xl bg-white/5 border border-white/10 p-4 text-center">
        <p className="text-sm text-[var(--color-text-muted)]">
          Acumulando datos para predicción...
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm">🔮</span>
        <h3 className="text-sm font-semibold text-[var(--color-text)]">
          Predicción de Readiness
        </h3>
      </div>

      <div className="flex gap-2.5">
        {forecasts.map((day, i) => {
          const level = getScoreLevel(day.predicted_score);
          const colors = SCORE_COLORS[level];
          const barWidth = `${day.predicted_score}%`;
          const confidenceOpacity = day.confidence;

          return (
            <motion.div
              key={day.date}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex-1 rounded-lg bg-white/5 p-2.5 text-center"
              style={{ opacity: 0.4 + confidenceOpacity * 0.6 }}
            >
              <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">
                {day.weekday.slice(0, 3)}
              </p>
              <p className={`text-xl font-bold ${colors.text} mt-1`}>
                {day.predicted_score}
              </p>
              <div className="w-full h-1.5 bg-white/10 rounded-full mt-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: barWidth }}
                  transition={{ delay: 0.3 + i * 0.1, duration: 0.6 }}
                  className={`h-full rounded-full ${colors.bar}`}
                />
              </div>
              <div className="flex items-center justify-center gap-1 mt-1.5">
                <div
                  className="h-1 rounded-full bg-[var(--color-text-subtle)]"
                  style={{ width: `${day.confidence * 100}%`, opacity: 0.5 }}
                />
                <span className="text-[9px] text-[var(--color-text-subtle)]">
                  {Math.round(day.confidence * 100)}%
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      <p className="text-[10px] text-[var(--color-text-subtle)] mt-2.5 text-center">
        Confianza disminuye a mayor distancia temporal
      </p>
    </div>
  );
};

export default ForecastWidget;
