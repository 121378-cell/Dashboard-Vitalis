"""
ATLAS Auto-Sync and Notification Scheduler
==========================================

Uses APScheduler to schedule:
- Daily Garmin sync for all users at 03:00 UTC
- Daily morning briefing generation at 05:30 UTC (07:30 Spain)
- Weekly report generation on Sundays at 20:00 UTC
"""

import logging
import os
from datetime import datetime, date, timedelta, timezone
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
                    from app.models.biometrics import Biometrics
                    from app.models.workout import Workout
                    cutoff = (date.today() - timedelta(days=30)).isoformat()
                    recent_biometrics = db.query(Biometrics).filter(
                        Biometrics.user_id == user_id,
                        Biometrics.date >= cutoff
                    ).order_by(Biometrics.date.desc()).all()
                    recent_workouts = db.query(Workout).filter(
                        Workout.user_id == user_id,
                        Workout.date >= datetime.strptime(cutoff, "%Y-%m-%d")
                    ).order_by(Workout.date.desc()).limit(20).all()
                    MemoryService.auto_generate_from_sync(
                        db=db,
                        user_id=user_id,
                        biometrics_data=None,
                        workouts_data=[],
                        recent_biometrics=recent_biometrics
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


async def run_daily_loop_job():
    """Run the daily intelligence loop for all users."""
    logger.info("Starting scheduled daily loop")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            try:
                from app.services.daily_loop_service import DailyLoopService
                result = DailyLoopService.run_daily_loop(db, user.id)
                if not result.get("error"):
                    logger.info(f"Daily loop completado. Readiness: {result['readiness_score']}/100")
                else:
                    logger.error(f"Daily loop error for user {user.id}: {result.get('message')}")
            except Exception as e:
                logger.error(f"Error en daily loop para user {user.id}: {e}", exc_info=True)
                continue
    finally:
        db.close()
    logger.info("Finished scheduled daily loop")


async def hydration_reminder_job():
    """Send hydration reminder notifications."""
    logger.info("Starting hydration reminder")
    db = SessionLocal()
    try:
        from app.services.notification_service import NotificationService
        enabled = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"
        if not enabled:
            logger.info("Notifications disabled, skipping hydration reminder")
            return
        NotificationService.send_notification(
            title="\U0001f4a7 Hidrataci\u00f3n",
            message="Recuerda beber agua. Objetivo: ~625ml en esta toma.",
            notification_type="hydration",
            priority="low",
            channels=["app", "telegram"],
            db=db,
        )
    except Exception as e:
        logger.error(f"Error sending hydration reminder: {e}", exc_info=True)
    finally:
        db.close()
    logger.info("Finished hydration reminder")


# ──────────────────────────────────────────────
# LIVING ATLAS — Intervention Scan Jobs
# ──────────────────────────────────────────────


async def morning_intervention_scan():
    """(06:30 UTC) Escanea oportunidades de intervención matutina."""
    logger.info("Starting morning intervention scan")
    db = SessionLocal()
    try:
        from app.models.atlas_event import AtlasEvent
        from app.services.intervention_service import InterventionService
        from app.services.athlete_state_service import AthleteStateService

        users = db.query(User).all()
        for user in users:
            try:
                state = AthleteStateService.get_state(user.id)
                if state and state.risk_state in ("high", "acute"):
                    InterventionService.evaluate_triggers(
                        AtlasEvent(
                            event_type="morning_check",
                            user_id=user.id,
                            payload={}
                        )
                    )
            except Exception as e:
                logger.error(f"Error in morning scan for user {user.id}: {e}")
                continue
    finally:
        db.close()
    logger.info("Finished morning intervention scan")


async def midday_pulse_check():
    """(13:00 UTC) Check de medio día — ventanas de oportunidad."""
    logger.info("Starting midday pulse check")
    db = SessionLocal()
    try:
        from app.services.event_bus_service import emit
        users = db.query(User).all()
        for user in users:
            try:
                emit(
                    user_id=user.id,
                    event_type="midday_pulse",
                    payload={},
                    source="scheduler"
                )
            except Exception as e:
                logger.error(f"Error in midday pulse for user {user.id}: {e}")
                continue
    finally:
        db.close()
    logger.info("Finished midday pulse check")


async def evening_review_scan():
    """(20:00 UTC) Escaneo de cierre del día."""
    logger.info("Starting evening review scan")
    db = SessionLocal()
    try:
        from app.services.event_bus_service import emit
        users = db.query(User).all()
        for user in users:
            try:
                emit(
                    user_id=user.id,
                    event_type="evening_review",
                    payload={},
                    source="scheduler"
                )
            except Exception as e:
                logger.error(f"Error in evening scan for user {user.id}: {e}")
                continue
    finally:
        db.close()
    logger.info("Finished evening review scan")


async def missed_session_detection():
    """(cada 2h) Detecta sesiones planificadas no realizadas."""
    logger.info("Starting missed session detection")
    db = SessionLocal()
    try:
        from app.services.event_bus_service import emit
        from app.models.adaptive_training_plan import AdaptiveTrainingPlan, AdaptivePlannedSession

        now_utc = datetime.now(timezone.utc)
        today = date.today()

        users = db.query(User).all()
        for user in users:
            try:
                # Join through plan to get user's sessions (user_id lives on AdaptiveTrainingPlan)
                pending_sessions = db.query(AdaptivePlannedSession).join(
                    AdaptiveTrainingPlan,
                    AdaptivePlannedSession.plan_id == AdaptiveTrainingPlan.id
                ).filter(
                    AdaptiveTrainingPlan.user_id == user.id,
                    AdaptivePlannedSession.date == today,
                    AdaptivePlannedSession.status == "planned",
                ).all()

                for session in pending_sessions:
                    if session.scheduled_time:
                        scheduled_dt = datetime.combine(today, session.scheduled_time)
                        if now_utc > scheduled_dt + timedelta(hours=1):
                            emit(
                                user_id=user.id,
                                event_type="workout_missed",
                                payload={
                                    "session_id": session.id,
                                    "session_title": session.title,
                                    "scheduled_time": str(session.scheduled_time),
                                },
                                source="scheduler"
                            )
            except Exception as e:
                logger.error(f"Error detecting missed sessions for user {user.id}: {e}")
                continue
    finally:
        db.close()
    logger.info("Finished missed session detection")


# ──────────────────────────────────────────────
# LIVING ATLAS — Event Processor & Cleanup
# ──────────────────────────────────────────────


async def event_processor():
    """(cada 5 min) Procesa eventos pendientes en la cola."""
    logger.info("Starting event processor")
    try:
        from app.services.event_bus_service import process_pending
        result = process_pending()
        logger.info("Event processor completed")
    except Exception as e:
        logger.error(f"Error in event processor: {e}", exc_info=True)
    logger.info("Finished event processor")


async def cooldown_cleanup():
    """(cada 6h) Limpia cooldowns expirados de intervenciones."""
    logger.info("Starting cooldown cleanup")
    db = SessionLocal()
    try:
        from app.models.atlas_intervention import AtlasIntervention

        now = datetime.now(timezone.utc)
        expired = db.query(AtlasIntervention).filter(
            AtlasIntervention.cooldown_until.isnot(None),
            AtlasIntervention.cooldown_until <= now
        ).all()

        count = len(expired)
        for intervention in expired:
            intervention.cooldown_until = None

        db.commit()
        logger.info(f"Cleaned up {count} expired cooldowns")
    except Exception as e:
        logger.error(f"Error in cooldown cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
    logger.info("Finished cooldown cleanup")


async def cleanup_old_events():
    """(semanal, domingo 03:00 UTC) Limpia eventos e intervenciones antiguas."""
    logger.info("Starting cleanup of old events and interventions")
    db = SessionLocal()
    try:
        from app.services.event_bus_service import cleanup_events
        cleanup_events(older_than_days=30)

        from app.models.atlas_intervention import AtlasIntervention
        cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        deleted = db.query(AtlasIntervention).filter(
            AtlasIntervention.created_at < cutoff,
            AtlasIntervention.status.in_(["executed", "expired", "rejected"])
        ).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} old interventions (>60 days)")
    except Exception as e:
        logger.error(f"Error in cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
    logger.info("Finished cleanup of old events and interventions")


async def generate_weekly_plan_for_all_users():
    """Generate new weekly training plan for all users every Sunday."""
    logger.info("Starting scheduled weekly plan generation for all users")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            try:
                logger.info(f"Generating weekly plan for user {user.id}")

                from app.services.planner_service import TrainingPlannerService

                planner = TrainingPlannerService()
                plan = await planner.generate_weekly_plan(db, user.id)

                token = db.query(Token).filter(Token.user_id == user.id).first()

                if token and token.fcm_token:
                    from app.services.push_service import push_service
                    await push_service.send_push(
                        token=token.fcm_token,
                        title="Nuevo Plan Semanal",
                        body=f"Tu plan para la semana {plan.get('week_start', '')} esta listo. {plan.get('structure_name', '')}",
                        data={"type": "weekly_plan", "user_id": user.id},
                    )
                    logger.info(f"Sent weekly plan notification to user {user.id}")

            except Exception as e:
                logger.error(f"Error generating weekly plan for user {user.id}: {e}", exc_info=True)
                continue
    finally:
        db.close()
    logger.info("Finished scheduled weekly plan generation")


def start_scheduler():
    """Start the APScheduler and add jobs."""
    logger.info("Starting ATLAS scheduler...")

    scheduler.add_job(
        sync_garmin_all_users,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="sync_garmin_all_users",
        name="Sync Garmin data for all users",
        replace_existing=True,
    )

    scheduler.add_job(
        generate_morning_briefings,
        trigger=CronTrigger(hour=5, minute=30, timezone="UTC"),
        id="generate_morning_briefings",
        name="Generate morning briefings",
        replace_existing=True,
    )

    scheduler.add_job(
        run_daily_loop_job,
        trigger=CronTrigger(hour=5, minute=15, timezone="UTC"),
        id="daily_loop",
        name="Daily intelligence loop (readiness + adaptation)",
        replace_existing=True,
    )

    scheduler.add_job(
        hydration_reminder_job,
        trigger=CronTrigger(hour=8, minute=0, timezone="UTC"),
        id="hydration_reminder_10",
        name="Hydration reminder 10:00",
        replace_existing=True,
    )

    scheduler.add_job(
        hydration_reminder_job,
        trigger=CronTrigger(hour=11, minute=0, timezone="UTC"),
        id="hydration_reminder_13",
        name="Hydration reminder 13:00",
        replace_existing=True,
    )

    scheduler.add_job(
        hydration_reminder_job,
        trigger=CronTrigger(hour=14, minute=0, timezone="UTC"),
        id="hydration_reminder_16",
        name="Hydration reminder 16:00",
        replace_existing=True,
    )

    scheduler.add_job(
        hydration_reminder_job,
        trigger=CronTrigger(hour=17, minute=0, timezone="UTC"),
        id="hydration_reminder_19",
        name="Hydration reminder 19:00",
        replace_existing=True,
    )

    scheduler.add_job(
        generate_weekly_plan_for_all_users,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, timezone="UTC"),
        id="generate_weekly_plan",
        name="Generate weekly training plan",
        replace_existing=True,
    )

    scheduler.add_job(
        weekly_report,
        trigger=CronTrigger(day_of_week="sun", hour=20, minute=0, timezone="UTC"),
        id="weekly_report",
        name="Generate weekly report",
        replace_existing=True,
    )

    # ── Living ATLAS — Intervention Scans ──
    scheduler.add_job(
        morning_intervention_scan,
        trigger=CronTrigger(hour=6, minute=30, timezone="UTC"),
        id="morning_intervention_scan",
        name="Morning intervention scan",
        replace_existing=True,
    )
    scheduler.add_job(
        midday_pulse_check,
        trigger=CronTrigger(hour=13, minute=0, timezone="UTC"),
        id="midday_pulse_check",
        name="Midday pulse check",
        replace_existing=True,
    )
    scheduler.add_job(
        evening_review_scan,
        trigger=CronTrigger(hour=20, minute=0, timezone="UTC"),
        id="evening_review_scan",
        name="Evening review scan",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=8, minute=0, timezone="UTC"),
        id="missed_session_detection_08",
        name="Missed session detection 08:00",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=10, minute=0, timezone="UTC"),
        id="missed_session_detection_10",
        name="Missed session detection 10:00",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=12, minute=0, timezone="UTC"),
        id="missed_session_detection_12",
        name="Missed session detection 12:00",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=14, minute=0, timezone="UTC"),
        id="missed_session_detection_14",
        name="Missed session detection 14:00",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=16, minute=0, timezone="UTC"),
        id="missed_session_detection_16",
        name="Missed session detection 16:00",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=18, minute=0, timezone="UTC"),
        id="missed_session_detection_18",
        name="Missed session detection 18:00",
        replace_existing=True,
    )
    scheduler.add_job(
        missed_session_detection,
        trigger=CronTrigger(hour=20, minute=0, timezone="UTC"),
        id="missed_session_detection_20",
        name="Missed session detection 20:00",
        replace_existing=True,
    )

    # ── Living ATLAS — Event Processor & Cleanup ──
    scheduler.add_job(
        event_processor,
        trigger=CronTrigger(minute="*/5"),
        id="event_processor",
        name="Process pending events",
        replace_existing=True,
    )
    scheduler.add_job(
        cooldown_cleanup,
        trigger=CronTrigger(hour="*/6"),
        id="cooldown_cleanup",
        name="Cleanup expired cooldowns",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_old_events,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
        id="cleanup_old_events",
        name="Cleanup old events and interventions",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("ATLAS scheduler started successfully")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    logger.info("Shutting down ATLAS scheduler...")
    scheduler.shutdown()
    logger.info("ATLAS scheduler shut down")


# Export for use in main.py
__all__ = [
    "start_scheduler", "shutdown_scheduler",
    "morning_intervention_scan", "midday_pulse_check", "evening_review_scan",
    "missed_session_detection", "event_processor",
    "cooldown_cleanup", "cleanup_old_events",
]
