"""
ATLAS Notifications WebSocket
==============================

WebSocket endpoint for real-time notification delivery.
- Requires JWT token as query parameter: ?token=<jwt>
- Sends last 5 unread on connect
- Broadcasts new notifications to all connected clients
"""

import json
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_id_from_token
from app.services.notification_service import ws_manager, NotificationService

router = APIRouter()


@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Validar token JWT del query parameter
    try:
        user_id = get_current_user_id_from_token(token)
    except HTTPException:
        await websocket.close(code=4001, reason="Token invalido o expirado")
        return
    except Exception:
        await websocket.close(code=4001, reason="Error de autenticacion")
        return

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
