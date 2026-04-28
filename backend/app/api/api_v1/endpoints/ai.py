from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ai_service import AIService
from app.services.context_service import ContextService
from app.services.session_service import SessionService
from app.services.memory_service import MemoryService
from app.models.biometrics import Biometrics
from app.models.session import TrainingSession
from pydantic import BaseModel
from datetime import date, timedelta
from typing import List, Optional
import json
import re
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
ai_service = AIService()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    system_prompt: Optional[str] = "Eres ATLAS, el Advanced Training & Lifestyle Assistant."

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db), user_id: str = "default_user"):
    """Enhanced coaching chat with real-time context injection and session generation."""
    try:
        # Detectar si el usuario pide un entreno
        last_message = request.messages[-1].content.lower() if request.messages else ""
        workout_keywords = ["entreno", "sesión", "workout", "entrena", "ejercicio hoy", 
                            "hacer ejercicio", "hacer deporte", "gym hoy", "entrenar"]
        
        is_workout_request = any(kw in last_message for kw in workout_keywords)
    except Exception as e:
        logger.error(f"Error detecting workout request: {e}")
        is_workout_request = False
    
    # Si pide entreno, generar sesión automáticamente
    if is_workout_request:
        try:
            # Verificar si ya hay sesión para hoy
            today_str = date.today().isoformat()
            existing_session = db.query(TrainingSession).filter(
                TrainingSession.user_id == user_id,
                TrainingSession.date == today_str
            ).first()
            
            if existing_session and existing_session.status in ["planned", "active"]:
                # Devolver sesión existente
                plan = json.loads(existing_session.plan_json) if existing_session.plan_json else {}
                return {
                    "content": json.dumps(plan),
                    "provider": "atlas_session",
                    "session_id": existing_session.id,
                    "type": "session_plan"
                }
            else:
                # Generar nueva sesión
                plan = SessionService.generate_session_plan(user_id, db, date.today())
                
                # Guardar en BD
                session = TrainingSession(
                    user_id=user_id,
                    date=today_str,
                    status="planned",
                    generated_by="atlas",
                    plan_json=json.dumps(plan)
                )
                db.add(session)
                db.commit()
                
                return {
                    "content": json.dumps(plan),
                    "provider": "atlas_session",
                    "session_id": session.id,
                    "type": "session_plan"
                }
        except Exception as e:
            # Si falla la generación de sesión, continuar con chat normal
            pass
    
    # REQ-B25: Inject coach context from ContextService
    coach_context = ContextService.get_full_coach_context(db, user_id)
    
    # Añadir sesión planificada al contexto si existe
    try:
        today_str = date.today().isoformat()
        today_session = db.query(TrainingSession).filter(
            TrainingSession.user_id == user_id,
            TrainingSession.date == today_str,
            TrainingSession.status.in_(["planned", "active"])
        ).first()
        
        if today_session and today_session.plan_json:
            plan = json.loads(today_session.plan_json)
            session_context = f"\n\n📅 SESIÓN PLANIFICADA PARA HOY ({today_str}):\n"
            session_context += f"Nombre: {plan.get('session_name', 'N/A')}\n"
            session_context += f"Duración estimada: {plan.get('estimated_duration_min', 0)} min\n"
            session_context += f"Ejercicios: {len(plan.get('exercises', []))}\n"
            coach_context += session_context
    except Exception:
        pass  # No crítico si falla

    # Inject LTM (Long-Term Memory) context
    try:
        memory_context = MemoryService.get_memory_context_string(db, user_id)
        if memory_context:
            coach_context += memory_context
    except Exception:
        pass  # Non-critical

    full_system_prompt = f"{coach_context}\n\n{request.system_prompt or ''}"
        
    # Convert Pydantic messages to list of dicts for AIService
    messages_list = [{"role": m.role, "content": m.content} for m in request.messages]
        
    try:
        # Pass the enriched context to the LLM
        result = AIService.chat(messages_list, full_system_prompt)
        return {
            "content": result["content"],
            "provider": result["provider"]
        }
    except Exception as e:
        logger.error(f"AI Service failed: {e}")
        return {
            "content": "Lo siento, el servicio de IA no está disponible en este momento. Por favor, inténtalo de nuevo más tarde.",
            "provider": "error",
            "error": str(e)
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
    coach_context = ContextService.get_full_coach_context(db, user_id)
    
    prompt = "Genera mi Daily Briefing matutino basado en los datos proporcionados. Sé técnico pero motivador."
    system_instr = f"{coach_context}\n\nEres ATLAS. Da un resumen estructurado en 3 secciones: 1. Estado de Recuperación, 2. Análisis de Carga (ACWR), 3. Recomendación del día."
    
    try:
        briefing = ai_service.generate_response(prompt, system_instr)
        return {"briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
