import { BACKEND_URL } from '../config';
import { Message, ChatResponse, WelcomeMessage } from '../types';

export async function callAI(messages: Message[], systemPrompt?: string): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-user-id': 'default_user' },
    body: JSON.stringify({
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      system_prompt: systemPrompt,
    }),
  });

  if (!res.ok) {
    throw new Error(`Chat API failed: ${res.status}`);
  }

  const data = await res.json();
  return {
    content: data.content,
    provider: data.provider,
    mode: data.mode,
    type: data.type,
    session_id: data.session_id,
    plan_id: data.plan_id,
    context_meta: data.context_meta,
  };
}

export async function getWelcomeMessage(): Promise<WelcomeMessage> {
  const res = await fetch(`${BACKEND_URL}/ai/welcome-message`, {
    headers: { 'x-user-id': 'default_user' },
  });

  if (!res.ok) {
    throw new Error(`Welcome API failed: ${res.status}`);
  }

  return res.json();
}

export async function getContextPreview(): Promise<{
  system_prompt: string;
  context_meta: Record<string, unknown>;
}> {
  const res = await fetch(`${BACKEND_URL}/ai/context-preview`, {
    headers: { 'x-user-id': 'default_user' },
  });

  if (!res.ok) {
    throw new Error(`Context preview API failed: ${res.status}`);
  }

  return res.json();
}
