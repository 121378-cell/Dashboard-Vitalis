// Metric Card Component
// ======================
// Individual metric display card

import { motion } from 'framer-motion';

interface MetricCardProps {
  icon: string;
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'success' | 'warning' | 'danger' | 'default';
}

export const MetricCard = ({ 
  icon, 
  label, 
  value, 
  unit, 
  trend = 'neutral',
  color = 'default'
}: MetricCardProps) => {
  const colorClasses = {
    success: 'text-[var(--color-success)]',
    warning: 'text-[var(--color-warning)]',
    danger: 'text-[var(--color-danger)]',
    default: 'text-[var(--color-text)]',
  };

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-xl p-3 flex items-center gap-3"
    >
      <div className="w-10 h-10 rounded-lg bg-[var(--color-surface-high)] flex items-center justify-center text-xl">
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-xs text-[var(--color-text-muted)]">{label}</p>
        <div className="flex items-baseline gap-1">
          <span className={`text-lg font-semibold font-display ${colorClasses[color]}`}>
            {value || '--'}
          </span>
          {unit && (
            <span className="text-xs text-[var(--color-text-muted)]">{unit}</span>
          )}
        </div>
      </div>
      <span className="text-xs text-[var(--color-text-subtle)]">{trendIcons[trend]}</span>
    </motion.div>
  );
};

export default MetricCard;
