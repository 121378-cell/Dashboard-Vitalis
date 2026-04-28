// Biometrics Widget
// ==================
// Widget showing all biometrics data

import { motion } from 'framer-motion';
import { Biometrics, ReadinessScore } from '../../types';
import { ReadinessDial } from './ReadinessDial';
import { MetricCard } from './MetricCard';

interface BiometricsWidgetProps {
  biometrics: Biometrics | null;
  readiness: ReadinessScore | null;
}

export const BiometricsWidget = ({ biometrics, readiness }: BiometricsWidgetProps) => {
  return (
    <div className="space-y-4">
      {/* Readiness Score */}
      <div className="glass-high rounded-2xl p-4">
        <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">
          Readiness Score
        </h3>
        <ReadinessDial readiness={readiness} size={180} />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          icon="👣"
          label="Pasos"
          value={biometrics?.steps?.toLocaleString() || '--'}
          trend="neutral"
        />
        <MetricCard
          icon="❤️"
          label="FC Reposo"
          value={biometrics?.resting_hr || '--'}
          unit="bpm"
          trend="neutral"
        />
        <MetricCard
          icon="🌙"
          label="Sueño"
          value={biometrics?.sleep ? `${biometrics.sleep.toFixed(1)}` : '--'}
          unit="h"
          trend="neutral"
        />
        <MetricCard
          icon="⚡"
          label="HRV"
          value={biometrics?.hrv || '--'}
          unit="ms"
          trend="neutral"
        />
      </div>

      {/* Additional Metrics */}
      <div className="glass rounded-xl p-4">
        <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-3">
          Más métricas
        </h4>
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center">
            <p className="text-lg font-display font-semibold text-[var(--color-text)]">
              {biometrics?.stress || '--'}
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">Estrés</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-display font-semibold text-[var(--color-text)]">
              {biometrics?.calories ? biometrics.calories.toLocaleString() : '--'}
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">Kcal</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-display font-semibold text-[var(--color-text)]">
              {biometrics?.spo2 || '--'}
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">SpO2%</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BiometricsWidget;
