"""
ATLAS Notifications WebSocket
==============================

WebSocket endpoint for real-time notification delivery.
- Sends last 5 unread on connect
- Broadcasts new notifications to all connected clients
"""

import json
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.notification_service import ws_manager, NotificationService

router = APIRouter()


@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    await ws_manager.connect(websocket)
    try:
        recent = NotificationService.get_recent_for_ws(db, limit=5)
        if recent:
            await websocket.send_json({
                "type": "initial",
                "data": recent,
            })

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")
                if action == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                    })
                elif action == "mark_read":
                    nid = message.get("id")
                    if nid:
                        NotificationService.mark_read(db, nid)
                        await websocket.send_json({
                            "type": "marked_read",
                            "id": nid,
                        })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


__all__ = ["router", "ws_manager"]
