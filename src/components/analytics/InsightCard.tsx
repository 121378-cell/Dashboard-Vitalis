import { motion } from 'framer-motion';
import type { InsightItem } from '../../types';

interface InsightCardProps {
  insight: InsightItem;
  onTap?: (insight: InsightItem) => void;
}

const IMPORTANCE_CONFIG = {
  alta: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', icon: '📊' },
  media: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: '📈' },
  baja: { bg: 'bg-gray-500/10', border: 'border-gray-500/30', text: 'text-gray-400', icon: '💡' },
} as const;

export const InsightCard = ({ insight, onTap }: InsightCardProps) => {
  const config = IMPORTANCE_CONFIG[insight.importance] || IMPORTANCE_CONFIG.media;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onTap?.(insight)}
      className={`rounded-xl border ${config.border} ${config.bg} backdrop-blur-sm p-3 cursor-pointer hover:bg-white/5 transition-colors`}
    >
      <div className="flex items-start gap-2.5">
        <span className="text-lg mt-0.5">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[var(--color-text)] leading-relaxed">
            {insight.text}
          </p>
          {insight.suggestion && (
            <p className="text-xs text-[var(--color-primary)] mt-1.5">
              → {insight.suggestion}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className={`text-[10px] font-semibold uppercase tracking-wider ${config.text}`}>
              {insight.importance}
            </span>
            {insight.correlation_r != null && (
              <span className="text-[10px] text-[var(--color-text-subtle)]">
                r={insight.correlation_r}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default InsightCard;
