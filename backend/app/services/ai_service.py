import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from openai import OpenAI
from app.core.config import settings
from app.services.memory_service import MemoryService

logger = logging.getLogger("app.services.ai_service")

MASTER_SYSTEM_PROMPT = """Eres ATLAS, el Director Deportivo de IA de {athlete_name}. NO eres un asistente pasivo.

IDENTIDAD CORE:
- Eres el guardián del PROYECTO 31/07: {athlete_name} debe llegar al 31 de Julio en su mejor forma histórica.
- Tono: Directo, basado en datos, exigente pero leal. Si los datos sugieren descanso, lo dictas como orden profesional, no como sugerencia.
- Edad del atleta: {athlete_age} años — ajusta recuperación y volumen en consecuencia. Un atleta de 47 años NO recupera como uno de 25.
- PROACTIVIDAD: Analiza los datos de Garmin proporcionados. Si {athlete_name} no llega a sus {step_target} pasos, comunícalo con firmeza. Si su HRV es excelente, empújale a sesión de fuerza de alta intensidad.

REGLAS ABSOLUTAS:
1. NUNCA respondas "Como modelo de lenguaje..." o "No tengo acceso a...". Si no tienes un dato, di qué dato falta y qué decisión tomarías al respecto.
2. NUNCA des respuestas genéricas sin datos del atleta. Cada recomendación debe estar anclada a métricas reales.
3. MÁXIMO 150 PALABRAS por respuesta. Sé quirúrgico. Emojis funcionales solo (📊🟢🟡🔴⚡🛡️).
4. Cuando generes un entrenamiento, USA SIEMPRE los marcadores 'json_session_start' y 'json_session_end' con JSON editable por filas.
5. Usa ÚNICAMENTE nombres de ejercicios de la lista HEVY para que el usuario pueda registrarlos sin problemas.

GUARDIA BIOMÉTRICA (OBLIGATORIO):
- Readiness < 55 o HRV bajo baseline → ABORTAR fuerza, dictar Recuperación Activa o Descanso.
- Alerta de lesión activa → EVITAR zonas lesionadas, proponer alternativas.
- Dolor agudo reportado (≥8) → CONSULTA MÉDICA inmediata. ATLAS no diagnostica.
- Lesiones son PERMANENTES en memoria — nunca las ignores.

METODOLOGÍA:
- Sobrecarga Progresiva como motor principal.
- Protocolos McGill para salud espinal y recuperación.
- Intensidad Stoppani para periodización.
- NEAT: {step_target} pasos/día como motor de composición corporal.
- Hitos: Banca 50kg / Prensa 100kg.

MODO DE CONVERSACIÓN ACTUAL: {conversation_mode}
{mode_instructions}

CONTEXTO REAL DE HOY ({today_date}):
{biometrics_context}
{injury_context}
{readiness_context}
{acwr_context}
{workouts_context}
{plan_context}
{memory_context}

PERFIL DEL ATLETA:
{profile_context}

BIBLIA DE EJERCICIOS HEVY:
{exercise_context}
ORDEN: Usa ÚNICAMENTE nombres de ejercicios de la lista HEVY.

PROTOCOLO DE ADAPTABILIDAD CONTINUA:
1. ALINEACIÓN: Cada sesión debe ser un peldaño hacia el Proyecto 31/07.
2. GUARDIA BIOMÉTRICA: Si el Readiness Score es < 55 o el HRV está por debajo de su baseline, DEBES abortar el plan de fuerza.
3. ESCUCHA ACTIVA: Si {athlete_name} menciona cansancio o dolor, ajusta la rutina de inmediato.
4. FORMATO: Entrenamientos SIEMPRE con 'json_session_start' y 'json_session_end'.

DISEÑO DE SESIÓN: Diseña rutinas con sobrecarga progresiva, 100% coherentes con el estado físico real de hoy."""

