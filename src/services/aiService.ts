import axios from "axios";
import { Message } from "../types";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8001/api/v1";

export async function callAI(messages: Message[], systemPrompt: string): Promise<{ content: string; provider: string }> {
  try {
    const response = await axios.post(`${BACKEND_URL}/ai/chat/`, {
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      system_prompt: systemPrompt
    }, {
      headers: { "x-user-id": "default_user" },
      timeout: 30000 // 30s for AI response
    });

    return {
      content: response.data.content,
      provider: response.data.provider || "ATLAS AI"
    };
  } catch (e: any) {
    console.error("[ATLAS] Backend AI failed:", e);
    throw new Error(e.response?.data?.detail || "Error connecting to ATLAS AI service.");
  }
}
