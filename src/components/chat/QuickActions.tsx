// Quick Actions Component
// =======================
// Horizontal scrollable quick action buttons

import { motion } from 'framer-motion';

interface QuickActionsProps {
  onAction: (action: string) => void;
}

const ACTIONS = [
  { label: 'Plan de hoy', prompt: '¿Cuál es mi plan de entrenamiento para hoy?' },
  { label: 'Readiness', prompt: '¿Cómo está mi readiness hoy?' },
  { label: 'Generar sesión', prompt: 'Genera una sesión de entrenamiento para hoy' },
  { label: 'Análisis semanal', prompt: 'Dame un análisis de mi semana' },
  { label: 'Consejo', prompt: 'Dame un consejo de entrenamiento' },
];

export const QuickActions = ({ onAction }: QuickActionsProps) => {
  return (
    <div className="px-3 py-2 overflow-x-auto">
      <div className="flex gap-2">
        {ACTIONS.map((action) => (
          <motion.button
            key={action.label}
            whileTap={{ scale: 0.95 }}
            onClick={() => onAction(action.prompt)}
            className="whitespace-nowrap px-4 py-2 rounded-full bg-[var(--color-surface-high)] text-xs text-[var(--color-text)] border border-[var(--color-outline)] hover:border-[var(--color-primary)] transition-colors"
          >
            {action.label}
          </motion.button>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
