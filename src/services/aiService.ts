import { GoogleGenAI } from "@google/genai";
import { Message } from "../types";

const GROQ_API_KEY = import.meta.env.VITE_GROQ_API_KEY;
const OLLAMA_URL = import.meta.env.VITE_OLLAMA_URL || "http://localhost:11434";
const OLLAMA_MODEL = import.meta.env.VITE_OLLAMA_MODEL || "llama3";
const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY;

export async function callAI(messages: Message[], systemPrompt: string): Promise<{ content: string; provider: 'Groq' | 'Ollama' | 'Gemini' }> {
  // REQ-F15: Fallback in cascade (Groq -> Ollama -> Gemini)
  
  // 1. Try Groq (REQ-F15a)
  if (GROQ_API_KEY) {
    try {
      console.log("[ATLAS] Attempting Groq...");
      const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${GROQ_API_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: "llama3-70b-8192",
          messages: [{ role: "system", content: systemPrompt }, ...messages.map(m => ({ role: m.role, content: m.content }))],
          temperature: 0.7
        }),
        signal: AbortSignal.timeout(15000)
      });

      if (response.ok) {
        const data = await response.json();
        return { content: data.choices[0].message.content, provider: 'Groq' };
      }
    } catch (e) {
      console.error("[ATLAS] Groq failed:", e);
    }
  }

  // 2. Try Ollama (REQ-F15b)
  try {
    console.log("[ATLAS] Attempting Ollama...");
    const response = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        messages: [{ role: "system", content: systemPrompt }, ...messages.map(m => ({ role: m.role, content: m.content }))],
        stream: false
      }),
      signal: AbortSignal.timeout(5000) // Short timeout for local service
    });

    if (response.ok) {
      const data = await response.json();
      return { content: data.message.content, provider: 'Ollama' };
    }
  } catch (e) {
    console.error("[ATLAS] Ollama failed:", e);
  }

  // 3. Try Gemini (REQ-F15c)
  if (GEMINI_API_KEY) {
    try {
      console.log("[ATLAS] Attempting Gemini...");
      const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });
      const response = await ai.models.generateContent({
        model: "gemini-1.5-pro",
        contents: messages.map(m => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })),
        config: {
          systemInstruction: systemPrompt
        }
      });
      return { content: response.text || "No response from Gemini", provider: 'Gemini' };
    } catch (e) {
      console.error("[ATLAS] Gemini failed:", e);
    }
  }

  throw new Error("No AI providers available.");
}
