from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ai_service import AIService, build_atlas_system_prompt, detect_conversation_mode, MODE_INSTRUCTIONS
from app.services.session_service import SessionService
from app.models.session import TrainingSession
from pydantic import BaseModel
from datetime import date
from typing import List, Optional
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
ai_service = AIService()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    system_prompt: Optional[str] = None

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db), user_id: str = "default_user"):
    """Enhanced coaching chat with dynamic ATLAS persona, mode detection, and session generation."""
    last_message = request.messages[-1].content if request.messages else ""

    try:
        workout_keywords = ["entreno", "sesión", "workout", "entrena", "ejercicio hoy",
            "hacer ejercicio", "hacer deporte", "gym hoy", "entrenar"]
        is_workout_request = any(kw in last_message.lower() for kw in workout_keywords)
    except Exception as e:
        logger.error(f"Error detecting workout request: {e}")
        is_workout_request = False

    detected_mode = None
    if is_workout_request:
        try:
            today_str = date.today().isoformat()
            existing_session = db.query(TrainingSession).filter(
                TrainingSession.user_id == user_id,
                TrainingSession.date == today_str
            ).first()

            if existing_session and existing_session.status in ["planned", "active"]:
                plan = json.loads(existing_session.plan_json) if existing_session.plan_json else {}
                detected_mode = "planning"
                return {
                    "content": json.dumps(plan),
                    "provider": "atlas_session",
                    "session_id": existing_session.id,
                    "type": "session_plan",
                    "mode": "planning"
                }
            else:
                plan = SessionService.generate_session_plan(user_id, db, date.today())
                session = TrainingSession(
                    user_id=user_id,
                    date=today_str,
                    status="planned",
                    generated_by="atlas",
                    plan_json=json.dumps(plan)
                )
                db.add(session)
                db.commit()
                detected_mode = "planning"
                return {
                    "content": json.dumps(plan),
                    "provider": "atlas_session",
                    "session_id": session.id,
                    "type": "session_plan",
                    "mode": "planning"
                }
        except Exception as e:
            pass

    # Build dynamic ATLAS system prompt with real-time context
    prompt_result = build_atlas_system_prompt(db, user_id)
    full_system_prompt = prompt_result["prompt"]
    athlete_name = prompt_result["athlete_name"]

    # Use cached context values from build_atlas_system_prompt (avoids double DB queries)
    readiness_score = prompt_result.get("readiness_score")
    bio_summary = prompt_result.get("bio_summary", "")
    injury_summary = prompt_result.get("injury_summary", "clear")

    mode = detect_conversation_mode(last_message, bio_summary, injury_summary, readiness_score)

    mode_inst = MODE_INSTRUCTIONS.get(mode, "").format(athlete_name=athlete_name)

    full_system_prompt = full_system_prompt.replace(
        "MODO DE CONVERSACIÓN ACTUAL: ANALYSIS",
        f"MODO DE CONVERSACIÓN ACTUAL: {mode.upper()}"
    )

    import re as _re
    pattern = r'INSTRUCCIÓN DE MODO:.*?(?=\n\nCONTEXTO REAL|CONTEXTO REAL|\Z)'
    full_system_prompt = _re.sub(pattern, mode_inst, full_system_prompt, flags=_re.DOTALL)

    # Convert Pydantic messages to list of dicts for AIService
    messages_list = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        result = AIService.chat(messages_list, full_system_prompt)
        return {
            "content": result["content"],
            "provider": result["provider"],
            "mode": mode
        }
    except Exception as e:
        logger.error(f"AI Service failed: {e}")
        return {
            "content": "Lo siento, el servicio de IA no está disponible en este momento. Por favor, inténtalo de nuevo más tarde.",
            "provider": "error",
            "error": str(e),
            "mode": mode
            }

@router.post("/generate-plan")
def generate_plan(
    db: Session = Depends(get_db),
    user_id: str = "default_user",
    objective: str = "hipertrofia",
    level: str = "intermedio"
):
    """Generate a 4-week training plan."""
    prompt = f"Genera un plan de 4 semanas para un atleta con objetivo '{objective}' y nivel '{level}'. Responde ÚNICAMENTE con JSON."
    system_instr = "Eres un experto en periodización. Formato JSON: {weeks: [...]}"
    
    try:
        plan_json = ai_service.generate_response(prompt, system_instr)
        return {"plan": json.loads(plan_json)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/daily-briefing")
def daily_briefing(db: Session = Depends(get_db), user_id: str = "default_user"):
    """Get the morning summary with deep analysis context."""
    prompt_result = build_atlas_system_prompt(db, user_id)
    full_system_prompt = prompt_result["prompt"]

    system_instr = f"{full_system_prompt}\n\nDa un resumen estructurado en 3 secciones: 1. Estado de Recuperación, 2. Análisis de Carga (ACWR), 3. Recomendación del día."
    prompt = "Genera mi Daily Briefing matutino basado en los datos proporcionados. Sé técnico pero motivador."

    try:
        briefing = ai_service.generate_response(prompt, system_instr)
        return {"briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
