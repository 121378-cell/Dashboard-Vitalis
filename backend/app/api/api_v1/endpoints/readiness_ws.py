"""
VITALIS WEBSOCKET MANAGER
========================
Sistema de streaming de datos en tiempo real para Readiness Score

Funcionalidades:
- Push automático cuando cambian los datos biométricos
- Recálculo en tiempo real cuando se sincroniza Garmin
- Notificaciones de alerta (score bajo, recuperación completa)
"""

import json
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# WebSocket imports
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """Gestiona las conexiones WebSocket activas."""
    
    def __init__(self):
        # user_id -> Set de WebSockets activos
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Cache del último readiness score por usuario
        self.last_scores: Dict[str, dict] = {}
        # Umbral de cambio para enviar update (evitar spam)
        self.score_threshold = 2.0  # Solo enviar si cambia > 2 puntos
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Enviar score actual inmediatamente al conectar
        if user_id in self.last_scores:
            await websocket.send_json({
                "type": "initial",
                "data": self.last_scores[user_id]
            })
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Envía mensaje a un usuario específico."""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            
            # Limpiar conexiones rotas
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast(self, message: dict):
        """Broadcast a todos los usuarios conectados (para mantenimiento)."""
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)
    
    async def update_readiness_score(self, user_id: str, score_data: dict, force: bool = False):
        """
        Actualiza y notifica el readiness score si ha cambiado significativamente.
        
        Args:
            user_id: ID del usuario
            score_data: Datos del readiness score
            force: Si True, enviar incluso si el cambio es pequeño
        """
        previous = self.last_scores.get(user_id, {})
        current_score = score_data.get("readiness_score", 0)
        previous_score = previous.get("readiness_score", 0)
        
        # Guardar en cache
        self.last_scores[user_id] = score_data
        
        # Determinar si enviar update
        should_send = force or abs(current_score - previous_score) > self.score_threshold
        
        # También enviar si cambia el status (low/medium/high)
        current_status = score_data.get("status")
        previous_status = previous.get("status")
        if current_status != previous_status:
            should_send = True
        
        if should_send and user_id in self.active_connections:
            await self.send_personal_message({
                "type": "readiness_update",
                "timestamp": datetime.now().isoformat(),
                "data": score_data,
                "change": round(current_score - previous_score, 1) if previous else None
            }, user_id)
    
    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# Instancia global del manager
manager = ConnectionManager()


# ==================== ENDPOINT WEBSOCKET ====================

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.deps import get_current_user_id_from_token

router = APIRouter()

@router.websocket("/ws/readiness")
async def readiness_websocket(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    WebSocket para streaming en tiempo real del Readiness Score.
    
    URL: ws://localhost:8005/api/v1/ws/readiness?token=<jwt_token>
    
    Mensajes enviados:
    
    1. Conexión inicial:
    {
        "type": "initial",
        "data": {...}  // Score actual
    }
    
    2. Actualización automática (cuando cambian los datos):
    {
        "type": "readiness_update",
        "timestamp": "2026-03-26T18:30:00",
        "data": {...},
        "change": 5.2  // Diferencia con el score anterior
    }
    
    3. Alerta de cambio de status:
    {
        "type": "status_change",
        "from": "medium",
        "to": "low",
        "message": "Tu readiness ha bajado. Considera descanso."
    }
    """
    # TODO: Validar token JWT para obtener user_id
    # Por ahora usamos default_user para testing
    user_id = "default_user"  # En producción: decode_jwt(token)
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Recibir mensajes del cliente (ping, configuración, etc.)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            
            elif action == "get_current":
                # Cliente solicita score actual
                if user_id in manager.last_scores:
                    await websocket.send_json({
                        "type": "current",
                        "data": manager.last_scores[user_id]
                    })
                else:
                    # Calcular y enviar
                    from app.core.readiness_engine import compute_readiness_score
                    # TODO: Obtener datos actuales de la base de datos
                    await websocket.send_json({
                        "type": "current",
                        "data": {"error": "No cached data available"}
                    })
            
            elif action == "subscribe_alerts":
                # Cliente quiere recibir alertas específicas
                alert_types = message.get("types", ["status_change", "significant_drop"])
                await websocket.send_json({
                    "type": "subscribed",
                    "alert_types": alert_types
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


# ==================== INTEGRACIÓN CON SINCRONIZACIÓN ====================

async def notify_readiness_update(user_id: str, db: Session):
    """
    Función para llamar después de sincronizar datos de Garmin.
    Recalcula el readiness score y notifica a los clientes conectados.
    
    Uso en sync_service.py después de guardar nuevos datos:
    
    from app.api.api_v1.endpoints.readiness_ws import notify_readiness_update
    await notify_readiness_update(user_id, db)
    """
    from app.core.readiness_engine import compute_readiness_score
    from app.models.biometrics import Biometrics
    import json
    
    # Obtener datos más recientes
    latest = db.query(Biometrics).filter(
        Biometrics.user_id == user_id
    ).order_by(Biometrics.date.desc()).first()
    
    if not latest:
        return
    
    try:
        bio_data = json.loads(latest.data) if latest.data else {}
    except:
        return
    
    # Preparar input para el engine
    input_data = {
        "heart_rate": bio_data.get("heartRate", 60),
        "hrv": bio_data.get("hrv"),
        "sleep_hours": bio_data.get("sleep", 0),
        "stress_level": bio_data.get("stress", 50),
        "steps": bio_data.get("steps", 0),
        "steps_prev_7d_avg": 10000,  # Simplificado
        "is_rest_day": bio_data.get("steps", 0) < 8000,
        "exercise_load_7d": 1.0
    }
    
    # Calcular score
    result = compute_readiness_score(user_id, input_data, db)
    
    # Notificar a clientes conectados
    await manager.update_readiness_score(user_id, result)


# ==================== BACKGROUND TASK ====================

async def periodic_readiness_check(db: Session, interval_minutes: int = 15):
    """
    Task de fondo que verifica y actualiza el readiness score periódicamente.
    Útil para mantener el score actualizado sin esperar sincronización manual.
    
    Uso en main.py:
    
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(periodic_readiness_check_task())
    """
    while True:
        try:
            # Obtener todos los usuarios activos
            from app.models.user import User
            users = db.query(User).all()
            
            for user in users:
                if manager.is_user_connected(user.id):
                    # Solo recalcular si hay clientes conectados (ahorro de recursos)
                    await notify_readiness_update(user.id, db)
            
            await asyncio.sleep(interval_minutes * 60)
        except Exception as e:
            print(f"Error en periodic check: {e}")
            await asyncio.sleep(60)  # Retry en 1 min si hay error


# Ejemplo de integración en sync_service.py:
INTEGRATION_COMMENT = """
# En app/services/sync_service.py, añadir al final de sync_garmin_health:

from app.api.api_v1.endpoints.readiness_ws import notify_readiness_update

# Después de guardar biometrics en la base de datos:
await notify_readiness_update(user_id, db)
"""
