"""
ATLAS Notifications Endpoints
============================

Endpoints for managing push notifications and FCM tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.push_service import push_service
from app.services.token_service import TokenService
from app.models.token import Token
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class FCMTokenRegister(BaseModel):
    """Model for registering FCM token."""
    fcm_token: str


class FCMTokenResponse(BaseModel):
    """Response model for FCM token operations."""
    success: bool
    message: str


@router.post("/register", response_model=FCMTokenResponse)
def register_fcm_token(
    token_data: FCMTokenRegister,
    db: Session = Depends(get_db),
    user_id: str = "default_user"  # In production, this would come from auth
):
    """
    Register or update FCM token for push notifications.
    
    Args:
        token_data: FCM token data
        db: Database session
        user_id: User ID (from authentication)
        
    Returns:
        FCMTokenResponse: Success status and message
    """
    try:
        success = push_service.register_token(
            db=db,
            user_id=user_id,
            fcm_token=token_data.fcm_token
        )
        
        if success:
            return FCMTokenResponse(
                success=True,
                message="FCM token registered successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to register FCM token"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering FCM token: {str(e)}"
        )


@router.get("/briefing/today")
def get_today_briefing(
    db: Session = Depends(get_db),
    user_id: str = "default_user"  # In production, this would come from auth
):
    """
    Get pre-generated briefing for today.
    
    Args:
        db: Database session
        user_id: User ID (from authentication)
        
    Returns:
        dict: Today's briefing content
    """
    try:
        from app.models.daily_briefing import DailyBriefing
        from datetime import date
        
        today = date.today()
        briefing = db.query(DailyBriefing).filter(
            DailyBriefing.user_id == user_id,
            DailyBriefing.date == today
        ).first()
        
        if not briefing:
            # Return empty briefing or generate on-the-fly?
            # For now, return empty structure
            return {
                "date": today.isoformat(),
                "content": {},
                "message": "No briefing available for today"
            }
        
        import json
        content = json.loads(briefing.content) if briefing.content else {}
        
        return {
            "date": briefing.date.isoformat(),
            "content": content
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving briefing: {str(e)}"
        )


@router.post("/trigger", response_model=FCMTokenResponse)
def trigger_manual_sync(
    db: Session = Depends(get_db),
    user_id: str = "default_user"  # In production, this would come from auth
):
    """
    Trigger manual sync for a user.
    
    Args:
        db: Database session
        user_id: User ID (from authentication)
        
    Returns:
        FCMTokenResponse: Success status and message
    """
    try:
        # Import here to avoid circular imports
        from app.services.sync_service import SyncService
        from app.models.token import Token
        from app.utils.garmin import get_garmin_client
        from datetime import date, timedelta
        
        creds = db.query(Token).filter(Token.user_id == user_id).first()
        if not (creds and creds.garmin_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Garmin not connected"
            )
        
        # Get Garmin client
        client, login_result = get_garmin_client(
            email=creds.garmin_email,
            password=creds.garmin_password,
            db=db,
            user_id=user_id
        )
        
        if not client:
            if login_result == "rate_limited":
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Garmin rate limit exceeded"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not authenticate with Garmin"
                )
        
        # Sync last 7 days
        date_range = [(date.today() - timedelta(days=i)).isoformat() for i in range(7)]
        
        # Perform sync
        health_success = SyncService.sync_garmin_health(db, user_id, date_range, client=client)
        acts_success = SyncService.sync_garmin_activities(db, user_id, date_range, client=client)
        
        if not health_success and not acts_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync Garmin data"
            )
        
        # Calculate readiness
        from app.services.readiness_service import ReadinessService
        ReadinessService.calculate_and_store(db, user_id)
        
        # Generate memories
        from app.services.memory_service import MemoryService
        MemoryService.auto_generate_from_sync(
            db=db,
            user_id=user_id,
            # Additional parameters would go here
        )
        
        return FCMTokenResponse(
            success=True,
            message="Manual sync completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering sync: {str(e)}"
        )


# Export router
__all__ = ["router"]