"""
ATLAS Auto-Sync and Notification Scheduler
==========================================

Uses APScheduler to schedule:
- Daily Garmin sync for all users at 03:00 UTC
- Daily morning briefing generation at 05:30 UTC (07:30 Spain)
- Weekly report generation on Sundays at 20:00 UTC
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.token import Token

logger = logging.getLogger("app.services.scheduler_service")

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def sync_garmin_all_users():
    """Sync Garmin data for all authenticated users."""
    logger.info("Starting scheduled Garmin sync for all users")
    db = SessionLocal()
    try:
        # Get all users with Garmin credentials
        users_with_tokens = db.query(Token.user_id).filter(
            Token.garmin_email.isnot(None),
            Token.garmin_password.isnot(None)
        ).all()
        
        user_ids = [u[0] for u in users_with_tokens]
        logger.info(f"Found {len(user_ids)} users with Garmin credentials")
        
        for user_id in user_ids:
            try:
                logger.info(f"Syncing Garmin data for user {user_id}")
                
                # Get Garmin credentials
                token = db.query(Token).filter(Token.user_id == user_id).first()
                if not token:
                    continue
                
                # Import here to avoid circular imports
                from app.utils.garmin import get_garmin_client
                from app.services.sync_service import SyncService
                from datetime import datetime as dt
                
                # Get Garmin client
                client, login_result = get_garmin_client(
                    email=token.garmin_email,
                    password=token.garmin_password,
                    db=db,
                    user_id=user_id
                )
                
                if not client:
                    if login_result == "rate_limited":
                        logger.warning(f"Garmin rate limited for user {user_id}")
                    else:
                        logger.warning(f"Could not authenticate Garmin for user {user_id}")
                    continue
                
                # Sync last 7 days
                date_range = [(dt.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
                
                # Perform sync
                health_success = SyncService.sync_garmin_health(db, user_id, date_range, client=client)
                acts_success = SyncService.sync_garmin_activities(db, user_id, date_range, client=client)
                
                if health_success or acts_success:
                    logger.info(f"Completed sync for user {user_id}")
                    
                    # Calculate readiness
                    from app.services.readiness_service import ReadinessService
                    ReadinessService.calculate_and_store(db, user_id)
                    
                    # Auto-generate memories from sync
                    from app.services.memory_service import MemoryService
                    # Get recent data for memory generation
                    recent_biometrics = db.query().filter().all()  # Simplified
                    recent_workouts = db.query().filter().all()  # Simplified
                    MemoryService.auto_generate_from_sync(
                        db=db,
                        user_id=user_id,
                        biometrics_data=None,
                        workouts_data=[],
                        recent_biometrics=[]
                    )
                else:
                    logger.warning(f"Sync failed for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Error syncing user {user_id}: {e}", exc_info=True)
                continue
    finally:
        db.close()
    logger.info("Finished scheduled Garmin sync for all users")


async def generate_morning_briefings():
    """Generate morning briefings for all users and send push notifications."""
    logger.info("Starting scheduled morning briefing generation")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            try:
                logger.info(f"Generating morning briefing for user {user.id}")
                
                # Calculate readiness first (this stores it in daily_briefings)
                from app.services.readiness_service import ReadinessService
                readiness_result = ReadinessService.calculate_and_store(db, user.id)
                
                # Generate briefing with AI
                from app.services.ai_service import AIService
                ai_service = AIService()
                briefing_content = await ai_service.generate_morning_briefing(
                    db=db,
                    user_id=user.id,
                    readiness_result=readiness_result
                )
                
                # Save briefing to DB
                from app.models.daily_briefing import DailyBriefing
                import json
                
                today = date.today()
                existing = db.query(DailyBriefing).filter(
                    DailyBriefing.user_id == user.id,
                    DailyBriefing.date == today
                ).first()
                
                content_json = json.dumps(briefing_content)
                
                if existing:
                    existing.content = content_json
                else:
                    briefing = DailyBriefing(
                        id=f"{user.id}_{today.isoformat()}",
                        user_id=user.id,
                        date=today,
                        content=content_json
                    )
                    db.add(briefing)
                
                db.commit()
                
                # Send push notification if FCM token available
                token = db.query(Token).filter(Token.user_id == user.id).first()
                
                if token and token.fcm_token:
                    readiness_score = briefing_content.get('readiness_score', 0)
                    recommendation = briefing_content.get('recommendation', '')
                    
                    from app.services.push_service import push_service
                    await push_service.send_push(
                        token=token.fcm_token,
                        title="Buenos días 🌅",
                        body=f"Tu readiness hoy es {readiness_score}/100. {recommendation}",
                        data={"type": "morning_briefing", "user_id": user.id}
                    )
                    logger.info(f"Sent morning briefing push to user {user.id}")
                else:
                    logger.info(f"No FCM token for user {user.id}, skipping push")
                    
            except Exception as e:
                logger.error(f"Error generating briefing for user {user.id}: {e}", exc_info=True)
                continue
    finally:
        db.close()
    logger.info("Finished scheduled morning briefing generation")


async def weekly_report():
    """Generate weekly report and send push notification."""
    logger.info("Starting scheduled weekly report generation")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            try:
                logger.info(f"Generating weekly report for user {user.id}")
                
                # Generate weekly report with AI
                from app.services.ai_service import AIService
                ai_service = AIService()
                report_content = await ai_service.generate_weekly_report(
                    db=db,
                    user_id=user.id
                )
                
                # Send push notification if FCM token available
                token = db.query(Token).filter(Token.user_id == user.id).first()
                
                if token and token.fcm_token:
                    from app.services.push_service import push_service
                    await push_service.send_push(
                        token=token.fcm_token,
                        title="📊 Resumen semanal",
                        body=report_content.get('summary', 'Resumen semanal disponible'),
                        data={"type": "weekly_report", "user_id": user.id}
                    )
                    logger.info(f"Sent weekly report push to user {user.id}")
                else:
                    logger.info(f"No FCM token for user {user.id}, skipping weekly push")
                    
            except Exception as e:
                logger.error(f"Error generating weekly report for user {user.id}: {e}", exc_info=True)
                continue
    finally:
        db.close()
    logger.info("Finished scheduled weekly report generation")


def start_scheduler():
    """Start the APScheduler and add jobs."""
    logger.info("Starting ATLAS scheduler...")
    
    # Schedule Garmin sync: daily at 03:00 UTC
    scheduler.add_job(
        sync_garmin_all_users,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="sync_garmin_all_users",
        name="Sync Garmin data for all users",
        replace_existing=True
    )
    
    # Schedule morning briefings: daily at 05:30 UTC (07:30 Spain)
    scheduler.add_job(
        generate_morning_briefings,
        trigger=CronTrigger(hour=5, minute=30, timezone="UTC"),
        id="generate_morning_briefings",
        name="Generate morning briefings",
        replace_existing=True
    )
    
    # Schedule weekly report: weekly on Sunday at 20:00 UTC
    scheduler.add_job(
        weekly_report,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, timezone="UTC"),
        id="weekly_report",
        name="Generate weekly report",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("ATLAS scheduler started successfully")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    logger.info("Shutting down ATLAS scheduler...")
    scheduler.shutdown()
    logger.info("ATLAS scheduler shut down")


# Export for use in main.py
__all__ = ["start_scheduler", "shutdown_scheduler"]
