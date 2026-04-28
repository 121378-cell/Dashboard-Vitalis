import { CapacitorHttp } from '@capacitor/core';
import { Message } from "../types";

const BACKEND_URL = "https://atlas-vitalis-backend.fly.dev/api/v1";
const GEMINI_API_KEY = "AIzaSyAOQLH9ys29PJK4-SxphRIsJmnXHZP-DvQ";
const GROQ_API_KEY = "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";

async function callNative(url: string, data: any, headers: any = {}) {
  const options = {
    url,
    headers: { 'Content-Type': 'application/json', ...headers },
    data,
    connectTimeout: 5000,
    readTimeout: 10000
  };
  return await CapacitorHttp.post(options);
}

export async function callAI(messages: Message[], systemPrompt: string) {
  const lastMsg = messages[messages.length - 1]?.content || "Hola";
  let logs = [];

  // 1. INTENTO GROQ (El más rápido en móvil)
  try {
    const res = await callNative(
      "https://api.groq.com/openai/v1/chat/completions",
      { 
        model: "llama-3.1-8b-instant", 
        messages: [{ role: "user", content: lastMsg }] 
      },
      { 'Authorization': `Bearer ${GROQ_API_KEY}` }
    );
    if (res.status === 200) return { content: res.data.choices[0].message.content, provider: "Groq (Nativo)" };
    logs.push(`Groq:${res.status}`);
  } catch (e: any) { logs.push(`Groq:${e.message}`); }

  // 2. INTENTO GEMINI (Flash Latest)
  try {
    const res = await callNative(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${GEMINI_API_KEY}`,
      { contents: [{ parts: [{ text: lastMsg }] }] }
    );
    if (res.status === 200) return { content: res.data.candidates[0].content.parts[0].text, provider: "Gemini (Nativo)" };
    logs.push(`Gemini:${res.status}`);
  } catch (e: any) { logs.push(`Gemini:${e.message}`); }

  // 3. INTENTO PC BACKEND
  try {
    const res = await callNative(
      `${BACKEND_URL}/ai/chat`,
      { messages: messages.map(m => ({ role: m.role, content: m.content })), system_prompt: systemPrompt }
    );
    if (res.status === 200) return { content: res.data.content, provider: "ATLAS PC" };
    logs.push(`PC:${res.status}`);
  } catch (e: any) { logs.push(`PC:${e.message}`); }

  throw new Error(`Chat bloqueado. Logs: ${logs.join(" | ")}`);
}
