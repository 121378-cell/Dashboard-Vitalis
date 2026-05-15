"""
ATLAS VIVO — Bus de Eventos Internos.

Sistema ligero de eventos que permite a los servicios notificar
que algo ha ocurrido sin acoplarse directamente entre sí.

Flujo:
1. Un servicio llama a emit() → se guarda en la tabla atlas_events
2. El event processor job (scheduler) llama a process_pending()
3. process_pending() evalúa triggers y genera intervenciones si procede
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func as sa_func

from app.db.session import SessionLocal
from app.models.atlas_event import AtlasEvent

logger = logging.getLogger(__name__)

# ─── Constantes ─────────────────────────────────────────────────────────────

BATCH_SIZE = 50  # Eventos a procesar por lote
MAX_EVENT_AGE_DAYS = 30  # Eventos más antiguos se limpian
CLEANUP_BATCH_SIZE = 500  # Registros a eliminar por lote de cleanup


# ─── Core API ───────────────────────────────────────────────────────────────

def emit(
    user_id: str,
    event_type: str,
    payload: dict | None = None,
    source: str = "system",
    correlation_id: str | None = None,
) -> AtlasEvent | None:
    """
    Registra un evento en la cola interna.

    Args:
        user_id: Identificador del usuario
        event_type: Tipo de evento (ver AtlasEvent.event_type docs)
        payload: Datos adicionales del evento
        source: Origen del evento (daily_loop, sync_service, etc.)
        correlation_id: ID para correlacionar eventos relacionados

    Returns:
        El evento creado, o None si falló
    """
    try:
        event = AtlasEvent(
            user_id=user_id,
            event_type=event_type,
            payload=payload or {},
            source=source,
            correlation_id=correlation_id,
        )
        with SessionLocal() as db:
            db.add(event)
            db.commit()
            db.refresh(event)
            logger.debug(
                "Event emitted: type=%s user=%s source=%s",
                event_type, user_id, source,
            )
            return event
    except Exception as e:
        logger.error("Failed to emit event %s for user %s: %s", event_type, user_id, e)
        return None


def process_pending(dry_run: bool = False) -> list[dict[str, Any]]:
    """
    Procesa eventos pendientes (processed=False) por orden de creación.

    Para cada evento:
    1. Lo marca como procesado
    2. Lo pasa al InterventionService para evaluar triggers
    3. Si el InterventionService decide intervenir, ejecuta la acción

    Args:
        dry_run: Si True, solo simula el procesamiento sin modificar BD

    Returns:
        Lista de intervenciones generadas (o simuladas si dry_run=True)
    """
    interventions: list[dict[str, Any]] = []

    try:
        with SessionLocal() as db:
            pending = (
                db.query(AtlasEvent)
                .filter(AtlasEvent.processed == False)  # noqa: E712
                .order_by(AtlasEvent.created_at.asc())
                .limit(BATCH_SIZE)
                .all()
            )

            if not pending:
                return interventions

            logger.info("Processing %d pending events...", len(pending))

            for event in pending:
                try:
                    if not dry_run:
                        event.processed = True
                        event.processed_at = datetime.utcnow()

                    # Evaluar triggers para este evento
                    from app.services.intervention_service import InterventionService
                    result = InterventionService.evaluate_triggers(event)

                    if result:
                        interventions.append({
                            "event_id": event.id,
                            "event_type": event.event_type,
                            "user_id": event.user_id,
                            "intervention": result,
                        })

                except Exception as e:
                    logger.error(
                        "Error processing event %d (%s): %s",
                        event.id, event.event_type, e,
                    )
                    if not dry_run:
                        event.error = str(e)[:500]

            if not dry_run:
                db.commit()

            logger.info(
                "Processed %d events, generated %d interventions",
                len(pending), len(interventions),
            )
            return interventions

    except Exception as e:
        logger.error("Failed to process pending events: %s", e)
        return interventions


def get_events(
    user_id: str,
    event_type: str | None = None,
    limit: int = 50,
    unprocessed_only: bool = False,
) -> list[AtlasEvent]:
    """
    Obtiene historial de eventos para un usuario.

    Args:
        user_id: Identificador del usuario
        event_type: Filtrar por tipo (opcional)
        limit: Máximo de eventos a devolver
        unprocessed_only: Solo eventos no procesados

    Returns:
        Lista de eventos
    """
    try:
        with SessionLocal() as db:
            query = db.query(AtlasEvent).filter(AtlasEvent.user_id == user_id)

            if event_type:
                query = query.filter(AtlasEvent.event_type == event_type)

            if unprocessed_only:
                query = query.filter(AtlasEvent.processed == False)  # noqa: E712

            query = query.order_by(AtlasEvent.created_at.desc()).limit(limit)
            return query.all()
    except Exception as e:
        logger.error("Failed to get events for user %s: %s", user_id, e)
        return []


def cleanup_events(older_than_days: int = MAX_EVENT_AGE_DAYS) -> int:
    """
    Limpia eventos procesados más antiguos que older_than_days.

    Debe ejecutarse periódicamente (job semanal del scheduler).

    Args:
        older_than_days: Días de antigüedad para eliminar

    Returns:
        Número de eventos eliminados
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        with SessionLocal() as db:
            result = (
                db.query(AtlasEvent)
                .filter(
                    AtlasEvent.created_at < cutoff,
                    AtlasEvent.processed == True,  # noqa: E712
                )
                .limit(CLEANUP_BATCH_SIZE)
                .delete(synchronize_session=False)
            )
            db.commit()
            if result > 0:
                logger.info("Cleaned up %d events older than %d days", result, older_than_days)
            return result
    except Exception as e:
        logger.error("Failed to cleanup events: %s", e)
        return 0


def count_pending(user_id: str | None = None) -> int:
    """
    Cuenta eventos pendientes de procesar.

    Args:
        user_id: Si se especifica, cuenta solo para ese usuario

    Returns:
        Número de eventos pendientes
    """
    try:
        with SessionLocal() as db:
            query = db.query(AtlasEvent).filter(
                AtlasEvent.processed == False  # noqa: E712
            )
            if user_id:
                query = query.filter(AtlasEvent.user_id == user_id)
            return query.count()
    except Exception as e:
        logger.error("Failed to count pending events: %s", e)
        return 0


def get_stats(user_id: str | None = None) -> dict[str, Any]:
    """
    Estadísticas de eventos para monitorización.

    Args:
        user_id: Si se especifica, stats para ese usuario

    Returns:
        Diccionario con estadísticas
    """
    try:
        with SessionLocal() as db:
            query = db.query(AtlasEvent)
            if user_id:
                query = query.filter(AtlasEvent.user_id == user_id)

            total = query.count()

            pending = query.filter(
                AtlasEvent.processed == False  # noqa: E712
            ).count()

            # Eventos por tipo
            type_counts = dict(
                db.query(
                    AtlasEvent.event_type,
                    sa_func.count(AtlasEvent.id),
                )
                .group_by(AtlasEvent.event_type)
                .all()
            )

            return {
                "total": total,
                "pending": pending,
                "by_type": type_counts,
                "user_id": user_id or "all",
            }
    except Exception as e:
        logger.error("Failed to get event stats: %s", e)
        return {"error": str(e)}
