from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.services.community_service import CommunityService
from app.db.session import get_db
from app.models.user import User
from app.core.auth import get_current_active_user
from app.models.community import Challenge, ChallengeParticipant, ChallengeType

router = APIRouter(
    prefix="/community",
    tags=["community"]
)

@router.get("/leaderboard/{metric}")
async def get_leaderboard(
    metric: str,
    period: str = "weekly",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Solo usuarios ATLAS Pro pueden ver el leaderboard")
    
    service = CommunityService(db)
    leaderboard = service.get_leaderboard(metric, period)
    
    return {
        "leaderboard": [{
            "challenge_id": item["challenge_id"],
            "title": item["title"],
            "participants": [{
                "display_name": part["display_name"],
                "rank": part["rank"],
                "score": part["score"]
            } for part in item["leaderboard"]]
        } for item in leaderboard]
    }

@router.post("/challenges/{challenge_id}/join")
async def join_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = CommunityService(db)
    success = service.join_challenge(challenge_id, current_user.id)
    if not success:
        raise HTTPException(status_code=403, detail="Solo usuarios ATLAS Pro pueden participar en desafíos")
    
    return {"message": "Te has unido al desafío exitosamente"}

@router.get("/profile/{user_id}")
async def get_public_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    service = CommunityService(db)
    profile = service.get_public_profile(user_id)
    return {
        "user_id": user_id,
        "display_name": profile["display_name"],
        "avatar_url": profile["avatar_url"],
        "is_public": profile["is_public"],
        "statistics": profile["statistics"]
    }

# Endpoint para obtener desafíos activos
@router.get("/challenges/active")
async def get_active_challenges(
    db: Session = Depends(get_db)
):
    service = CommunityService(db)
    challenges = service.get_active_challenges()
    return [{
        "id": c.id,
        "title": c.title,
        "type": c.type.value if hasattr(c.type, 'value') else str(c.type),
        "prize_xp": c.prize_xp
    } for c in challenges]

@router.post("/challenges", response_model=dict)
async def create_challenge(
    title: str,
    type: ChallengeType,
    start_date: str,
    end_date: str,
    metric: str,
    description: Optional[str] = None,
    prize_xp: int = 0,
    db: Session = Depends(get_db)
):
    service = CommunityService(db)
    challenge = service.create_challenge(title, description, type, start_date, end_date, metric, prize_xp)
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "type": challenge.type.value if hasattr(challenge.type, 'value') else str(challenge.type),
        "start_date": challenge.start_date.isoformat(),
        "end_date": challenge.end_date.isoformat(),
        "metric": challenge.metric,
        "prize_xp": challenge.prize_xp
    }

@router.post("/participants", response_model=dict)
async def add_participant(
    challenge_id: int,
    user_id: str,
    current_value: float = 0.0,
    rank: int = 0,
    db: Session = Depends(get_db)
):
    # Verificar que el desafío exista y sea ACTIVO
    challenge = db.query(Challenge).get(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafío no encontrado")
    
    # Verificar que sea la fecha actual de inicio o posterior
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        if start_date_obj > datetime.utcnow():
            raise HTTPException(status_code=400, detail="El desafío no ha comenzado")
    except:
        # If we don't have start_date in the challenge object, we skip this check
        pass
    
    participant = ChallengeParticipant(
        challenge_id=challenge_id,
        user_id=user_id,
        current_value=current_value,
        rank=rank
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return {
        "id": participant.id,
        "challenge_id": participant.challenge_id,
        "user_id": participant.user_id,
        "current_value": participant.current_value,
        "rank": participant.rank
    }

@router.put("/participants/{user_id}/{challenge_id}")
async def update_participant(
    user_id: str,
    challenge_id: int,
    current_value: float,
    rank: int,
    db: Session = Depends(get_db)
):
    participant = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.user_id == user_id
    ).filter(
        ChallengeParticipant.challenge_id == challenge_id
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    
    participant.current_value = current_value
    participant.rank = rank
    db.commit()
    return {
        "id": participant.id,
        "challenge_id": participant.challenge_id,
        "user_id": participant.user_id,
        "current_value": participant.current_value,
        "rank": participant.rank
    }

@router.delete("/participants/{user_id}/{challenge_id}")
async def leave_challenge(
    user_id: str,
    challenge_id: int,
    db: Session = Depends(get_db)
):
    participant = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.user_id == user_id
    ).filter(
        ChallengeParticipant.challenge_id == challenge_id
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    
    db.delete(participant)
    db.commit()
    return {"detail": "Participante eliminado exitosamente"}

@router.get("/user/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id != user_id and not current_user.is_pro:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver este perfil")
    
    service = CommunityService(db)
    profile = service.get_public_profile(user_id)
    return {
        "profile": profile
    }

@router.get("/user/{user_id}/challenges")
async def get_user_challenges(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id != user_id and not current_user.is_pro:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver estos desafíos")
    
    # This is a simplified version - in reality we'd join with challenges and public profiles
    db = Session()
    participations = db.query(ChallengeParticipant).filter(ChallengeParticipant.user_id == user_id).all()
    challenges = db.query(Challenge).filter(Challenge.id.in_([p.challenge_id for p in participations])).all()
    return [{
        "challenge_id": p.challenge_id,
        "title": next((c.title for c in challenges if c.id == p.challenge_id), "Unknown"),
        "metric": p.current_value,
        "rank": p.rank,
        "prize": 0  # We don't have prize in participant, but we could join with challenge
    } for p in participations]

@router.get("/leaderboard/global/{metric}/{period}")
async def get_global_leaderboard(
    metric: str,
    period: str,
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_pro:
        raise HTTPException(status_code=403, detail="Solo ATLAS Pro pueden ver este leaderboard")
    
    service = CommunityService(db)
    return service.get_leaderboard(metric, period)

@router.get("/challenges/creator/{user_id}")
async def get_user_created_challenges(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id != user_id and not current_user.is_pro:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    service = CommunityService(db)
    return service.get_user_created_challenges(user_id)

# Note: The following endpoints are placeholders as they require additional methods in CommunityService
# We'll implement them in the service if needed, but for now we return empty lists or basic info

@router.get("/challenges/upcoming")
async def get_upcoming_challenges(
    db: Session = Depends(get_db)
):
    # Placeholder - would require implementation in service
    return []

@router.get("/challenges/history/{user_id}")
async def get_challenge_history(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id != user_id and not current_user.is_pro:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver el historial de desafíos")
    # Placeholder
    return []