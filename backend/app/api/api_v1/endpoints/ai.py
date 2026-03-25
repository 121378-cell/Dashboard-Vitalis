from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ai_service import AIService
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
    """Enhanced coaching chat with message history."""
    # Convert Pydantic messages to list of dicts for AIService
    messages_list = [{"role": m.role, "content": m.content} for m in request.messages]
    
    try:
        # Use AIService's chat method which handles fallback and history
        result = AIService.chat(messages_list, request.system_prompt)
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
    """Get the morning summary."""
    today_str = date.today().isoformat()
    bio = db.query(Biometrics).filter(Biometrics.user_id == user_id, Biometrics.date == today_str).first()
    
    if not bio:
        return {"briefing": "Aún no hay datos biométricos para hoy. ¡Sincroniza tu Garmin!"}
    
    data = json.loads(bio.data)
    prompt = f"Genera un briefing corto basado en: HRV={data.get('hrv')}, Sueño={data.get('sleep')}h, Pasos={data.get('steps')}."
    system_instr = "Eres ATLAS. Da un resumen motivador y técnico de 3 párrafos."
    
    try:
        briefing = ai_service.generate_response(prompt, system_instr)
        return {"briefing": briefing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
