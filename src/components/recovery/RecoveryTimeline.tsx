import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import type { InjuryRecord, InjuryPatternsResponse } from '../../types';
import { recoveryService } from '../../services/recoveryService';

interface RecoveryTimelineProps {
  refreshTrigger?: number;
}

export const RecoveryTimeline = ({ refreshTrigger }: RecoveryTimelineProps) => {
  const [injuries, setInjuries] = useState<InjuryRecord[]>([]);
  const [patterns, setPatterns] = useState<InjuryPatternsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [historyRes, patternsRes] = await Promise.all([
          recoveryService.getInjuryHistory(),
          recoveryService.getInjuryPatterns(),
        ]);
        setInjuries(historyRes.data);
        setPatterns(patternsRes.data);
      } catch {
        // silent
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [refreshTrigger]);

  const getZoneColor = (zone: string) => {
    const colors: Record<string, string> = {
      neck: '#A78BFA',
      shoulder_left: '#818CF8',
      shoulder_right: '#818CF8',
      upper_back: '#6366F1',
      lower_back: '#4F46E5',
      elbow_left: '#EC4899',
      elbow_right: '#EC4899',
      wrist_left: '#F472B6',
      wrist_right: '#F472B6',
      chest: '#14B8A6',
      core: '#2DD4BF',
      hip_left: '#F59E0B',
      hip_right: '#F59E0B',
      knee_left: '#EF4444',
      knee_right: '#EF4444',
      ankle_left: '#F97316',
      ankle_right: '#F97316',
      hand_left: '#F472B6',
      hand_right: '#F472B6',
    };
    return colors[zone] || '#6B7280';
  };

  const getPainBarWidth = (level: number) => `${(level / 10) * 100}%`;

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const calculateDaysSince = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      return Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
    } catch {
      return null;
    }
  };

  if (isLoading) {
    return (
      <div className="glass-high rounded-2xl p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-5 w-48 bg-white/5 rounded" />
          <div className="h-20 bg-white/5 rounded-xl" />
          <div className="h-20 bg-white/5 rounded-xl" />
        </div>
      </div>
    );
  }

  if (injuries.length === 0) {
    return (
      <div className="glass-high rounded-2xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">📋</span>
          <h3 className="font-display font-semibold text-[var(--color-text)]">
            Historial de Lesiones
          </h3>
        </div>
        <div className="text-center py-8">
          <p className="text-3xl mb-2">💪</p>
          <p className="text-sm text-[var(--color-text-muted)]">
            Sin lesiones reportadas. ¡Sigue así!
          </p>
          <p className="text-xs text-[var(--color-text-subtle)] mt-1">
            Reporta cualquier molestia para que ATLAS pueda protegerte.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-high rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-outline)] flex items-center gap-2">
        <span className="text-xl">📋</span>
        <h3 className="font-display font-semibold text-[var(--color-text)]">
          Historial de Lesiones
        </h3>
        <span className="ml-auto text-xs text-[var(--color-text-muted)] bg-white/5 px-2 py-1 rounded-full">
          {injuries.length} registros
        </span>
      </div>

      {/* Injury Pattern Insights */}
      {patterns && patterns.insights.length > 0 && (
        <div className="p-4 border-b border-white/5 bg-orange-500/5">
          <p className="text-xs font-semibold text-orange-400 uppercase tracking-wider mb-2">
            Patrones detectados
          </p>
          <ul className="space-y-1">
            {patterns.insights.map((insight, i) => (
              <li key={i} className="text-sm text-[var(--color-text-muted)] flex items-start gap-1.5">
                <span className="text-orange-400 mt-0.5">▸</span>
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Timeline */}
      <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
        {injuries
          .filter(inj => inj.type === 'injury')
          .map((injury, index) => {
            const daysSince = calculateDaysSince(injury.date);
            const zoneColor = getZoneColor(injury.zone || '');
            const isActive = injury.is_active;

            return (
              <motion.div
                key={injury.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`relative flex gap-3 p-3 rounded-xl ${
                  isActive ? 'bg-red-500/5 border border-red-500/20' : 'bg-white/5'
                }`}
              >
                {/* Timeline dot */}
                <div className="flex flex-col items-center shrink-0">
                  <div
                    className="w-3 h-3 rounded-full mt-1 shrink-0"
                    style={{
                      backgroundColor: zoneColor,
                      boxShadow: isActive ? `0 0 8px ${zoneColor}60` : 'none',
                    }}
                  />
                  {index < injuries.filter(i => i.type === 'injury').length - 1 && (
                    <div className="w-px flex-1 mt-1 bg-white/10" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-[var(--color-text)]">
                      {(injury.zone || 'zona desconocida').replace(/_/g, ' ')}
                    </span>
                    {isActive && (
                      <span className="text-xs px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 font-medium">
                        Activa
                      </span>
                    )}
                    {daysSince !== null && (
                      <span className="text-xs text-[var(--color-text-subtle)] ml-auto shrink-0">
                        {daysSince === 0 ? 'Hoy' : daysSince === 1 ? 'Ayer' : `hace ${daysSince}d`}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-[var(--color-text-muted)] mb-2">
                    {injury.content}
                  </p>

                  {/* Pain level bar */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: getPainBarWidth(injury.pain_level) }}
                        transition={{ duration: 0.5, delay: index * 0.05 }}
                        className="h-full rounded-full"
                        style={{
                          backgroundColor: zoneColor,
                          opacity: injury.pain_level > 5 ? 1 : 0.6,
                        }}
                      />
                    </div>
                    <span className="text-xs text-[var(--color-text-subtle)] shrink-0">
                      {injury.pain_level}/10
                    </span>
                  </div>

                  {/* Date */}
                  <p className="text-xs text-[var(--color-text-subtle)] mt-1.5">
                    {formatDate(injury.date)}
                  </p>
                </div>
              </motion.div>
            );
          })}
      </div>

      {/* Recurrence patterns */}
      {patterns && patterns.patterns.length > 0 && (
        <div className="p-4 border-t border-white/5">
          <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
            Recurrencias
          </p>
          <div className="space-y-1.5">
            {patterns.patterns.slice(0, 5).map((pattern, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                <span className="text-orange-400">↻</span>
                <span>{pattern.zone.replace(/_/g, ' ')}</span>
                <span className="text-[var(--color-text-subtle)]">—</span>
                <span>Recurre cada ~{pattern.recurrence_gap_days} días</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zone frequency chart */}
      {patterns && Object.keys(patterns.zone_frequency).length > 1 && (
        <div className="p-4 border-t border-white/5">
          <p className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
            Frecuencia por zona
          </p>
          <div className="space-y-1.5">
            {Object.entries(patterns.zone_frequency)
              .sort(([, a], [, b]) => b - a)
              .map(([zone, count]) => (
                <div key={zone} className="flex items-center gap-2">
                  <span className="text-xs text-[var(--color-text)] w-24 truncate">
                    {zone.replace(/_/g, ' ')}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(count / injuries.length) * 100}%` }}
                      transition={{ duration: 0.5 }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: getZoneColor(zone) }}
                    />
                  </div>
                  <span className="text-xs text-[var(--color-text-subtle)] w-6 text-right">
                    {count}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RecoveryTimeline;
