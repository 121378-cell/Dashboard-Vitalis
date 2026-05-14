"""
ATLAS Notifications Endpoints
===========================

Endpoints for managing notifications: unread, mark_read, history, send.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.api.deps import get_db, get_current_user_id
from app.services.notification_service import NotificationService

router = APIRouter()


class SendNotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str = "general"
    priority: str = "medium"
    channels: List[str] = ["app"]
    action_url: Optional[str] = None
    metadata: Optional[dict] = None


class MarkReadRequest(BaseModel):
    id: Optional[int] = None
    all: bool = False


@router.get("/unread")
def get_unread(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return NotificationService.get_unread(db, limit)


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
):
    return {"count": NotificationService.get_unread_count(db)}


@router.post("/mark-read")
def mark_read(
    req: MarkReadRequest,
    db: Session = Depends(get_db),
):
    if req.all:
        count = NotificationService.mark_all_read(db)
        return {"success": True, "marked": count}
    elif req.id:
        ok = NotificationService.mark_read(db, req.id)
        if not ok:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"success": True, "marked": 1}
    else:
        raise HTTPException(status_code=400, detail="Provide 'id' or 'all=true'")


@router.get("/history")
def get_history(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return NotificationService.get_history(db, days)


@router.post("/send")
def send_notification(
    req: SendNotificationRequest,
    db: Session = Depends(get_db),
):
    result = NotificationService.send_notification(
        title=req.title,
        message=req.message,
        notification_type=req.notification_type,
        priority=req.priority,
        channels=req.channels,
        action_url=req.action_url,
        metadata=req.metadata,
        db=db,
    )
    return result


class FCMTokenRegister(BaseModel):
    fcm_token: str


class FCMTokenResponse(BaseModel):
    success: bool
    message: str


@router.post("/register", response_model=FCMTokenResponse)
def register_fcm_token(
    token_data: FCMTokenRegister,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        from app.services.push_service import push_service
        success = push_service.register_token(db=db, user_id=user_id, fcm_token=token_data.fcm_token)
        if success:
            return FCMTokenResponse(success=True, message="FCM token registered successfully")
        else:
            raise HTTPException(status_code=400, detail="Failed to register FCM token")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering FCM token: {str(e)}")


@router.get("/briefing/today")
def get_today_briefing(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        from app.models.daily_briefing import DailyBriefing
        from datetime import date
        import json

        today = date.today()
        briefing = db.query(DailyBriefing).filter(
            DailyBriefing.user_id == user_id,
            DailyBriefing.date == today
        ).first()

        if not briefing:
            return {"date": today.isoformat(), "content": {}, "message": "No briefing available for today"}

        content = json.loads(briefing.content) if briefing.content else {}
        return {"date": briefing.date.isoformat(), "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving briefing: {str(e)}")


__all__ = ["router"]
