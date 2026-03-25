import logging
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger("app.services.ai_service")

class AIService:
    def __init__(self):
        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
        
        self.gemini_client = None
        if settings.GEMINI_API_KEY:
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
        self.ollama_client = OpenAI(
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1"
        )

    def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Resilience-based generation: Groq -> Ollama -> Gemini"""
        
        # 1. Try Groq
        if self.groq_client:
            try:
                return self._generate_openai_compatible(self.groq_client, "llama-3.3-70b-versatile", prompt, system_instruction)
            except Exception as e:
                logger.warning(f"Groq failed: {e}")

        # 2. Try Ollama (Local)
        try:
            return self._generate_openai_compatible(self.ollama_client, "llama3", prompt, system_instruction)
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")

        # 3. Fallback to Gemini
        if self.gemini_client:
            try:
                return self._generate_gemini(prompt, system_instruction)
            except Exception as e:
                logger.error(f"Gemini failed: {e}")
        
        raise Exception("All AI providers failed")

    def _generate_openai_compatible(self, client: OpenAI, model: str, prompt: str, system_instruction: str = None) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content

    def _generate_gemini(self, prompt: str, system_instruction: str = None) -> str:
        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = self.gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )
        return response.text
