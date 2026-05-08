import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAtlasStore } from '../../store/atlasStore';
import { MessageBubble } from './MessageBubble';
import { InputBar } from './InputBar';
import { QuickActions } from './QuickActions';
import { callAI, getWelcomeMessage } from '../../services/aiService';
import { ChatContextMeta } from '../../types';

const READINESS_COLOR_MAP: Record<string, string> = {
  green: '#4ADE80',
  blue: '#60A5FA',
  yellow: '#FB923C',
  red: '#F87171',
  gray: '#6B6B8A',
};

export const Chat = () => {
  const { chatHistory, addChatMessage } = useAtlasStore();
  const [isTyping, setIsTyping] = useState(false);
  const [welcomeMsg, setWelcomeMsg] = useState<string | null>(null);
  const [contextMeta, setContextMeta] = useState<ChatContextMeta | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const welcomeFetched = useRef(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  useEffect(() => {
    if (welcomeFetched.current) return;
    welcomeFetched.current = true;
    getWelcomeMessage()
      .then((data) => setWelcomeMsg(data.message))
      .catch(() => setWelcomeMsg('Hola, Sergi. Soy ATLAS, tu Director Deportivo. ¿En qué te puedo ayudar?'));
  }, []);

  const handleSend = async (content: string) => {
    addChatMessage({ role: 'user', content });
    setIsTyping(true);

    try {
      const response = await callAI(
        [...chatHistory, { role: 'user', content }]
      );

      if (response) {
        addChatMessage({
          role: 'assistant',
          content: response.content,
          provider: response.provider,
        });
        if (response.context_meta) {
          setContextMeta(response.context_meta);
        }
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

  const readinessColor = contextMeta?.readiness_color
    ? READINESS_COLOR_MAP[contextMeta.readiness_color] || READINESS_COLOR_MAP.gray
    : READINESS_COLOR_MAP.gray;

  const contextIndicator = contextMeta ? (
    <div className="flex items-center gap-2 px-4 py-2 text-xs text-[var(--color-text-muted)] border-b border-[var(--color-outline)]">
      <span className="font-medium" style={{ fontFamily: 'var(--font-mono)' }}>ATLAS Coach</span>
      {contextMeta.readiness_score != null && (
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: readinessColor }} />
          Readiness: {contextMeta.readiness_score}/100
        </span>
      )}
      {contextMeta.data_freshness && (
        <span>Datos: {contextMeta.data_freshness}</span>
      )}
      {contextMeta.plan_active && contextMeta.plan_progress && (
        <span>Plan: {contextMeta.plan_progress} ✓</span>
      )}
      {contextMeta.unread_insights > 0 && (
        <span className="text-[var(--color-warning)]">{contextMeta.unread_insights} insights</span>
      )}
    </div>
  ) : null;

  return (
    <div className="flex flex-col h-full">
      {contextIndicator}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {chatHistory.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-8"
            >
              <h3 className="text-lg font-medium text-[var(--color-text)] mb-2">
                {welcomeMsg || '¡Hola! Soy ATLAS'}
              </h3>
              <p className="text-sm text-[var(--color-text-muted)]">
                Tu Director Deportivo de IA. Datos en tiempo real.
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

      <QuickActions onAction={handleQuickAction} />

      <InputBar onSend={handleSend} disabled={isTyping} />
    </div>
  );
};

export default Chat;
