import { motion } from 'framer-motion';

interface QuickActionsProps {
  onAction: (action: string) => void;
}

const QUICK_COMMANDS = [
  { label: '¿Cómo estoy?', message: '¿Cómo estoy hoy? Dame un análisis de mi estado actual.' },
  { label: '¿Qué entreno?', message: '¿Qué entreno hoy basándote en mi readiness?' },
  { label: 'Generar plan', message: 'Genera mi plan de entrenamiento semanal.' },
  { label: 'Ver readiness', message: 'Muéstrame mi readiness score y componentes de hoy.' },
  { label: 'Resumen semana', message: 'Dame un resumen de mi semana de entrenamiento.' },
];

export const QuickActions = ({ onAction }: QuickActionsProps) => {
  return (
    <div className="px-3 py-2 overflow-x-auto">
      <div className="flex gap-2">
        {QUICK_COMMANDS.map((cmd) => (
          <motion.button
            key={cmd.label}
            whileTap={{ scale: 0.95 }}
            onClick={() => onAction(cmd.message)}
            className="whitespace-nowrap px-4 py-2 rounded-full bg-[var(--color-surface-high)] text-xs text-[var(--color-text)] border border-[var(--color-outline)] hover:border-[var(--color-primary)] transition-colors"
          >
            {cmd.label}
          </motion.button>
        ))}
      </div>
    </div>
  );
};

export default QuickActions;
