import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface SessionEditModalProps {
  open: boolean;
  sessionTitle: string;
  sessionId: number;
  onSubmit: (sessionId: number, request: string) => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

const SUGGESTION_CHIPS = [
  'Cambiar ejercicios',
  'Reducir intensidad',
  'Más volumen',
  'Sustituir ejercicio',
  'Menos duración',
  'Añadir movilidad',
];

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const modalVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1 },
};

const SessionEditModal: React.FC<SessionEditModalProps> = ({
  open,
  sessionTitle,
  sessionId,
  onSubmit,
  onClose,
  loading,
}) => {
  const [text, setText] = useState('');

  const resetAndClose = useCallback(() => {
    if (!loading) {
      setText('');
      onClose();
    }
  }, [loading, onClose]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') resetAndClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, resetAndClose]);

  const handleSubmit = async () => {
    if (!text.trim() || loading) return;
    try {
      await onSubmit(sessionId, text.trim());
      setText('');
      onClose();
    } catch {}
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          variants={overlayVariants}
          initial="hidden"
          animate="visible"
          exit="hidden"
          transition={{ duration: 0.2 }}
          onClick={resetAndClose}
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

          <motion.div
            className="relative w-full max-w-lg rounded-2xl overflow-hidden"
            style={{ backgroundColor: '#13131A' }}
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            transition={{ duration: 0.25, ease: 'easeOut' }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between px-5 pt-5 pb-3">
              <div>
                <h2
                  className="text-lg font-bold"
                  style={{ fontFamily: "'Orbitron', sans-serif", color: '#F0F0FF' }}
                >
                  Adaptar Sesión
                </h2>
                <p className="text-sm mt-1" style={{ color: '#6B6B8A' }}>
                  Sesión: {sessionTitle}
                </p>
              </div>
              <button
                onClick={resetAndClose}
                disabled={loading}
                className="p-1.5 rounded-lg transition-colors hover:bg-white/10"
                style={{ color: '#6B6B8A' }}
                aria-label="Cerrar"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                >
                  <line x1="5" y1="5" x2="15" y2="15" />
                  <line x1="15" y1="5" x2="5" y2="15" />
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="px-5 pb-4 space-y-4">
              <div>
                <label
                  className="block text-sm mb-2"
                  style={{ color: '#F0F0FF', fontFamily: "'DM Sans', sans-serif" }}
                >
                  Describe qué quieres cambiar en esta sesión:
                </label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={4}
                  placeholder="Ej: Cambiar press banca por press inclinado, reducir series a 3..."
                  className="w-full text-sm px-3 py-2.5 rounded-xl border focus:outline-none resize-none transition-colors"
                  style={{
                    backgroundColor: '#1C1C26',
                    borderColor: text.trim() ? '#E8FF4740' : '#6B6B8A40',
                    color: '#F0F0FF',
                    fontFamily: "'DM Sans', sans-serif",
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = '#E8FF4780';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = text.trim() ? '#E8FF4740' : '#6B6B8A40';
                  }}
                />
              </div>

              <div>
                <p
                  className="text-xs uppercase tracking-wider mb-2"
                  style={{ color: '#6B6B8A', fontFamily: "'DM Sans', sans-serif" }}
                >
                  Sugerencias rápidas
                </p>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTION_CHIPS.map((chip) => (
                    <button
                      key={chip}
                      onClick={() => setText(chip)}
                      className="px-3 py-1.5 rounded-full text-xs border transition-colors"
                      style={{
                        backgroundColor: '#1C1C26',
                        borderColor: '#6B6B8A40',
                        color: '#F0F0FF',
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#E8FF47';
                        e.currentTarget.style.color = '#E8FF47';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = '#6B6B8A40';
                        e.currentTarget.style.color = '#F0F0FF';
                      }}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div
              className="flex items-center justify-end gap-3 px-5 py-4"
              style={{ borderTop: '1px solid #6B6B8A20' }}
            >
              <button
                onClick={resetAndClose}
                disabled={loading}
                className="px-4 py-2 rounded-xl text-sm transition-colors hover:bg-white/10"
                style={{
                  color: '#6B6B8A',
                  fontFamily: "'DM Sans', sans-serif",
                }}
              >
                Cancelar
              </button>
              <button
                onClick={handleSubmit}
                disabled={!text.trim() || loading}
                className="px-5 py-2 rounded-xl text-sm font-semibold transition-all flex items-center justify-center gap-2 disabled:opacity-40"
                style={{
                  backgroundColor: '#E8FF47',
                  color: '#0A0A0F',
                  fontFamily: "'DM Sans', sans-serif",
                }}
              >
                {loading && (
                  <svg
                    className="animate-spin h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeDasharray="31.4 31.4"
                      strokeLinecap="round"
                    />
                  </svg>
                )}
                Enviar a ATLAS
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SessionEditModal;
