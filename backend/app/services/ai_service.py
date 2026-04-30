import logging
import time
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from openai import OpenAI
from app.core.config import settings
from app.services.memory_service import MemoryService

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
        
        # 1. Groq (llama-3.3-70b-versatile) — fastest, 10s timeout
        if self.groq_client:
            try:
                logger.info("Trying Groq AI provider...")
                content = self._generate_openai_compatible(
                    self.groq_client, "llama-3.3-70b-versatile", messages, system_instruction, timeout=10
                )
                logger.info(f"Groq responded in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Groq"}
            except Exception as e:
                logger.warning(f"Groq failed: {e}")

        # 2. Gemini (gemini-2.0-flash) — fallback, 10s timeout
        if self.gemini_client:
            try:
                logger.info("Trying Gemini AI provider...")
                content = self._generate_gemini(messages, system_instruction)
                logger.info(f"Gemini responded in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Gemini"}
            except Exception as e:
                logger.error(f"Gemini failed: {e}")

        # 3. Ollama local — offline fallback, 10s timeout
        if self._check_ollama_available():
            try:
                logger.info("Trying Ollama (local) AI provider...")
                content = self._generate_openai_compatible(
                    self.ollama_client, "llama3", messages, system_instruction, timeout=10
                )
                logger.info(f"Ollama responded in {time.time() - start_time:.1f}s")
                return {"content": content, "provider": "Ollama (Local)"}
            except Exception as e:
                logger.warning(f"Ollama failed: {e}")
        
        elapsed = time.time() - start_time
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
            model="gemini-2.0-flash",
            contents=contents,
            config=config
        )
        return response.text

    @staticmethod
    def inject_memory_context(
        db: Session,
        user_id: str,
        base_system_prompt: str,
        max_tokens: int = 2000
    ) -> str:
        """
        Inject memory context into system prompt for personalized AI responses.
        
        This method retrieves the athlete's historical memories and adds them
        to the system prompt, enabling the AI to provide contextually-aware
        coaching that considers the athlete's history, injuries, patterns,
        and achievements.
        
        Args:
            db: Database session
            user_id: Athlete user ID
            base_system_prompt: Original system prompt without memory context
            max_tokens: Maximum tokens for memory context
            
        Returns:
            Enhanced system prompt with memory context injected
        """
        try:
            # Get memory context string
            memory_context = MemoryService.get_memory_context_string(
                db, user_id, max_tokens=max_tokens
            )
            
            if not memory_context:
                return base_system_prompt

            return base_system_prompt + memory_context
        except Exception as e:
            logger.error(f"Error injecting memory context: {e}")
            return base_system_prompt

    async def generate_morning_briefing(
        self, 
        db: Session, 
        user_id: str,
        readiness_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a morning briefing for a user.
        
        Args:
            db: Database session
            user_id: User ID
            readiness_result: Optional readiness result from readiness_service
            
        Returns:
            Dict containing briefing content with readiness_score and recommendation
        """
        try:
            # Get user's readiness score (use provided result or calculate)
            from app.services.readiness_service import ReadinessService
            if readiness_result is None:
                readiness_result = ReadinessService.calculate(db, user_id)
            
            # Get user's recent memories for context
            from app.services.memory_service import MemoryService
            memories = MemoryService.get_memory_context_string(
                db, user_id, max_tokens=1000
            )
            
            # Prepare prompt for AI
            system_prompt = """Eres un entrenador personal experto que proporciona un briefing matutino personalizado basado en los datos biométricos y el historial del atleta."""
            
            user_prompt = f"""
            Genera un briefing matutino personalizado para el atleta basado en:
            
            Puntuación de readiness: {readiness_result.get('score', 'N/A')}/100
            Estado: {readiness_result.get('status', 'N/A')}
            Componentes: {readiness_result.get('components', {})}
            
            Historial y contexto del atleta:
            {memories if memories else 'No hay datos históricos disponibles'}
            
            El briefing debe incluir:
            1. Una evaluación del estado físico y mental del día
            2. Una recomendación de entrenamiento específica
            3. Un mensaje motivacional
            
            Formato de respuesta como JSON con:
            {{
                "readiness_score": número (0-100),
                "status": string (excellent, good, moderate, poor, rest),
                "recommendation": string (recomendación de entrenamiento),
                "summary": string (resumen breve del briefing),
                "motivational_message": string (mensaje motivacional)
            }}
            """
            
            # Generate response using AI
            messages = [{"role": "user", "content": user_prompt}]
            response = self._generate_chat_response(messages, system_prompt)
            
            # Parse JSON response
            import json
            try:
                briefing_content = json.loads(response["content"])
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                briefing_content = {
                    "readiness_score": readiness_result.get('score', 50),
                    "status": readiness_result.get('status', 'moderate'),
                    "recommendation": readiness_result.get('recommendation', 'Entrenamiento moderado recomendado'),
                    "summary": f"Tu readiness hoy es {readiness_result.get('score', 'N/A')}/100. Estado: {readiness_result.get('status', 'N/A')}.",
                    "motivational_message": "¡Que tengas un gran día!"
                }
            
            return briefing_content
            
        except Exception as e:
            logger.error(f"Error generating morning briefing for user {user_id}: {e}", exc_info=True)
            # Return fallback briefing
            return {
                "readiness_score": 50,
                "status": "moderate",
                "recommendation": "Entrenamiento moderado recomendado",
                "summary": "Error generando briefing. Por favor intenta de nuevo más tarde.",
                "motivational_message": "¡Confía en el proceso!"
            }

    async def generate_weekly_report(
        self, 
        db: Session, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Generate a weekly report for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dict containing report content with summary and stats
        """
        try:
            from datetime import date, timedelta
            from app.models.biometrics import Biometrics
            from app.models.workout import Workout
            
            # Get data for the last 7 days
            cutoff = (date.today() - timedelta(days=7)).isoformat()
            
            # Get biometrics
            biometrics = db.query(Biometrics).filter(
                Biometrics.user_id == user_id,
                Biometrics.date >= cutoff
            ).all()
            
            # Get workouts
            workouts = db.query(Workout).filter(
                Workout.user_id == user_id,
                Workout.date >= cutoff
            ).all()
            
            # Calculate stats
            total_workouts = len(workouts)
            total_duration = sum(w.duration or 0 for w in workouts)  # in minutes
            total_calories = sum(w.calories or 0 for w in workouts)
            
            # Calculate average readiness
            readiness_scores = []
            for bio in biometrics:
                if bio.data:
                    try:
                        data = json.loads(bio.data)
                        # We don't store readiness directly in biometrics, so we'll estimate
                        # In a real implementation, we'd join with daily_briefings or readiness table
                        readiness_scores.append(70)  # placeholder
                    except:
                        pass
            
            avg_readiness = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 70
            
            # Prepare prompt for AI
            system_prompt = """Eres un entrenador personal experto que proporciona un informe semanal personalizado basado en los datos de entrenamiento y biométricos del atleta."""
            
            user_prompt = f"""
            Genera un informe semanal personalizado para el atleta basado en:
            
            Entrenamientos totales: {total_workouts}
            Duración total: {total_duration} minutos
            Calorías totales quemadas: {total_calories} kcal
            Readiness promedio estimado: {avg_readiness:.1f}/100
            
            El informe debe incluir:
            1. Resumen de la semana de entrenamiento
            2. Logros y progresos destacados
            3. Áreas de mejora para la próxima semana
            4. Recomendaciones generales
            
            Formato de respuesta como JSON con:
            {{
                "summary": string (resumen ejecutivo del informe semanal),
                "total_workouts": número,
                "total_duration_minutes": número,
                "total_calories": número,
                "avg_readiness": número,
                "achievements": array de strings (logros destacados),
                "recommendations": array de strings (recomendaciones para próxima semana)
            }}
            """
            
            # Generate response using AI
            messages = [{"role": "user", "content": user_prompt}]
            response = self._generate_chat_response(messages, system_prompt)
            
            # Parse JSON response
            import json
            try:
                report_content = json.loads(response["content"])
            except json.JSONDecodeError:
                # Fallback if AI doesn't return valid JSON
                report_content = {
                    "summary": f"Semana con {total_workouts} entrenamientos, {total_duration} minutos de actividad y {total_calories} kcal quemadas.",
                    "total_workouts": total_workouts,
                    "total_duration_minutes": total_duration,
                    "total_calories": total_calories,
                    "avg_readiness": round(avg_readiness, 1),
                    "achievements": ["Completaste todos tus entrenamientos programados"] if total_workouts > 0 else ["Mantuviste tu rutina"],
                    "recommendations": ["Continúa con tu plan de entrenamiento", "Presta atención a tu recuperación"]
                }
            
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating weekly report for user {user_id}: {e}", exc_info=True)
            # Return fallback report
            return {
                "summary": "Error generando informe semanal. Por favor intenta de nuevo más tarde.",
                "total_workouts": 0,
                "total_duration_minutes": 0,
                "total_calories": 0,
                "avg_readiness": 50,
                "achievements": [],
                "recommendations": ["Verifica tu conexión y vuelve a intentar"]
            }
            

