import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import type { PlateauEntry } from '../../types';

interface PlateauAlertProps {
  plateaus: PlateauEntry[];
  isLoading?: boolean;
}

export const PlateauAlert = ({ plateaus, isLoading }: PlateauAlertProps) => {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="rounded-xl bg-orange-500/5 border border-orange-500/20 p-4 space-y-2">
        <div className="h-4 w-40 bg-white/10 rounded animate-pulse" />
        <div className="h-12 bg-white/5 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!plateaus.length) {
    return null;
  }

  return (
    <div className="rounded-xl bg-orange-500/5 border border-orange-500/20 backdrop-blur-sm p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm">⚠️</span>
        <h3 className="text-sm font-semibold text-orange-400">
          Plateaus Detectados
        </h3>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-orange-500/20 text-orange-400 font-medium">
          {plateaus.length}
        </span>
      </div>

      <div className="space-y-2">
        {plateaus.map((p) => (
          <motion.div
            key={p.exercise}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            className="rounded-lg bg-white/5 p-3 cursor-pointer hover:bg-white/10 transition-colors"
            onClick={() => setExpanded(expanded === p.exercise ? null : p.exercise)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-orange-400">🏋️</span>
                <span className="text-sm font-medium text-[var(--color-text)]">
                  {p.exercise}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-orange-400 font-medium">
                  {p.current_weight}kg
                </span>
                <span className="text-[10px] text-[var(--color-text-subtle)]">
                  {p.weeks_stagnant}sem
                </span>
              </div>
            </div>

            <AnimatePresence>
              {expanded === p.exercise && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 pt-2 border-t border-white/5 space-y-2">
                    <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
                      <span>Pendiente: {p.slope_per_week} kg/sem</span>
                      <span>Semanas estancado: {p.weeks_stagnant}</span>
                    </div>
                    <div className="rounded-lg bg-orange-500/10 p-2.5">
                      <p className="text-xs text-orange-300">
                        💡 {p.suggestion}
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default PlateauAlert;
