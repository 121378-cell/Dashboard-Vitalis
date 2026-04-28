import React from 'react';

interface ReadinessResult {
  score: number;
  status: string;
  recommendation: string;
  components: {
    hrv?: number;
    sleep?: number;
    stress?: number;
    rhr?: number;
    load?: number;
  };
  overtraining_risk?: boolean;
}

interface Props {
  readiness: ReadinessResult | null;
}

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'excellent':
      return '#4ADE80';
    case 'good':
      return '#E8FF47';
    case 'moderate':
      return '#FB923C';
    case 'poor':
    case 'rest':
      return '#F87171';
    default:
      return '#94A3B8';
  }
};

const getColor = (score: number): string => {
  if (score >= 85) return '#4ADE80';
  if (score >= 70) return '#E8FF47';
  if (score >= 50) return '#FB923C';
  return '#F87171';
};

export const ReadinessDial: React.FC<Props> = ({ readiness }) => {
  const score = readiness?.score ?? 0;
  const status = readiness?.status ?? 'no_data';
  const recommendation = readiness?.recommendation ?? '';
  const components = readiness?.components ?? {};
  const overtrainingRisk = readiness?.overtraining_risk ?? false;

  const color = readiness ? getColor(score) : '#94A3B8';
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Build tooltip content with component scores
  const tooltipContent = Object.entries(components)
    .filter(([key]) => ['hrv', 'sleep', 'stress', 'rhr'].includes(key))
    .map(([key, value]) => {
      const labels: Record<string, string> = {
        hrv: 'HRV',
        sleep: 'Sueño',
        stress: 'Estrés',
        rhr: 'FC Reposo',
      };
      return `${labels[key] || key}: ${value}`;
    })
    .join(' | ');

  return (
    <div className="relative flex flex-col items-center justify-center p-4">
      {/* Tooltip */}
      {tooltipContent && (
        <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 bg-[var(--color-surface)] px-2 py-1 rounded text-xs text-[var(--color-text-muted)] whitespace-nowrap z-10">
          {tooltipContent}
        </div>
      )}

      {/* Overtraining risk badge */}
      {overtrainingRisk && (
        <div className="absolute -top-1 right-0 flex items-center gap-1 bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full text-xs font-medium border border-red-500/30">
          ⚠️ Riesgo sobreentrenamiento
        </div>
      )}

      {/* Dial */}
      <svg className="w-32 h-32 transform -rotate-90" style={{ filter: readiness ? `drop-shadow(0 0 8px ${color}40)` : 'none' }}>
        <circle
          cx="64" cy="64" r={radius}
          stroke="var(--color-surface-high)"
          strokeWidth="8"
          fill="transparent"
          className="text-surface-variant/20"
        />
        <circle
          cx="64" cy="64" r={radius}
          stroke={color}
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-1000"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>

      {/* Score and status */}
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-black" style={{ color }}>
          {score}
        </span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-text-muted)]">
          {status}
        </span>
      </div>

      {/* Recommendation */}
      {recommendation && (
        <p className="text-xs text-center mt-3 px-3 text-[var(--color-text)] max-w-[200px] leading-relaxed">
          {recommendation}
        </p>
      )}
    </div>
  );
};
