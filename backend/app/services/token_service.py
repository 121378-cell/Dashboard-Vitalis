"""
ATLAS Token Service
==================

Service layer for token operations, providing a consistent interface
for accessing and manipulating user tokens.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.token import Token

class TokenService:
    """Service for handling token operations."""
    
    model = Token  # Reference to the Token model for use in queries
    
    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[Token]:
        """
        Get token by user ID.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Token object if found, None otherwise
        """
        return db.query(Token).filter(Token.user_id == user_id).first()
    
    @staticmethod
    def create_or_update(
        db: Session, 
        user_id: str, 
        garmin_email: Optional[str] = None,
        garmin_password: Optional[str] = None,
        fcm_token: Optional[str] = None,
        wger_api_key: Optional[str] = None,
        hevy_username: Optional[str] = None,
        strava_access_token: Optional[str] = None,
        strava_refresh_token: Optional[str] = None,
        strava_expires_at: Optional[str] = None,
        strava_athlete_id: Optional[str] = None,
        strava_connected: Optional[str] = None
    ) -> Token:
        """
        Create or update token for a user.
        
        Args:
            db: Database session
            user_id: User ID
            garmin_email: Garmin email
            garmin_password: Garmin password
            fcm_token: FCM token for push notifications
            wger_api_key: Wger API key
            hevy_username: Hevy username
            strava_access_token: Strava access token
            strava_refresh_token: Strava refresh token
            strava_expires_at: Strava token expiration
            strava_athlete_id: Strava athlete ID
            strava_connected: Strava connection status ("true" or "false")
            
        Returns:
            Token object
        """
        token = db.query(Token).filter(Token.user_id == user_id).first()
        
        if not token:
            token = Token(user_id=user_id)
            db.add(token)
        
        # Update fields if provided
        if garmin_email is not None:
            token.garmin_email = garmin_email
        if garmin_password is not None:
            token.garmin_password = garmin_password
        if fcm_token is not None:
            token.fcm_token = fcm_token
        if wger_api_key is not None:
            token.wger_api_key = wger_api_key
        if hevy_username is not None:
            token.hevy_username = hevy_username
        if strava_access_token is not None:
            token.strava_access_token = strava_access_token
        if strava_refresh_token is not None:
            token.strava_refresh_token = strava_refresh_token
        if strava_expires_at is not None:
            token.strava_expires_at = strava_expires_at
        if strava_athlete_id is not None:
            token.strava_athlete_id = strava_athlete_id
        if strava_connected is not None:
            token.strava_connected = strava_connected
            
        db.commit()
        db.refresh(token)
        return token

# Create service instance for easy importing
token_service = TokenService()

# Export for use in other modules
__all__ = ["TokenService", "token_service"]