MODE_INSTRUCTIONS = {
    "analysis": """INSTRUCCIÓN DE MODO: {athlete_name} quiere un ANÁLISIS de sus datos.
- Desglosa métricas clave con comparación a baseline.
- Señala tendencias (mejorando/estable/empeorando).
- Concluye con 1-2 acciones concretas basadas en los datos.
- Usa formato: métrica → interpretación → acción.""",

    "planning": """INSTRUCCIÓN DE MODO: {athlete_name} quiere un PLAN o ENTRENAMIENTO.
- Diseña la sesión basándote en: readiness actual, lesiones activas, ACWR, y objetivo 31/07.
- Si readiness < 55 → dicta recuperación activa (McGill, movilidad, caminata).
- Si readiness ≥ 70 → sesión de fuerza con sobrecarga progresiva.
- INCLUYE siempre: ejercicios, series, reps, RPE objetivo, duración estimada.
- Usa marcadores json_session_start / json_session_end.""",

    "motivation": """INSTRUCCIÓN DE MODO: {athlete_name} necesita MOTIVACIÓN.
- Reconoce su esfuerzo con datos reales (rachas, PRs, volumen).
- Conecta el día a día con la visión del 31 de Julio.
- Sé intenso pero no vacío — cita métricas, no frases hechas.
- 3-4 frases máximo. Impacto sobre cantidad.""",

    "alert": """INSTRUCCIÓN DE MODO: ALERTA ACTIVA — datos biométricos en zona de riesgo.
- Comunica el problema con urgencia profesional, no alarma innecesaria.
- Especifica qué métrica está fuera de rango y cuánto.
- Dicta la acción (descanso, recuperación activa, consulta médica si dolor ≥8).
- NO propongas entrenamiento de fuerza bajo ninguna circunstancia.""",

    "celebration": """INSTRUCCIÓN DE MODO: {athlete_name} ha logrado algo destacable.
- Celebra con datos concretos (PR, racha, readiness alto, HRV excepcional).
- Conecta el logro con la trayectoria hacia el 31/07.
- Sugiere cómo capitalizar este estado (ej: hoy es día de intensidad máxima).
- 2-3 frases. Contundente.""",
}

_prompt_cache: Dict[str, Dict[str, Any]] = {}


def _cache_key(user_id: str) -> str:
    return f"atlas_prompt_{user_id}"


def detect_conversation_mode(message: str, biometrics_context: str, injury_context: str, readiness_score: Optional[int] = None) -> str:
    msg = message.lower()

    if injury_context and ("dolor" in msg or "lesion" in msg or "duele" in msg or "molestia" in msg):
        return "alert"
    if readiness_score is not None and readiness_score < 40:
        return "alert"
    if "🔴" in biometrics_context or "alerta" in biometrics_context.lower() or "crítico" in biometrics_context.lower():
        return "alert"

    celebration_keywords = ["récord", "record", "pr", "pr personal", "logr", "conseguí", "consegui", "llegué a", "llegue a", "supera", "mejor marca", "hit"]
    if any(kw in msg for kw in celebration_keywords):
        return "celebration"

    planning_keywords = ["entreno", "sesión", "workout", "entrena", "ejercicio hoy", "rutina", "plan", "programa", "hacer hoy", "gym", "entrenar", "fuerza hoy", "cardio hoy"]
    if any(kw in msg for kw in planning_keywords):
        return "planning"

    analysis_keywords = ["análisis", "analisis", "cómo estoy", "como estoy", "datos", "métricas", "metricas", "readiness", "hrv", "carga", "acwr", "progreso", "tendencia", "estado"]
    if any(kw in msg for kw in analysis_keywords):
        return "analysis"

    motivation_keywords = ["motiv", "ánimo", "animo", "cansado", "perezoso", "no puedo", "difícil", "costó", "perez", "vago", "quiero dejar", "no tengo ganas"]
    if any(kw in msg for kw in motivation_keywords):
        return "motivation"

    if readiness_score is not None and readiness_score >= 80:
        return "planning"

    if readiness_score is not None and readiness_score < 55:
        return "analysis"

    return "analysis"


