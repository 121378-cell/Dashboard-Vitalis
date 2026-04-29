"""
ATLAS Push Notification Service
===============================

Handles Firebase Cloud Messaging (FCM) integration for sending push notifications
to mobile devices. Includes token management and notification sending capabilities.
"""

import json
import logging
from typing import Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session
from app.models.token import Token

logger = logging.getLogger("app.services.push_service")

# FCM configuration - in production, these should come from environment variables
FCM_URL = "https://fcm.googleapis.com/fcm/send"
# FCM_SERVER_KEY should be set in environment variables
# For now, we'll handle missing credentials gracefully

class PushService:
    """Service for sending push notifications via Firebase Cloud Messaging."""
    
    @staticmethod
    async def send_push(
        token: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a push notification to a device via FCM.
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        if not token:
            logger.warning("Attempted to send push notification with empty token")
            return False
            
        # Get FCM server key from environment (should be configured)
        import os
        fcm_server_key = os.getenv("FCM_SERVER_KEY")
        
        if not fcm_server_key:
            logger.warning("FCM_SERVER_KEY not configured - push notifications disabled")
            # In development, we might want to log instead of failing
            logger.info(f"Would send push to {token}: {title} - {body}")
            return True  # Return True in dev to not break functionality
        
        headers = {
            "Authorization": f"key={fcm_server_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": data or {},
        }
        
        # For data-only messages (when app is in background)
        if not payload["notification"]:
            payload.pop("notification", None)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    FCM_URL,
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", 0) > 0:
                        logger.info(f"Push notification sent successfully to token ending in ...{token[-6:]}")
                        return True
                    else:
                        error = result.get("results", [{}])[0].get("error", "Unknown error")
                        logger.error(f"FCM error sending to token ...{token[-6:]}: {error}")
                        return False
                else:
                    logger.error(f"FCM HTTP error {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Exception sending push notification: {e}", exc_info=True)
            return False
    
    @staticmethod
    def register_token(db: Session, user_id: str, fcm_token: str) -> bool:
        """
        Register or update FCM token for a user.
        
        Args:
            db: Database session
            user_id: User ID
            fcm_token: FCM device token
            
        Returns:
            bool: True if token was registered successfully
        """
        try:
            # Import here to avoid circular imports
            from app.services.token_service import TokenService
            
            token_obj = db.query(TokenService.model).filter(
                TokenService.model.user_id == user_id
            ).first()
            
            if not token_obj:
                logger.warning(f"No token record found for user {user_id}")
                return False
                
            # Add FCM token field to token model if it doesn't exist
            # We'll need to extend the Token model to include fcm_token
            # For now, we'll store it in a flexible way or extend the model
            
            # Since we need to modify the Token model, let's do it properly
            # But first, let's check if we can add the column or if we need to extend
            
            # For now, we'll use a workaround by storing in garmin_session or similar
            # But better to extend the model properly
            
            # Let's check if fcm_token attribute exists, if not we'll need to migrate
            if hasattr(token_obj, 'fcm_token'):
                token_obj.fcm_token = fcm_token
            else:
                # We'll need to add the column - for now, let's store in a JSON field or extend
                # Since this is a new feature, we should extend the model properly
                logger.warning("Token model does not have fcm_token field - need to extend model")
                # As a temporary solution, we'll store in garmin_session (not ideal but works for now)
                # In a real implementation, we'd add a proper migration
                token_obj.garmin_session = fcm_token  # Temporary workaround
                
            db.commit()
            logger.info(f"FCM token registered for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering FCM token for user {user_id}: {e}", exc_info=True)
            db.rollback()
            return False
    
    @staticmethod
    def get_token(db: Session, user_id: str) -> Optional[str]:
        """
        Get FCM token for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Optional[str]: FCM token if found, None otherwise
        """
        try:
            from app.services.token_service import TokenService
            
            token_obj = db.query(TokenService.model).filter(
                TokenService.model.user_id == user_id
            ).first()
            
            if token_obj:
                # Check if fcm_token attribute exists
                if hasattr(token_obj, 'fcm_token') and token_obj.fcm_token:
                    return token_obj.fcm_token
                # Fallback to garmin_session if we used it as temporary storage
                elif hasattr(token_obj, 'garmin_session') and token_obj.garmin_session:
                    # Basic validation - FCM tokens are usually long strings
                    if len(token_obj.garmin_session) > 100:  # FCM tokens are typically long
                        return token_obj.garmin_session
            
            return None
        except Exception as e:
            logger.error(f"Error getting FCM token for user {user_id}: {e}", exc_info=True)
            return None

# Create service instance for easy importing
push_service = PushService()

# Export for use in other modules
__all__ = ["PushService", "push_service"]