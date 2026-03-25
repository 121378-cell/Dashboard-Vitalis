from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ai_service import AIService
from app.services.context_service import ContextService
from app.models.biometrics import Biometrics
from pydantic import BaseModel
from datetime import date
from typing import List, Optional
import json

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
    """Enhanced coaching chat with real-time context injection."""
    # REQ-B25: Inject coach context from ContextService
    coach_context = ContextService.get_full_coach_context(db, user_id)
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
        raise HTTPException(status_code=500, detail=str(e))

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
