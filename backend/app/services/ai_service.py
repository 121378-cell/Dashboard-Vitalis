import logging
import time
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

    @staticmethod
    def chat(messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Class method for direct chat with provider fallback."""
        service = AIService()
        content = service._generate_chat_response(messages, system_prompt)
        return content

    def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Simple prompt-based generation."""
        messages = [{"role": "user", "content": prompt}]
        res = self._generate_chat_response(messages, system_instruction)
        return res["content"]

    def _generate_chat_response(self, messages: List[Dict[str, str]], system_instruction: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # 1. Try Groq with 15s timeout
        if self.groq_client:
            try:
                logger.info("Trying Groq AI provider...")
                content = self._generate_openai_compatible(self.groq_client, "llama-3.1-8b-instant", messages, system_instruction, timeout=15)
                logger.info(f"Groq responded successfully in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Groq"}
            except Exception as e:
                logger.warning(f"Groq failed: {e}")

        # 2. Check Ollama availability before trying (2s quick check)
        ollama_available = self._check_ollama_available()
        if ollama_available:
            try:
                logger.info("Trying Ollama (local) AI provider...")
                content = self._generate_openai_compatible(self.ollama_client, "llama3", messages, system_instruction, timeout=10)
                logger.info(f"Ollama responded successfully in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Ollama (Local)"}
            except Exception as e:
                logger.warning(f"Ollama failed: {e}")
        else:
            logger.info("Ollama not available, skipping...")

        # 3. Fallback to Gemini with 15s timeout
        if self.gemini_client:
            try:
                logger.info("Trying Gemini AI provider...")
                content = self._generate_gemini(messages, system_instruction)
                logger.info(f"Gemini responded successfully in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Gemini"}
            except Exception as e:
                logger.error(f"Gemini failed: {e}")
        
        # All providers failed - return error within 45s total
        elapsed = time.time() - start_time
        if elapsed > 45:
            logger.error(f"All AI providers failed after {elapsed:.1f}s (timeout exceeded)")
        else:
            logger.error(f"All AI providers failed after {elapsed:.1f}s")
        
        raise Exception("All AI providers failed. Please check your API keys or try again later.")

    def _check_ollama_available(self) -> bool:
        """Quick 2s check if Ollama is running."""
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def _generate_openai_compatible(self, client: OpenAI, model: str, messages: List[Dict], system_instruction: str = None, timeout: int = 30) -> str:
        full_messages = []
        if system_instruction:
            full_messages.append({"role": "system", "content": system_instruction})
        full_messages.extend(messages)
        
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
            stream=False,
            timeout=timeout
        )
        return response.choices[0].message.content

    def _generate_gemini(self, messages: List[Dict], system_instruction: str = None) -> str:
        # Convert messages to Gemini format
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
            
        config = types.GenerateContentConfig(system_instruction=system_instruction)
        response = self.gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=contents,
            config=config
        )
        return response.text
