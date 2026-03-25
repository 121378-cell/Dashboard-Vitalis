from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ai_service import AIService
from app.models.biometrics import Biometrics
from datetime import date
import json

router = APIRouter()
ai_service = AIService()

@router.post("/chat")
def chat(
    db: Session = Depends(get_db),
    user_id: str = Body("default_user"),
    message: str = Body(...)
):
    """General coaching chat with context."""
    # Fetch recent context for the prompt
    today_str = date.today().isoformat()
    bio = db.query(Biometrics).filter(Biometrics.user_id == user_id, Biometrics.date == today_str).first()
    
    context = ""
    if bio:
        data = json.loads(bio.data)
        context = f"Contexto biométrico de hoy: HRV={data.get('hrv')}, Sueño={data.get('sleep')}h, Pasos={data.get('steps')}.\n"
    
    system_instr = "Eres ATLAS, el Advanced Training & Lifestyle Assistant. Eres un coach de élite."
    prompt = f"{context}Usuario: {message}"
    
    try:
        response = ai_service.generate_response(prompt, system_instr)
        return {"response": response, "provider": "atlas_v1"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-plan")
def generate_plan(
    db: Session = Depends(get_db),
    user_id: str = Body("default_user"),
    objective: str = Body("hipertrofia"),
    level: str = Body("intermedio")
):
    """Generate a 4-week training plan."""
    prompt = f"Genera un plan de 4 semanas para un atleta con objetivo '{objective}' y nivel '{level}'. Responde ÚNICAMENTE con JSON."
    system_instr = "Eres un experto en periodización. Formato JSON: {weeks: [...]}"
    
    try:
        # For simplicity, we just leverage the AI service to get the JSON structure
        plan_json = ai_service.generate_response(prompt, system_instr)
        # Parse and save to DB (omitted logic for brevity in this initial port)
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
