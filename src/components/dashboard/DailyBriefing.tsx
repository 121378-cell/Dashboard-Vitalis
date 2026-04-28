// Daily Briefing Component
// ========================
// Proactive daily briefing card with glassmorphism

import { useState } from 'react';
import { motion } from 'framer-motion';
import { DailyBriefing as DailyBriefingType } from '../../types';

interface DailyBriefingProps {
  briefing: DailyBriefingType | null;
  onRefresh: () => void;
  isLoading?: boolean;
}

export const DailyBriefing = ({ briefing, onRefresh, isLoading }: DailyBriefingProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-high rounded-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-outline)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">📋</span>
          <h3 className="font-display font-semibold text-[var(--color-text)]">
            Briefing Diario
          </h3>
        </div>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-primary)] disabled:opacity-50"
        >
          {isLoading ? 'Actualizando...' : 'Actualizar'}
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {briefing ? (
          <div className="space-y-3">
            <p className={`text-sm text-[var(--color-text)] leading-relaxed ${
              isExpanded ? '' : 'line-clamp-4'
            }`}>
              {briefing.briefing}
            </p>
            
            {briefing.briefing.length > 200 && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs text-[var(--color-primary)] hover:underline"
              >
                {isExpanded ? 'Ver menos' : 'Ver más'}
              </button>
            )}
            
            {briefing.generated_at && (
              <p className="text-xs text-[var(--color-text-muted)]">
                Generado: {new Date(briefing.generated_at).toLocaleString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            )}
          </div>
        ) : (
          <div className="text-center py-6">
            <p className="text-sm text-[var(--color-text-muted)]">
              No hay briefing disponible
            </p>
            <button
              onClick={onRefresh}
              className="mt-2 text-sm text-[var(--color-primary)] hover:underline"
            >
              Generar briefing
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default DailyBriefing;
