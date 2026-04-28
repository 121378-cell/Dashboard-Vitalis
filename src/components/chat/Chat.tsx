// Chat Component
// ==============
// Main chat container with message history

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAtlasStore } from '../../store/atlasStore';
import { MessageBubble } from './MessageBubble';
import { InputBar } from './InputBar';
import { QuickActions } from './QuickActions';
import { callAI } from '../../services/aiService';

export const Chat = () => {
  const { chatHistory, addChatMessage } = useAtlasStore();
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleSend = async (content: string) => {
    // Add user message
    addChatMessage({ role: 'user', content });
    setIsTyping(true);

    try {
      // Call AI service
      const response = await callAI(
        [...chatHistory, { role: 'user', content }],
        'Eres ATLAS, un entrenador personal AI experto.'
      );

      // Add AI response
      if (response) {
        addChatMessage({
          role: 'assistant',
          content: response.content,
          provider: response.provider,
        });
      }
    } catch (error) {
      console.error('[Chat] AI call failed:', error);
      addChatMessage({
        role: 'assistant',
        content: 'Lo siento, no pude procesar tu mensaje. Inténtalo de nuevo.',
      });
    } finally {
      setIsTyping(false);
    }
  };

  const handleQuickAction = (action: string) => {
    handleSend(action);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {chatHistory.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-8"
            >
              <h3 className="text-lg font-medium text-[var(--color-text)] mb-2">
                ¡Hola! Soy ATLAS
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                Tu entrenador personal AI. ¿En qué puedo ayudarte hoy?
              </p>
            </motion.div>
          ) : (
            chatHistory.map((msg, index) => (
              <MessageBubble
                key={index}
                message={msg}
                isLast={index === chatHistory.length - 1}
              />
            ))
          )}
        </AnimatePresence>

        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-[var(--color-text-muted)]"
          >
            <div className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-bounce" />
            <div className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-bounce delay-100" />
            <div className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-bounce delay-200" />
            <span className="text-xs">ATLAS está escribiendo...</span>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <QuickActions onAction={handleQuickAction} />

      {/* Input */}
      <InputBar onSend={handleSend} disabled={isTyping} />
    </div>
  );
};

export default Chat;
