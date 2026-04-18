import axios from "axios";
import { Message } from "../types";

const BACKEND_URL = "http://192.168.1.133:8005/api/v1";
const GEMINI_API_KEY = "AIzaSyAOQLH9ys29PJK4-SxphRIsJmnXHZP-DvQ";

async function callGoogleGemini(model: string, messages: Message[]) {
  // Probamos la v1beta que es la más amable con claves nuevas
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${GEMINI_API_KEY}`;
  const lastMessage = messages[messages.length - 1]?.content || "Hola";

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: lastMessage }] }]
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Google ${model} dio ${response.status}: ${text.substring(0, 40)}`);
  }

  const data = await response.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "";
}

export async function callAI(messages: Message[], systemPrompt: string) {
  let reports = [];

  // INTENTO A: Gemini Flash
  try {
    const text = await callGoogleGemini("gemini-1.5-flash", messages);
    if (text) return { content: text, provider: "Gemini Flash" };
  } catch (e: any) {
    reports.push(`G-Flash: ${e.message}`);
  }

  // INTENTO B: Gemini Pro (Más lento pero más compatible)
  try {
    const text = await callGoogleGemini("gemini-pro", messages);
    if (text) return { content: text, provider: "Gemini Pro" };
  } catch (e: any) {
    reports.push(`G-Pro: ${e.message}`);
  }

  // INTENTO C: Backend PC
  try {
    const response = await axios.post(`${BACKEND_URL}/ai/chat`, {
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      system_prompt: systemPrompt
    }, { timeout: 4000 });
    return { content: response.data.content, provider: "ATLAS PC" };
  } catch (e: any) {
    reports.push(`PC (133): ${e.message}`);
  }

  throw new Error(`Sin conexión. Historial: ${reports.join(" | ")}`);
}
