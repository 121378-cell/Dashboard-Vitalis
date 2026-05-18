"""
ATLAS Notification Service
============================

Sistema de notificaciones multi-canal (app, Telegram, sistema).
- Guarda notificaciones en SQLite
- Envía a Telegram y notificaciones de sistema
- Broadcast en tiempo real via WebSocket
- Integrado con DailyLoopService para briefings matutinos
"""

import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import httpx
from fastapi import WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("app.services.notification_service")

PRIORITY_EMOJI = {
    "urgent": "\U0001f6a8",
    "high": "\u26a0\ufe0f",
    "medium": "\U0001f4ca",
    "low": "\u2139\ufe0f",
}


class NotificationConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


ws_manager = NotificationConnectionManager()


class NotificationService:
    @staticmethod
    def _ensure_table(db: Session):
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notification_type TEXT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                channel_app BOOLEAN DEFAULT 1,
                channel_telegram BOOLEAN DEFAULT 0,
                channel_system BOOLEAN DEFAULT 0,
                sent_app BOOLEAN DEFAULT 0,
                sent_telegram BOOLEAN DEFAULT 0,
                sent_system BOOLEAN DEFAULT 0,
                read_at TIMESTAMP,
                action_url TEXT,
                metadata_json TEXT
            )
        """))
        db.commit()

    @staticmethod
    def send_notification(
        title: str,
        message: str,
        notification_type: str = "general",
        priority: str = "medium",
        channels: Optional[List[str]] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        if channels is None:
            channels = ["app"]

        if db is None:
            from app.db.session import SessionLocal
            db = SessionLocal()
            own_session = True
        else:
            own_session = False

        try:
            NotificationService._ensure_table(db)

            channel_app = 1 if "app" in channels else 0
            channel_telegram = 1 if "telegram" in channels else 0
            channel_system = 1 if "system" in channels else 0

            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

            result = db.execute(text("""
                INSERT INTO notifications (
                    notification_type, title, message, priority,
                    channel_app, channel_telegram, channel_system,
                    action_url, metadata_json
                ) VALUES (
                    :notification_type, :title, :message, :priority,
                    :channel_app, :channel_telegram, :channel_system,
                    :action_url, :metadata_json
                )
            """), {
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "priority": priority,
                "channel_app": channel_app,
                "channel_telegram": channel_telegram,
                "channel_system": channel_system,
                "action_url": action_url,
                "metadata_json": metadata_json,
            })
            db.commit()

            notification_id = result.lastrowid

            sent_channels = []
            errors = []

            if channel_telegram:
                ok = NotificationService.enviar_telegram(title, message, priority)
                if ok:
                    db.execute(text(
                        "UPDATE notifications SET sent_telegram = 1 WHERE id = :id"
                    ), {"id": notification_id})
                    db.commit()
                    sent_channels.append("telegram")
                else:
                    errors.append("telegram")

            if channel_system:
                ok = NotificationService.enviar_sistema(title, message)
                if ok:
                    db.execute(text(
                        "UPDATE notifications SET sent_system = 1 WHERE id = :id"
                    ), {"id": notification_id})
                    db.commit()
                    sent_channels.append("system")
                else:
                    errors.append("system")

            if channel_app:
                db.execute(text(
                    "UPDATE notifications SET sent_app = 1 WHERE id = :id"
                ), {"id": notification_id})
                db.commit()
                sent_channels.append("app")

                try:
                    notif_data = {
                        "id": notification_id,
                        "title": title,
                        "message": message,
                        "priority": priority,
                        "notification_type": notification_type,
                        "action_url": action_url,
                        "created_at": datetime.now().isoformat(),
                    }
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(ws_manager.broadcast({
                            "type": "notification",
                            "data": notif_data,
                        }))
                    else:
                        loop.run_until_complete(ws_manager.broadcast({
                            "type": "notification",
                            "data": notif_data,
                        }))
                except RuntimeError:
                    pass

            return {
                "id": notification_id,
                "sent_channels": sent_channels,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Error en send_notification: {e}", exc_info=True)
            db.rollback()
            return {"id": None, "sent_channels": [], "errors": [str(e)]}
        finally:
            if own_session:
                db.close()

    @staticmethod
    def enviar_telegram(title: str, message: str, priority: str) -> bool:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados. Saltando Telegram.")
            return False

        emoji = PRIORITY_EMOJI.get(priority, "\U0001f4ca")
        hora_actual = datetime.now().strftime("%H:%M")

        texto = f"{emoji} *{title}*\n{message}\n_ATLAS Coach \u00b7 {hora_actual}_"

        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": texto,
                    "parse_mode": "Markdown",
                },
                timeout=5.0,
            )
            if response.status_code == 200:
                logger.info(f"Notificación Telegram enviada: {title}")
                return True
            else:
                logger.warning(f"Telegram HTTP {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            logger.warning(f"Error enviando Telegram: {e}")
            return False

    @staticmethod
    def enviar_sistema(title: str, message: str) -> bool:
        try:
            from plyer import notification as plyer_notification
            plyer_notification.notify(
                title=title,
                message=message[:200],
                app_name="ATLAS Coach",
                timeout=10,
            )
            return True
        except Exception as e:
            logger.warning(f"Notificación sistema no disponible: {e}")
            return False

    @staticmethod
    def send_daily_briefing(daily_loop_result: Dict[str, Any], db: Optional[Session] = None):
        if daily_loop_result.get("error"):
            logger.warning("Daily loop tuvo error, saltando briefing")
            return

        score = daily_loop_result["readiness_score"]
        category = daily_loop_result["readiness_category"]
        session = daily_loop_result.get("today_session")
        insights = daily_loop_result.get("insights", [])

        lines = [
            f"\U0001f4ca *Readiness: {score}/100 \u2014 {category}*",
            f"\U0001f50b Body Battery: {daily_loop_result['components']['body_battery']['value']}%",
            f"\u2764\ufe0f FC Reposo: {daily_loop_result['components']['resting_hr']['value']} bpm",
            f"\U0001f634 Sue\u00f1o: {daily_loop_result['components']['sleep']['value']:.1f}h",
        ]

        if session and session.get("planned"):
            s = session["planned"]
            lines.append(f"\n\U0001f3cb\ufe0f *Sesi\u00f3n de hoy:* {s['title']} ({s['duration_minutes']}min)")
            if session.get("adaptation", {}).get("suggestion") != "mantener":
                lines.append(f"\u26a1 {session['adaptation']['note']}")

        high_insights = [i for i in insights if i.get("priority") == "high"]
        if high_insights:
            lines.append("\n*\u26a0\ufe0f Alertas:*")
            for insight in high_insights[:2]:
                lines.append(f"\u2022 {insight['message']}")

        message = "\n".join(lines)

        NotificationService.send_notification(
            title="\U0001f305 Buenos d\u00edas, Atleta",
            message=message,
            notification_type="daily_readiness",
            priority="high" if score < 50 else "medium",
            channels=["app", "telegram", "system"],
            action_url="/dashboard",
            metadata={"readiness_score": score},
            db=db,
        )

    @staticmethod
    def send_insight(insight: Dict[str, Any], db: Optional[Session] = None):
        channels = ["app"]
        if insight.get("priority") == "high":
            channels.append("telegram")

        NotificationService.send_notification(
            title=insight.get("title", "Insight"),
            message=insight.get("message", ""),
            notification_type="insight",
            priority=insight.get("priority", "medium"),
            channels=channels,
            action_url="/dashboard",
            db=db,
        )

    @staticmethod
    def get_unread(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        NotificationService._ensure_table(db)
        rows = db.execute(text("""
            SELECT id, created_at, notification_type, title, message, priority,
                   channel_app, channel_telegram, channel_system,
                   sent_app, sent_telegram, sent_system,
                   read_at, action_url, metadata_json
            FROM notifications
            WHERE read_at IS NULL
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()

        return [NotificationService._row_to_dict(row) for row in rows]

    @staticmethod
    def mark_read(db: Session, notification_id: int) -> bool:
        NotificationService._ensure_table(db)
        result = db.execute(text(
            "UPDATE notifications SET read_at = :now WHERE id = :id"
        ), {"now": datetime.now().isoformat(), "id": notification_id})
        db.commit()
        return result.rowcount > 0

    @staticmethod
    def mark_all_read(db: Session) -> int:
        NotificationService._ensure_table(db)
        result = db.execute(text(
            "UPDATE notifications SET read_at = :now WHERE read_at IS NULL"
        ), {"now": datetime.now().isoformat()})
        db.commit()
        return result.rowcount

    @staticmethod
    def get_history(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        NotificationService._ensure_table(db)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = db.execute(text("""
            SELECT id, created_at, notification_type, title, message, priority,
                   channel_app, channel_telegram, channel_system,
                   sent_app, sent_telegram, sent_system,
                   read_at, action_url, metadata_json
            FROM notifications
            WHERE created_at >= :cutoff
            ORDER BY created_at DESC
        """), {"cutoff": cutoff}).fetchall()

        return [NotificationService._row_to_dict(row) for row in rows]

    @staticmethod
    def get_unread_count(db: Session) -> int:
        NotificationService._ensure_table(db)
        row = db.execute(text(
            "SELECT COUNT(*) FROM notifications WHERE read_at IS NULL"
        )).fetchone()
        return row[0] if row else 0

    @staticmethod
    def get_recent_for_ws(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        NotificationService._ensure_table(db)
        rows = db.execute(text("""
            SELECT id, created_at, notification_type, title, message, priority,
                   channel_app, channel_telegram, channel_system,
                   sent_app, sent_telegram, sent_system,
                   read_at, action_url, metadata_json
            FROM notifications
            WHERE read_at IS NULL
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()

        return [NotificationService._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        return {
            "id": row[0],
            "created_at": str(row[1]) if row[1] else None,
            "notification_type": row[2],
            "title": row[3],
            "message": row[4],
            "priority": row[5],
            "channel_app": bool(row[6]),
            "channel_telegram": bool(row[7]),
            "channel_system": bool(row[8]),
            "sent_app": bool(row[9]),
            "sent_telegram": bool(row[10]),
            "sent_system": bool(row[11]),
            "read_at": str(row[12]) if row[12] else None,
            "action_url": row[13],
            "metadata": json.loads(row[14]) if row[14] else None,
        }


    # ── Living ATLAS: Intervention Delivery ──

    @staticmethod
    def send_intervention(
        intervention,
        title: str,
        message: str,
        priority: str = "medium",
        channels: Optional[List[str]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Envía una notificación vinculada a una intervención de ATLAS."""
        if channels is None:
            from app.core.autonomy_policy import AutonomyLevel
            try:
                level = intervention.autonomy_level if hasattr(intervention, 'autonomy_level') else 1
                if level == AutonomyLevel.AUTONOMOUS or level == 1:
                    channels = ["app"]
                elif level == AutonomyLevel.PROPOSAL or level == 2:
                    channels = ["app", "system"]
                else:
                    channels = ["app", "telegram", "system"]
            except Exception:
                channels = ["app"]

        inter_id = intervention.id if hasattr(intervention, 'id') else None

        result = NotificationService.send_notification(
            title=title,
            message=message,
            notification_type="intervention",
            priority=priority,
            channels=channels,
            action_url="/dashboard?tab=live",
            metadata={"intervention_id": inter_id},
            db=db,
        )

        # Registrar delivered_at en la intervención
        if inter_id and result.get("id"):
            try:
                NotificationService._update_intervention_delivery(
                    intervention_id=inter_id,
                    field="delivered_at",
                    db=db,
                )
            except Exception as e:
                logger.warning(f"Error registrando delivery de intervención {inter_id}: {e}")

        return result

    @staticmethod
    def _update_intervention_delivery(
        intervention_id: int,
        field: str,
        value: Optional[str] = None,
        db: Optional[Session] = None,
    ):
        """Actualiza campos de tracking (delivered_at/opened_at) en una intervención."""
        if db is None:
            from app.db.session import SessionLocal
            db = SessionLocal()
            own_session = True
        else:
            own_session = False

        try:
            from app.models.atlas_intervention import AtlasIntervention
            from datetime import datetime, timezone

            intervention = db.query(AtlasIntervention).filter(
                AtlasIntervention.id == intervention_id
            ).first()

            if intervention:
                now = value or datetime.now(timezone.utc)
                if field == "delivered_at" and not intervention.delivered_at:
                    intervention.delivered_at = now
                elif field == "opened_at" and not intervention.opened_at:
                    intervention.opened_at = now
                db.commit()
        except Exception as e:
            logger.warning(f"Error updating intervention {intervention_id} field {field}: {e}")
            db.rollback()
        finally:
            if own_session:
                db.close()

    @staticmethod
    def mark_intervention_opened(
        intervention_id: int,
        db: Optional[Session] = None,
    ):
        """Registra que el usuario abrió una intervención."""
        NotificationService._update_intervention_delivery(
            intervention_id=intervention_id,
            field="opened_at",
            db=db,
        )


notification_service = NotificationService()
