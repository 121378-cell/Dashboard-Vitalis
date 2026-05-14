from fastapi import APIRouter, Depends, HTTPException, Body, Header
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id
from app.services.ai_service import AIService, build_coach_context, detect_conversation_mode, MODE_INSTRUCTIONS, generate_welcome_message
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
def chat(request: ChatRequest, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Enhanced coaching chat with dynamic ATLAS persona, mode detection, and session generation."""
    last_message = request.messages[-1].content if request.messages else ""

    try:
        workout_keywords = ["entreno", "sesión", "workout", "entrena", "ejercicio hoy",
                           "hacer ejercicio", "hacer deporte", "gym hoy", "entrenar"]
        is_workout_request = any(kw in last_message.lower() for kw in workout_keywords)
    except Exception as e:
        logger.error(f"Error detecting workout request: {e}")
        is_workout_request = False

    plan_trigger = any(kw in last_message.lower() for kw in ["generar plan", "plan semanal", "crear plan"])

    if is_workout_request and not plan_trigger:
        try:
            today_str = date.today().isoformat()
            existing_session = db.query(TrainingSession).filter(
                TrainingSession.user_id == user_id,
                TrainingSession.date == today_str
            ).first()

            if existing_session and existing_session.status in ["planned", "active"]:
                plan = json.loads(existing_session.plan_json) if existing_session.plan_json else {}
                context_result = build_coach_context(db, user_id)
                return {
                    "content": json.dumps(plan),
                    "provider": "atlas_session",
                    "session_id": existing_session.id,
                    "type": "session_plan",
                    "mode": "planning",
                    "context_meta": context_result.get("context_meta", {}),
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
                context_result = build_coach_context(db, user_id)
                return {
                    "content": json.dumps(plan),
                    "provider": "atlas_session",
                    "session_id": session.id,
                    "type": "session_plan",
                    "mode": "planning",
                    "context_meta": context_result.get("context_meta", {}),
                }
        except Exception as e:
            pass

    if plan_trigger:
        try:
            from app.services.training_plan_service import TrainingPlanService
            goal = "hipertrofia y fuerza"
            plan_result = TrainingPlanService.generate_weekly_plan(db, user_id, goal)
            context_result = build_coach_context(db, user_id)
            if plan_result.get("error"):
                return {
                    "content": plan_result["error"],
                    "provider": "atlas_plan",
                    "type": "plan_exists",
                    "mode": "planning",
                    "plan_id": plan_result.get("plan_id"),
                    "context_meta": context_result.get("context_meta", {}),
                }
            return {
                "content": json.dumps(plan_result),
                "provider": "atlas_plan",
                "type": "weekly_plan",
                "mode": "planning",
                "plan_id": plan_result.get("plan_id"),
                "context_meta": context_result.get("context_meta", {}),
            }
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")

    context_result = build_coach_context(db, user_id)
    full_system_prompt = context_result["prompt"]
    athlete_name = context_result["athlete_name"]

    readiness_score = context_result.get("readiness_score")
    bio_summary = context_result.get("bio_summary", "")
    injury_summary = context_result.get("injury_summary", "clear")

    mode = detect_conversation_mode(last_message, bio_summary, injury_summary, readiness_score)

    mode_inst = MODE_INSTRUCTIONS.get(mode, "").format(athlete_name=athlete_name)

    full_system_prompt = full_system_prompt.replace(
        "MODO DE CONVERSACIÓN ACTUAL: {conversation_mode}",
        f"MODO DE CONVERSACIÓN ACTUAL: {mode.upper()}"
    )
    full_system_prompt = full_system_prompt.replace("{mode_instructions}", mode_inst)

    if "{conversation_mode}" in full_system_prompt:
        full_system_prompt = full_system_prompt.replace("{conversation_mode}", mode.upper())
    if "{mode_instructions}" in full_system_prompt:
        full_system_prompt = full_system_prompt.replace("{mode_instructions}", mode_inst)

    messages_list = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        result = AIService.chat(messages_list, full_system_prompt)
        return {
            "content": result["content"],
            "provider": result["provider"],
            "mode": mode,
            "context_meta": context_result.get("context_meta", {}),
        }
    except Exception as e:
        logger.error(f"AI Service failed: {e}")
        return {
            "content": "Lo siento, el servicio de IA no está disponible en este momento. Por favor, inténtalo de nuevo más tarde.",
            "provider": "error",
            "error": str(e),
            "mode": mode,
            "context_meta": context_result.get("context_meta", {}),
        }

@router.get("/welcome-message")
def welcome_message(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Get personalized ATLAS welcome message. Cached 15min server-side."""
    result = generate_welcome_message(db, user_id)
    return result

@router.get("/context-preview")
def context_preview(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Debug endpoint: returns the full system prompt and context meta without calling LLM."""
    context_result = build_coach_context(db, user_id)
    return {
        "system_prompt": context_result["prompt"],
        "context_meta": context_result.get("context_meta", {}),
        "athlete_name": context_result.get("athlete_name"),
        "athlete_age": context_result.get("athlete_age"),
        "readiness_score": context_result.get("readiness_score"),
        "bio_summary": context_result.get("bio_summary"),
        "injury_summary": context_result.get("injury_summary"),
    }

@router.post("/generate-plan")
def generate_plan(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
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
def daily_briefing(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    """Get the morning summary with deep analysis context."""
    context_result = build_coach_context(db, user_id)
    full_system_prompt = context_result["prompt"]

    system_instr = f"{full_system_prompt}\n\nDa un resumen estructurado en 3 secciones: 1. Estado de Recuperación, 2. Análisis de Carga (ACWR), 3. Recomendación del día."
    prompt = "Genera mi Daily Briefing matutino basado en los datos proporcionados. Sé técnico pero motivador."

    try:
        briefing = ai_service.generate_response(prompt, system_instr)
        return {"briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
