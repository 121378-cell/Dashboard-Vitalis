import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, Zap, Brain, Heart, Target, Dumbbell, History } from 'lucide-react';
import { Message, SessionPlan } from '../types';
import { SessionTable } from './SessionTable';

interface Props {
  messages: Message[];
  onSendMessage: (content: string) => void;
  loading: boolean;
  quickActions: { label: string, prompt: string }[];
}

function extractSessionPlan(content: string): SessionPlan | null {
  try {
    // Intentar parsear directamente
    const parsed = JSON.parse(content);
    if (parsed.exercises && parsed.session_name) return parsed;
  } catch {}
  
  // Buscar JSON embebido en texto (con bloques markdown code)
  const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    try {
      const parsed = JSON.parse(codeBlockMatch[1]);
      if (parsed.exercises && parsed.session_name) return parsed;
    } catch {}
  }
  
  // Buscar JSON embebido directamente en texto
  const jsonMatch = content.match(/\{[\s\S]*"exercises"[\s\S]*"session_name"[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]);
      if (parsed.exercises) return parsed;
    } catch {}
  }
  return null;
}

export const Chat: React.FC<Props> = ({ messages, onSendMessage, loading, quickActions }) => {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (input.trim() && !loading) {
      onSendMessage(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-container-low rounded-xl border border-outline-variant/10 overflow-hidden">
      {/* Messages Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center text-primary animate-pulse">
              <Brain size={32} />
            </div>
            <h3 className="text-xl font-headline font-bold">Hola, soy ATLAS</h3>
            <p className="text-sm text-on-surface-variant max-w-md">
              Tu entrenador de élite con IA. Estoy listo para analizar tus biométricos y optimizar tu rendimiento.
            </p>
            <div className="grid grid-cols-2 gap-2 w-full max-w-lg mt-8">
              {quickActions.map((action) => (
                <button 
                  key={action.label}
                  onClick={() => onSendMessage(action.prompt)}
                  className="p-3 bg-surface-container text-left rounded-lg border border-outline-variant/10 hover:border-primary/50 transition-all group"
                >
                  <span className="text-[10px] font-bold uppercase text-primary block mb-1">{action.label}</span>
                  <span className="text-[11px] text-on-surface-variant line-clamp-1 group-hover:text-on-surface">{action.prompt}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        
        {messages.map((m, i) => {
          // Check if message contains a session plan
          const sessionPlan = m.role === 'assistant' ? extractSessionPlan(m.content) : null;
          
          if (sessionPlan) {
            return (
              <div key={i} className="flex justify-start w-full">
                <div className="w-full max-w-[95%]">
                  <SessionTable 
                    plan={sessionPlan} 
                    sessionId={sessionPlan.session_id}
                  />
                  {m.provider && (
                    <div className="mt-2 text-[8px] uppercase tracking-widest opacity-50 font-bold text-on-surface-variant">
                      Respondido por: {m.provider}
                    </div>
                  )}
                </div>
              </div>
            );
          }
          
          return (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] p-4 rounded-2xl ${
                m.role === 'user' 
                  ? 'bg-primary text-on-primary rounded-tr-none' 
                  : 'bg-surface-container-high text-on-surface rounded-tl-none border border-outline-variant/10'
              }`}>
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
                {m.provider && (
                  <div className="mt-2 text-[8px] uppercase tracking-widest opacity-50 font-bold">
                    Respondido por: {m.provider}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-container-high p-4 rounded-2xl rounded-tl-none border border-outline-variant/10 flex items-center gap-2">
              <Loader2 size={16} className="animate-spin text-primary" />
              <span className="text-xs text-on-surface-variant italic">ATLAS está procesando...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-surface-container-low border-t border-outline-variant/10">
        <div className="relative">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu mensaje a ATLAS..."
            className="w-full bg-surface-container-lowest border border-outline-variant/20 rounded-xl p-4 pr-12 outline-none focus:border-primary resize-none h-20 text-sm"
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="absolute bottom-4 right-4 p-2 bg-primary text-on-primary rounded-lg hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-[9px] text-on-surface-variant mt-2 text-center">
          Presiona Enter para enviar, Shift+Enter para nueva línea.
        </p>
      </div>
    </div>
  );
};