def build_atlas_system_prompt(db, user_id: str) -> Dict[str, Any]:
    from app.services.injury_prevention_service import InjuryPreventionService
    from app.services.readiness_service import ReadinessService
    from app.services.analytics_service import AnalyticsService
    from app.services.athlete_profile_service import AthleteProfileService
    from app.services.exercise_service import ExerciseService
    from app.models.biometrics import Biometrics
    from app.models.workout import Workout
    from app.models.session import TrainingSession
    import json

    key = _cache_key(user_id)
    cached = _prompt_cache.get(key)
    if cached and (datetime.now() - cached["ts"]).total_seconds() < 300:
        return cached["result"]

    today_str = date.today().isoformat()

    athlete_name = "Sergi"
    athlete_age = "47"
    step_target = "20.000"

    try:
        from app.models.user import User
        user_obj = db.query(User).filter(User.id == user_id).first()
        if user_obj and user_obj.name:
            athlete_name = user_obj.name
    except Exception:
        pass

    try:
        profile_summary = AthleteProfileService.get_profile_summary(user_id, db)
        if profile_summary and "Perfil no disponible" not in profile_summary:
            import re as _re
            age_match = _re.search(r'(\d+)\s*años', profile_summary)
            if age_match:
                athlete_age = age_match.group(1)
            steps_match = _re.search(r'([\d.,]+)\s*pasos/día', profile_summary)
            if steps_match:
                step_target = steps_match.group(1).replace(",", ".")
    except Exception:
        pass

    readiness_result = ReadinessService.calculate(db, user_id)
    readiness_score = readiness_result.get("score") or 50
    readiness_status = readiness_result.get("status", "moderate")
    readiness_rec = readiness_result.get("recommendation", "")
    baseline = readiness_result.get("baseline", {})

    readiness_context = f"""--- READINESS ({today_str}) ---
Puntuación: {readiness_score}/100 — Estado: {readiness_status.upper()}
Recomendación: {readiness_rec}
Baseline personal: HRV {baseline.get('hrv_mean', 'N/A')}ms | FCR {baseline.get('rhr_mean', 'N/A')}bpm | Sueño {baseline.get('sleep_mean', 'N/A')}h"""

    today_bio = db.query(Biometrics).filter(
        Biometrics.user_id == user_id, Biometrics.date == today_str
    ).first()

    if today_bio and today_bio.data:
        bio_data = json.loads(today_bio.data)
        hr = bio_data.get("heartRate", 0)
        hrv = bio_data.get("hrv", 0)
        sleep = bio_data.get("sleep", 0)
        steps = bio_data.get("steps", 0)
        stress = bio_data.get("stress", 0)

        hrv_baseline_val = baseline.get("hrv_mean") or 0
        rhr_baseline_val = baseline.get("rhr_mean") or 0

        biometrics_context = f"""--- BIOMÉTRICOS DE HOY ({today_str}) ---
FC Reposo: {hr} ppm (Baseline: {rhr_baseline_val} ppm)
HRV: {hrv} ms (Baseline: {hrv_baseline_val} ms)
Sueño: {sleep}h | Estrés: {stress}/100 | Pasos: {steps}"""

        if hrv_baseline_val > 0 and hrv > 0:
            diff = hrv - hrv_baseline_val
            if diff < -10:
                biometrics_context += "\n🔴 AVISO: HRV significativamente bajo — posible fatiga o inicio de enfermedad."
            elif diff > 10:
                biometrics_context += "\n🟢 HRV por encima de la media — recuperación excelente."
    else:
        biometrics_context = "No hay datos biométricos disponibles para hoy. Usa baselines históricos si están disponibles."

    injury_status = InjuryPreventionService.get_current_status(db, user_id)
    injury_dict = injury_status.to_dict() if hasattr(injury_status, "to_dict") else {}
    alert_level = injury_dict.get("alert_level", "optimal")
    active_injuries = injury_dict.get("active_injuries", [])
    zones_to_avoid = injury_dict.get("zones_to_avoid", [])
    alerts = injury_dict.get("alerts", [])

    if active_injuries or alert_level != "optimal":
        parts = [f"--- ALERTA DE LESIÓN: {alert_level.upper()} ---"]
        for a in alerts:
            parts.append(f"{'🔴' if a['level'] == 'stop' else '🟡' if a['level'] == 'caution' else '🟠'} {a['reason']} → {a['action_required']}")
        if active_injuries:
            for inj in active_injuries:
                parts.append(f"🩹 Lesión activa: {inj.get('zone', 'N/A')} — {inj.get('content', '')}")
        if zones_to_avoid:
            parts.append(f"Zonas a evitar: {', '.join(zones_to_avoid)}")
        injury_context = "\n".join(parts)
    else:
        injury_context = "Sin lesiones activas. Estado de prevención: ÓPTIMO 🟢"

    acwr = AnalyticsService.calculate_acwr(db, user_id)
    acwr_context = f"""--- CARGA DE ENTRENAMIENTO (ACWR) ---
Ratio: {acwr.get('ratio', 1.0)} — Estado: {acwr.get('status', 'mantenimiento').upper()}
{acwr.get('message', '')}"""

    recent_workouts = db.query(Workout).filter(
        Workout.user_id == user_id
    ).order_by(Workout.date.desc()).limit(5).all()

    if recent_workouts:
        w_lines = ["--- ENTRENAMIENTOS RECIENTES ---"]
        for w in recent_workouts[:3]:
            try:
                metrics = json.loads(w.description) if w.description else {}
                dist = metrics.get("distance", 0)
                sport = metrics.get("sport", "actividad").replace("_", " ")
                info = f"- {w.date.strftime('%d/%m') if hasattr(w.date, 'strftime') else w.date}: {w.name} ({sport}). "
                if dist:
                    info += f"Dist: {round(dist/1000, 2)}km. "
                info += f"Dur: {round(w.duration/60, 1)}min. Cal: {w.calories}."
                w_lines.append(info)
            except Exception:
                w_lines.append(f"- {w.name}. Dur: {w.duration}s.")
        workouts_context = "\n".join(w_lines)
    else:
        workouts_context = "No se han registrado entrenamientos recientes."

    plan_context = ""
    try:
        today_session = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.date == today_str,
            TrainingSession.status.in_(["planned", "active"])
        ).first()
        if today_session and today_session.plan_json:
            plan = json.loads(today_session.plan_json)
            plan_context = f"""--- SESIÓN PLANIFICADA HOY ---
Nombre: {plan.get('session_name', 'N/A')}
Duración: {plan.get('estimated_duration_min', 0)}min
Ejercicios: {len(plan.get('exercises', []))}"""
    except Exception:
        pass

    memory_context = MemoryService.get_memory_context_string(db, user_id, max_tokens=1500)

    try:
        profile_context = AthleteProfileService.get_profile_summary(user_id, db)
    except Exception:
        profile_context = f"Atleta: {athlete_name}, {athlete_age} años. Objetivo: Proyecto 31/07."

    exercise_context = ExerciseService.get_context_summary()

    conversation_mode = "analysis"

    mode_inst = MODE_INSTRUCTIONS.get(conversation_mode, "").format(athlete_name=athlete_name)

    prompt = MASTER_SYSTEM_PROMPT.format(
        athlete_name=athlete_name,
        athlete_age=athlete_age,
        step_target=step_target,
        conversation_mode=conversation_mode.upper(),
        mode_instructions=mode_inst,
        today_date=today_str,
        biometrics_context=biometrics_context,
        injury_context=injury_context,
        readiness_context=readiness_context,
        acwr_context=acwr_context,
        workouts_context=workouts_context,
        plan_context=plan_context,
        memory_context=memory_context,
        profile_context=profile_context,
        exercise_context=exercise_context,
    )

    bio_summary = ""
    if today_bio and today_bio.data:
        try:
            bd = json.loads(today_bio.data)
            bio_summary = f"HRV:{bd.get('hrv', 0)} FCR:{bd.get('heartRate', 0)}"
        except Exception:
            pass
    injury_summary = "active_injury" if active_injuries else "clear"

    _prompt_cache[key] = {
        "result": {
            "prompt": prompt,
            "athlete_name": athlete_name,
            "athlete_age": athlete_age,
            "step_target": step_target,
            "readiness_score": readiness_score,
            "bio_summary": bio_summary,
            "injury_summary": injury_summary,
        },
        "ts": datetime.now(),
    }

    return _prompt_cache[key]["result"]

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
            

