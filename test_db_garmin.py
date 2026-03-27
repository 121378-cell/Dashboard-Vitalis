import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, "backend")
sys.path.insert(0, backend_path)

from backend.app.utils.garmin import get_garmin_client
from backend.app.models.token import Token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_sync")

def test_db_sync():
    db_url = "sqlite:///c:/Users/sergi/Nueva carpeta/Dashboard-Vitalis/atlas_v2.db"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        token = db.query(Token).filter(Token.user_id == 'default_user').first()
        if not token or not token.garmin_email or not token.garmin_password:
            logger.error("No credentials found in database for default_user")
            return
            
        logger.info(f"Testing Garmin connection for: {token.garmin_email}")
        
        # Use the utility directly
        client, session_updated = get_garmin_client(token.garmin_email, token.garmin_password)
        
        if client:
            logger.info("✅ Successfully connected to Garmin!")
            logger.info(f"Session updated: {session_updated}")
            
            if session_updated:
                token.garmin_session = "UPDATED_SESSION_MOCK" # We don't have the real session object here easily but get_garmin_client should handle it
                # db.commit() # Don't commit yet in test
                
            try:
                stats = client.get_stats("2026-03-27")
                logger.info(f"Successfully fetched stats for today")
            except Exception as e:
                logger.error(f"Failed to fetch stats: {e}")
        else:
            logger.error("❌ Failed to connect to Garmin")
            
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db_sync()
