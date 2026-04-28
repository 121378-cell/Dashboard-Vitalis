// Message Bubble Component
// =========================
// Individual chat message display

import { motion } from 'framer-motion';
import { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
  isLast?: boolean;
}

export const MessageBubble = ({ message, isLast }: MessageBubbleProps) => {
  const isUser = message.role === 'user';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-[var(--color-primary)] text-[var(--color-on-primary)]'
            : 'glass text-[var(--color-text)]'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        
        {!isUser && message.provider && (
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            via {message.provider}
          </p>
        )}
      </div>
    </motion.div>
  );
};

export default MessageBubble;
