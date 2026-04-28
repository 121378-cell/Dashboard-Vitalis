// Readiness Dial Component
// ==========================
// Animated semi-circular gauge for readiness score

import { motion } from 'framer-motion';
import { useMemo } from 'react';
import { ReadinessScore, READINESS_THRESHOLDS } from '../../types';

interface ReadinessDialProps {
  readiness: ReadinessScore | null;
  size?: number;
}

export const ReadinessDial = ({ readiness, size = 200 }: ReadinessDialProps) => {
  const score = readiness?.score ?? 0;
  const status = readiness?.status ?? 'no_data';
  
  // Color based on score
  const color = useMemo(() => {
    if (score >= READINESS_THRESHOLDS.excellent) return '#4ADE80';
    if (score >= READINESS_THRESHOLDS.good) return '#E8FF47';
    if (score >= READINESS_THRESHOLDS.moderate) return '#FB923C';
    return '#F87171';
  }, [score]);
  
  // Calculate arc path
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  
  const statusText = {
    excellent: 'Excelente',
    good: 'Bueno',
    moderate: 'Moderado',
    poor: 'Bajo',
    rest: 'Descanso',
    no_data: 'Sin datos',
  }[status];

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size / 1.5 }}>
        {/* Background arc */}
        <svg
          width={size}
          height={size / 1.5}
          viewBox={`0 0 ${size} ${size / 1.5}`}
          className="absolute inset-0"
        >
          <path
            d={`M ${strokeWidth / 2} ${size / 1.5} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 1.5}`}
            fill="none"
            stroke="var(--color-surface-high)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          
          {/* Progress arc */}
          <motion.path
            d={`M ${strokeWidth / 2} ${size / 1.5} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 1.5}`}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: "easeOut" }}
            className="drop-shadow-lg"
            style={{ filter: `drop-shadow(0 0 10px ${color}40)` }}
          />
        </svg>
        
        {/* Score display */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="text-center"
          >
            <span
              className="text-5xl font-bold font-display"
              style={{ color }}
            >
              {score > 0 ? score : '--'}
            </span>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">
              {statusText}
            </p>
          </motion.div>
        </div>
      </div>
      
      {/* Baseline info */}
      {readiness && readiness.baseline_days > 0 && (
        <p className="text-xs text-[var(--color-text-subtle)] mt-2">
          Basado en {readiness.baseline_days} días
        </p>
      )}
    </div>
  );
};

export default ReadinessDial;
