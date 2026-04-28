// Input Bar Component
// ====================
// Message input with send button

import { useState, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';

interface InputBarProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export const InputBar = ({ onSend, disabled }: InputBarProps) => {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="glass border-t border-[var(--color-outline)] p-3">
      <div className="flex items-center gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe tu mensaje..."
          disabled={disabled}
          className="flex-1 bg-[var(--color-surface)] rounded-xl px-4 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] resize-none min-h-[40px] max-h-[100px] disabled:opacity-50"
          rows={1}
        />
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="w-10 h-10 rounded-xl bg-[var(--color-primary)] text-[var(--color-on-primary)] flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
        </motion.button>
      </div>
    </div>
  );
};

export default InputBar;
