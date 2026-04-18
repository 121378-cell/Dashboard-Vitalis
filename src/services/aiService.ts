import axios from "axios";
import { Message } from "../types";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8001/api/v1";
const GROQ_API_KEY = import.meta.env.VITE_GROQ_API_KEY || "";
const GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = "llama3-8b-8192"; // Rápido, gratuito, ideal para móvil

// ─── Groq Directo (sin backend) ───────────────────────────────────────────────
async function callGroqDirect(
  messages: Message[],
  systemPrompt: string
): Promise<{ content: string; provider: string }> {
  if (!GROQ_API_KEY) {
    throw new Error("VITE_GROQ_API_KEY no configurada.");
  }

  const response = await axios.post(
    GROQ_API_URL,
    {
      model: GROQ_MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        ...messages
          .filter((m) => m.role !== "system")
          .map((m) => ({ role: m.role, content: m.content })),
      ],
      temperature: 0.7,
      max_tokens: 1024,
    },
    {
      headers: {
        Authorization: `Bearer ${GROQ_API_KEY}`,
        "Content-Type": "application/json",
      },
      timeout: 30000, // Groq es muy rápido, 30s suficiente
    }
  );

  return {
    content: response.data.choices[0].message.content,
    provider: "Groq · Llama 3",
  };
}

// ─── Backend FastAPI (cuando está disponible) ─────────────────────────────────
async function callBackendAI(
  messages: Message[],
  systemPrompt: string
): Promise<{ content: string; provider: string }> {
  const response = await axios.post(
    `${BACKEND_URL}/ai/chat`,
    {
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      system_prompt: systemPrompt,
    },
    {
      headers: { "x-user-id": "default_user" },
      timeout: 120000,
    }
  );

  return {
    content: response.data.content,
    provider: response.data.provider || "ATLAS AI",
  };
}

// ─── Función principal: Backend primero, Groq como fallback ───────────────────
export async function callAI(
  messages: Message[],
  systemPrompt: string
): Promise<{ content: string; provider: string }> {
  // 1. Intentar el backend FastAPI (funciona en PC con servidor activo)
  if (BACKEND_URL && navigator.onLine) {
    try {
      return await callBackendAI(messages, systemPrompt);
    } catch (backendErr: any) {
      // Si el backend no responde (offline móvil), caemos a Groq
      const isNetworkError = !backendErr.response;
      if (isNetworkError) {
        console.info("[AI] Backend no accesible. Usando Groq directo...");
      } else {
        // Error del propio backend (4xx/5xx) → también intentamos Groq
        console.warn("[AI] Backend error:", backendErr.response?.status, "→ fallback a Groq");
      }
    }
  }

  // 2. Fallback: Llamada directa a Groq desde el cliente
  return await callGroqDirect(messages, systemPrompt);
}
